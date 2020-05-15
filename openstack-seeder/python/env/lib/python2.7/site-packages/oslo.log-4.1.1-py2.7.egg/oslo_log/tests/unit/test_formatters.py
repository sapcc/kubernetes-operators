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

"""Unit Tests for oslo.log formatter"""

import logging
import sys
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslo_context import context
from oslotest import base as test_base

from oslo_log import formatters
from oslo_log import log


def _fake_context():
    ctxt = context.RequestContext(user="user",
                                  tenant="tenant",
                                  project_domain="pdomain",
                                  user_domain="udomain",
                                  overwrite=True)

    return ctxt


class AlternativeRequestContext(object):

    def __init__(self, user=None, tenant=None):
        self.user = user
        self.tenant = tenant

    def to_dict(self):
        return {'user': self.user,
                'tenant': self.tenant}


class FormatterTest(test_base.BaseTestCase):

    def setUp(self):
        super(FormatterTest, self).setUp()

    def test_replace_false_value_exists(self):
        d = {"user": "user1"}
        s = "%(user)s" % formatters._ReplaceFalseValue(d)
        self.assertEqual(d['user'], s)

    def test_replace_false_value_not_exists(self):
        d = {"user": "user1"}
        s = "%(project)s" % formatters._ReplaceFalseValue(d)
        self.assertEqual("-", s)

    def test_dictify_context_empty(self):
        self.assertEqual({}, formatters._dictify_context(None))

    @mock.patch("debtcollector.deprecate")
    def test_dictify_context_with_dict(self, mock_deprecate):
        d = {"user": "user"}
        self.assertEqual(d, formatters._dictify_context(d))
        mock_deprecate.assert_not_called()

    @mock.patch("debtcollector.deprecate")
    def test_dictify_context_with_context(self, mock_deprecate):
        ctxt = _fake_context()
        self.assertEqual(ctxt.get_logging_values(),
                         formatters._dictify_context(ctxt))
        mock_deprecate.assert_not_called()

    @mock.patch("debtcollector.deprecate")
    def test_dictify_context_without_get_logging_values(self, mock_deprecate):
        ctxt = AlternativeRequestContext(user="user", tenant="tenant")
        d = {"user": "user", "tenant": "tenant"}
        self.assertEqual(d, formatters._dictify_context(ctxt))
        mock_deprecate.assert_called_with(
            'The RequestContext.get_logging_values() '
            'method should be defined for logging context specific '
            'information.  The to_dict() method is deprecated '
            'for oslo.log use.', removal_version='5.0.0', version='3.8.0')


# Test for https://bugs.python.org/issue28603
class FormatUnhashableExceptionTest(test_base.BaseTestCase):
    def setUp(self):
        super(FormatUnhashableExceptionTest, self).setUp()
        self.config_fixture = self.useFixture(
            config_fixture.Config(cfg.ConfigOpts()))
        self.conf = self.config_fixture.conf
        log.register_options(self.conf)

    def _unhashable_exception_info(self):
        class UnhashableException(Exception):
            __hash__ = None

        try:
            raise UnhashableException()
        except UnhashableException:
            return sys.exc_info()

    def test_error_summary(self):
        exc_info = self._unhashable_exception_info()
        record = logging.LogRecord('test', logging.ERROR, 'test', 0,
                                   'test message', [], exc_info)
        err_summary = formatters._get_error_summary(record)
        self.assertTrue(err_summary)

    def test_json_format_exception(self):
        exc_info = self._unhashable_exception_info()
        formatter = formatters.JSONFormatter()
        tb = ''.join(formatter.formatException(exc_info))
        self.assertTrue(tb)

    def test_fluent_format_exception(self):
        exc_info = self._unhashable_exception_info()
        formatter = formatters.FluentFormatter()
        tb = formatter.formatException(exc_info)
        self.assertTrue(tb)

    def test_context_format_exception_norecord(self):
        exc_info = self._unhashable_exception_info()
        formatter = formatters.ContextFormatter(config=self.conf)
        tb = formatter.formatException(exc_info)
        self.assertTrue(tb)

    def test_context_format_exception(self):
        exc_info = self._unhashable_exception_info()
        formatter = formatters.ContextFormatter(config=self.conf)
        record = logging.LogRecord('test', logging.ERROR, 'test', 0,
                                   'test message', [], exc_info)
        tb = formatter.format(record)
        self.assertTrue(tb)
