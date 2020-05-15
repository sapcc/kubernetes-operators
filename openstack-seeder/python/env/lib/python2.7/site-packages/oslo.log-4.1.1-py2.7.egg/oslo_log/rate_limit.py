# Copyright 2016 Red Hat, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import logging

try:
    from time import monotonic as monotonic_clock   # noqa
except ImportError:
    from monotonic import monotonic as monotonic_clock   # noqa


class _LogRateLimit(logging.Filter):
    def __init__(self, burst, interval, except_level=None):
        logging.Filter.__init__(self)
        self.burst = burst
        self.interval = interval
        self.except_level = except_level
        self.logger = logging.getLogger()
        self._reset()

    def _reset(self, now=None):
        if now is None:
            now = monotonic_clock()
        self.counter = 0
        self.end_time = now + self.interval
        self.emit_warn = False

    def filter(self, record):
        if (self.except_level is not None
           and record.levelno >= self.except_level):
            # don't limit levels >= except_level
            return True

        timestamp = monotonic_clock()
        if timestamp >= self.end_time:
            self._reset(timestamp)
            self.counter += 1
            return True

        self.counter += 1
        if self.counter <= self.burst:
            return True
        if self.emit_warn:
            # Allow to log our own warning: self.logger is also filtered by
            # rate limiting
            return True

        if self.counter == self.burst + 1:
            self.emit_warn = True
            self.logger.error("Logging rate limit: "
                              "drop after %s records/%s sec",
                              self.burst, self.interval)
            self.emit_warn = False

        # Drop the log
        return False


def _iter_loggers():
    """Iterate on existing loggers."""

    # Sadly, Logger.manager and Manager.loggerDict are not documented,
    # but there is no logging public function to iterate on all loggers.

    # The root logger is not part of loggerDict.
    yield logging.getLogger()

    manager = logging.Logger.manager
    for logger in manager.loggerDict.values():
        if isinstance(logger, logging.PlaceHolder):
            continue
        yield logger


_LOG_LEVELS = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'DEBUG': logging.DEBUG,
}


def install_filter(burst, interval, except_level='CRITICAL'):
    """Install a rate limit filter on existing and future loggers.

    Limit logs to *burst* messages every *interval* seconds, except of levels
    >= *except_level*. *except_level* is a log level name like 'CRITICAL'. If
    *except_level* is an empty string, all levels are filtered.

    The filter uses a monotonic clock, the timestamp of log records is not
    used.

    Raise an exception if a rate limit filter is already installed.
    """

    if install_filter.log_filter is not None:
        raise RuntimeError("rate limit filter already installed")

    try:
        except_levelno = _LOG_LEVELS[except_level]
    except KeyError:
        raise ValueError("invalid log level name: %r" % except_level)

    log_filter = _LogRateLimit(burst, interval, except_levelno)

    install_filter.log_filter = log_filter
    install_filter.logger_class = logging.getLoggerClass()

    class RateLimitLogger(install_filter.logger_class):
        def __init__(self, *args, **kw):
            logging.Logger.__init__(self, *args, **kw)
            self.addFilter(log_filter)

    # Setup our own logger class to automatically add the filter
    # to new loggers.
    logging.setLoggerClass(RateLimitLogger)

    # Add the filter to all existing loggers
    for logger in _iter_loggers():
        logger.addFilter(log_filter)


install_filter.log_filter = None
install_filter.logger_class = None


def uninstall_filter():
    """Uninstall the rate filter installed by install_filter().

    Do nothing if the filter was already uninstalled.
    """

    if install_filter.log_filter is None:
        # not installed (or already uninstalled)
        return

    # Restore the old logger class
    logging.setLoggerClass(install_filter.logger_class)

    # Remove the filter from all existing loggers
    for logger in _iter_loggers():
        logger.removeFilter(install_filter.log_filter)

    install_filter.logger_class = None
    install_filter.log_filter = None
