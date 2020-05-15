# Copyright (c) 2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Unit Tests for oslo.log with custom log handler"""


import logging

from oslo_log import log

from oslo_log.tests.unit.test_log import LogTestBase


class CustomLogHandler(logging.StreamHandler):
    # Custom loghandler to mimick the error which was later fixed by
    # https://github.com/openstack/oslo.privsep/commit/3c47348ced0d3ace1113ba8de8dff015792b0b89

    def emit(self, record):
        # Make args None; this was the error, which broke oslo_log formatting
        record.args = None  # This is intentionally wrong

        super(CustomLogHandler, self).emit(record)


class CustomLogHandlerTestCase(LogTestBase):
    def setUp(self):
        super(CustomLogHandlerTestCase, self).setUp()
        self.config(logging_context_format_string="HAS CONTEXT "
                                                  "[%(request_id)s]: "
                                                  "%(message)s",
                    logging_default_format_string="NOCTXT: %(message)s",
                    logging_debug_format_suffix="--DBG")
        self.log = log.getLogger('')  # obtain root logger instead of 'unknown'
        self._add_handler_with_cleanup(self.log, handler=CustomLogHandler)
        self._set_log_level_with_cleanup(self.log, logging.DEBUG)

    def test_log(self):
        message = 'foo'
        self.log.info(message)
        self.assertEqual("NOCTXT: %s\n" % message, self.stream.getvalue())
