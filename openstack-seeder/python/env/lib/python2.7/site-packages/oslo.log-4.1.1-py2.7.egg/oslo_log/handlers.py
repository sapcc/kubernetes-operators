# -*- coding: utf-8 -*-
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import inspect
import logging
import logging.config
import logging.handlers
import os

try:
    from systemd import journal
except ImportError:
    journal = None
try:
    import syslog
except ImportError:
    syslog = None


NullHandler = logging.NullHandler


def _get_binary_name():
    return os.path.basename(inspect.stack()[-1][1])


_AUDIT = logging.INFO + 1
_TRACE = 5

# This is a copy of the numerical constants from syslog.h. The
# definition of these goes back at least 20 years, and is specifically
# 3 bits in a packed field, so these aren't likely to ever need
# changing.
SYSLOG_MAP = {
    "CRITICAL": 2,
    "ERROR": 3,
    "WARNING": 4,
    "WARN": 4,
    "INFO": 6,
    "DEBUG": 7,
}


class OSSysLogHandler(logging.Handler):
    """Syslog based handler. Only available on UNIX-like platforms."""

    def __init__(self, facility=None):
        # Default values always get evaluated, for which reason we avoid
        # using 'syslog' directly, which may not be available.
        facility = facility if facility is not None else syslog.LOG_USER
        # Do not use super() unless type(logging.Handler) is 'type'
        # (i.e. >= Python 2.7).
        if not syslog:
            raise RuntimeError("Syslog not available on this platform")
        logging.Handler.__init__(self)
        binary_name = _get_binary_name()
        syslog.openlog(binary_name, 0, facility)

    def emit(self, record):
        priority = SYSLOG_MAP.get(record.levelname, 7)
        message = self.format(record)
        syslog.syslog(priority, message)


class OSJournalHandler(logging.Handler):

    custom_fields = (
        'project_name',
        'project_id',
        'user_name',
        'user_id',
        'request_id',
    )

    def __init__(self):
        # Do not use super() unless type(logging.Handler) is 'type'
        # (i.e. >= Python 2.7).
        if not journal:
            raise RuntimeError("Systemd bindings do not exist")
        logging.Handler.__init__(self)
        self.binary_name = _get_binary_name()

    def emit(self, record):
        priority = SYSLOG_MAP.get(record.levelname, 7)
        message = self.format(record)

        extras = {
            'CODE_FILE': record.pathname,
            'CODE_LINE': record.lineno,
            'CODE_FUNC': record.funcName,
            'THREAD_NAME': record.threadName,
            'PROCESS_NAME': record.processName,
            'LOGGER_NAME': record.name,
            'LOGGER_LEVEL': record.levelname,
            'SYSLOG_IDENTIFIER': self.binary_name,
            'PRIORITY': priority
        }

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatter.formatException(
                    record.exc_info)
        if record.exc_text:
            extras['EXCEPTION_INFO'] = record.exc_text
            # Leave EXCEPTION_TEXT for backward compatibility
            extras['EXCEPTION_TEXT'] = record.exc_text

        for field in self.custom_fields:
            value = record.__dict__.get(field)
            if value:
                extras[field.upper()] = value

        journal.send(message, **extras)


class ColorHandler(logging.StreamHandler):
    """Log handler that sets the 'color' key based on the level

    To use, include a '%(color)s' entry in the logging_context_format_string.
    There is also a '%(reset_color)s' key that can be used to manually reset
    the color within a log line.
    """
    LEVEL_COLORS = {
        _TRACE: '\033[00;35m',  # MAGENTA
        logging.DEBUG: '\033[00;32m',  # GREEN
        logging.INFO: '\033[00;36m',  # CYAN
        _AUDIT: '\033[01;36m',  # BOLD CYAN
        logging.WARN: '\033[01;33m',  # BOLD YELLOW
        logging.ERROR: '\033[01;31m',  # BOLD RED
        logging.CRITICAL: '\033[01;31m',  # BOLD RED
    }

    def format(self, record):
        record.color = self.LEVEL_COLORS[record.levelno]
        record.reset_color = '\033[00m'
        return logging.StreamHandler.format(self, record) + record.reset_color
