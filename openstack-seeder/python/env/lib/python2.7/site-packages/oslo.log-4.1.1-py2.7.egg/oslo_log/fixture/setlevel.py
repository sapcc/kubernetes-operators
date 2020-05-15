# All Rights Reserved.
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

import fixtures


class SetLogLevel(fixtures.Fixture):
    """Override the log level for the named loggers, restoring their
    previous value at the end of the test.

    To use::

      from oslo_log import fixture as log_fixture

      self.useFixture(log_fixture.SetLogLevel(['myapp.foo'], logging.DEBUG))

    :param logger_names: Sequence of logger names, as would be passed
                         to getLogger().
    :type logger_names: list(str)
    :param level: Logging level, usually one of logging.DEBUG,
                  logging.INFO, etc.
    :type level: int
    """

    def __init__(self, logger_names, level):
        self.logger_names = logger_names
        self.level = level

    def setUp(self):
        super(SetLogLevel, self).setUp()
        for name in self.logger_names:
            # NOTE(dhellmann): Use the stdlib version of getLogger()
            # so we get the logger and not any adaptor wrapping it.
            logger = logging.getLogger(name)
            self.addCleanup(logger.setLevel, logger.level)
            logger.setLevel(self.level)
