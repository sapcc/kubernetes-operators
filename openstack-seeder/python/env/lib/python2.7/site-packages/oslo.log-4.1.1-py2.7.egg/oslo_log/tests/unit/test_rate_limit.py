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

import io
import logging
from unittest import mock

from oslotest import base as test_base

from oslo_log import rate_limit


class LogRateLimitTestCase(test_base.BaseTestCase):
    def tearDown(self):
        super(LogRateLimitTestCase, self).tearDown()
        rate_limit.uninstall_filter()

    def install_filter(self, *args):
        rate_limit.install_filter(*args)

        logger = logging.getLogger()

        # remove handlers to not pollute stdout
        def restore_handlers(logger, handlers):
            for handler in handlers:
                logger.addHandler(handler)

        self.addCleanup(restore_handlers, logger, list(logger.handlers))
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

        # install our handler writing logs into a StringIO
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        return (logger, stream)

    @mock.patch('oslo_log.rate_limit.monotonic_clock')
    def test_rate_limit(self, mock_clock):
        mock_clock.return_value = 1
        logger, stream = self.install_filter(2, 1)

        # first burst
        logger.error("message 1")
        logger.error("message 2")
        logger.error("message 3")
        self.assertEqual(stream.getvalue(),
                         'message 1\n'
                         'message 2\n'
                         'Logging rate limit: drop after 2 records/1 sec\n')

        # second burst (clock changed)
        stream.seek(0)
        stream.truncate()
        mock_clock.return_value = 2

        logger.error("message 4")
        logger.error("message 5")
        logger.error("message 6")
        self.assertEqual(stream.getvalue(),
                         'message 4\n'
                         'message 5\n'
                         'Logging rate limit: drop after 2 records/1 sec\n')

    @mock.patch('oslo_log.rate_limit.monotonic_clock')
    def test_rate_limit_except_level(self, mock_clock):
        mock_clock.return_value = 1
        logger, stream = self.install_filter(1, 1, 'CRITICAL')

        # first burst
        logger.error("error 1")
        logger.error("error 2")
        logger.critical("critical 3")
        logger.critical("critical 4")
        self.assertEqual(stream.getvalue(),
                         'error 1\n'
                         'Logging rate limit: drop after 1 records/1 sec\n'
                         'critical 3\n'
                         'critical 4\n')

    def test_install_twice(self):
        rate_limit.install_filter(100, 1)
        self.assertRaises(RuntimeError, rate_limit.install_filter, 100, 1)

    @mock.patch('oslo_log.rate_limit.monotonic_clock')
    def test_uninstall(self, mock_clock):
        mock_clock.return_value = 1
        logger, stream = self.install_filter(1, 1)
        rate_limit.uninstall_filter()

        # not limited
        logger.error("message 1")
        logger.error("message 2")
        logger.error("message 3")
        self.assertEqual(stream.getvalue(),
                         'message 1\n'
                         'message 2\n'
                         'message 3\n')
