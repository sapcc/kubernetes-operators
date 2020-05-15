# -*- coding: utf-8 -*-

# Copyright (c) 2011 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.

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

from contextlib import contextmanager
import copy
import datetime
import io
import logging
import os
import platform
import shutil
import sys
try:
    import syslog
except ImportError:
    syslog = None
import tempfile
import time
from unittest import mock

from dateutil import tz
from oslo_config import cfg
from oslo_config import fixture as fixture_config  # noqa
from oslo_context import context
from oslo_context import fixture as fixture_context
from oslo_i18n import fixture as fixture_trans
from oslo_serialization import jsonutils
from oslotest import base as test_base
import testtools

from oslo_log import _options
from oslo_log import formatters
from oslo_log import handlers
from oslo_log import log
from oslo_utils import units


MIN_LOG_INI = b"""[loggers]
keys=root

[formatters]
keys=

[handlers]
keys=

[logger_root]
handlers=
"""


def _fake_context():
    ctxt = context.RequestContext(1, 1, overwrite=True)
    ctxt.user = 'myuser'
    ctxt.tenant = 'mytenant'
    ctxt.domain = 'mydomain'
    ctxt.project_domain = 'myprojectdomain'
    ctxt.user_domain = 'myuserdomain'

    return ctxt


def _fake_new_context():
    # New style contexts have a user_name / project_name, this is done
    # distinctly from the above context to not have to rewrite all the
    # other tests.
    ctxt = context.RequestContext(1, 1, overwrite=True)
    ctxt.user_name = 'myuser'
    ctxt.project_name = 'mytenant'
    ctxt.domain = 'mydomain'
    ctxt.project_domain = 'myprojectdomain'
    ctxt.user_domain = 'myuserdomain'

    return ctxt


class CommonLoggerTestsMixIn(object):
    """These tests are shared between LoggerTestCase and
    LazyLoggerTestCase.
    """

    def setUp(self):
        super(CommonLoggerTestsMixIn, self).setUp()
        # common context has different fields to the defaults in log.py
        self.config_fixture = self.useFixture(
            fixture_config.Config(cfg.ConfigOpts()))
        self.config = self.config_fixture.config
        self.CONF = self.config_fixture.conf
        log.register_options(self.config_fixture.conf)
        self.config(logging_context_format_string='%(asctime)s %(levelname)s '
                                                  '%(name)s [%(request_id)s '
                                                  '%(user)s %(tenant)s] '
                                                  '%(message)s')
        self.log = None
        log._setup_logging_from_conf(self.config_fixture.conf, 'test', 'test')
        self.log_handlers = log.getLogger(None).logger.handlers

    def test_handlers_have_context_formatter(self):
        formatters_list = []
        for h in self.log.logger.handlers:
            f = h.formatter
            if isinstance(f, formatters.ContextFormatter):
                formatters_list.append(f)
        self.assertTrue(formatters_list)
        self.assertEqual(len(formatters_list), len(self.log.logger.handlers))

    def test_handles_context_kwarg(self):
        self.log.info("foo", context=_fake_context())
        self.assertTrue(True)  # didn't raise exception

    def test_will_be_debug_if_debug_flag_set(self):
        self.config(debug=True)
        logger_name = 'test_is_debug'
        log.setup(self.CONF, logger_name)
        logger = logging.getLogger(logger_name)
        self.assertEqual(logging.DEBUG, logger.getEffectiveLevel())

    def test_will_be_info_if_debug_flag_not_set(self):
        self.config(debug=False)
        logger_name = 'test_is_not_debug'
        log.setup(self.CONF, logger_name)
        logger = logging.getLogger(logger_name)
        self.assertEqual(logging.INFO, logger.getEffectiveLevel())

    def test_no_logging_via_module(self):
        for func in ('critical', 'error', 'exception', 'warning', 'warn',
                     'info', 'debug', 'log'):
            self.assertRaises(AttributeError, getattr, log, func)

    @mock.patch('platform.system', return_value='Linux')
    def test_eventlog_missing(self, platform_mock):
        self.config(use_eventlog=True)
        self.assertRaises(RuntimeError,
                          log._setup_logging_from_conf,
                          self.CONF,
                          'test',
                          'test')

    @mock.patch('platform.system', return_value='Windows')
    @mock.patch('logging.handlers.NTEventLogHandler')
    @mock.patch('oslo_log.log.getLogger')
    def test_eventlog(self, loggers_mock, handler_mock, platform_mock):
        self.config(use_eventlog=True)
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        handler_mock.assert_called_once_with('test')
        mock_logger = loggers_mock.return_value.logger
        mock_logger.addHandler.assert_any_call(handler_mock.return_value)

    @mock.patch('oslo_log.watchers.FastWatchedFileHandler')
    @mock.patch('oslo_log.log._get_log_file_path', return_value='test.conf')
    @mock.patch('platform.system', return_value='Linux')
    def test_watchlog_on_linux(self, platfotm_mock, path_mock, handler_mock):
        self.config(watch_log_file=True)
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        handler_mock.assert_called_once_with(path_mock.return_value)
        self.assertEqual(self.log_handlers[0], handler_mock.return_value)

    @mock.patch('logging.handlers.WatchedFileHandler')
    @mock.patch('oslo_log.log._get_log_file_path', return_value='test.conf')
    @mock.patch('platform.system', return_value='Windows')
    def test_watchlog_on_windows(self, platform_mock, path_mock, handler_mock):
        self.config(watch_log_file=True)
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        handler_mock.assert_called_once_with(path_mock.return_value)
        self.assertEqual(self.log_handlers[0], handler_mock.return_value)

    @mock.patch('logging.handlers.TimedRotatingFileHandler')
    @mock.patch('oslo_log.log._get_log_file_path', return_value='test.conf')
    def test_timed_rotate_log(self, path_mock, handler_mock):
        rotation_type = 'interval'
        when = 'weekday'
        interval = 2
        backup_count = 2
        self.config(log_rotation_type=rotation_type,
                    log_rotate_interval=interval,
                    log_rotate_interval_type=when,
                    max_logfile_count=backup_count)
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        handler_mock.assert_called_once_with(path_mock.return_value,
                                             when='w2',
                                             interval=interval,
                                             backupCount=backup_count)
        self.assertEqual(self.log_handlers[0], handler_mock.return_value)

    @mock.patch('logging.handlers.RotatingFileHandler')
    @mock.patch('oslo_log.log._get_log_file_path', return_value='test.conf')
    def test_rotate_log(self, path_mock, handler_mock):
        rotation_type = 'size'
        max_logfile_size_mb = 100
        maxBytes = max_logfile_size_mb * units.Mi
        backup_count = 2
        self.config(log_rotation_type=rotation_type,
                    max_logfile_size_mb=max_logfile_size_mb,
                    max_logfile_count=backup_count)
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        handler_mock.assert_called_once_with(path_mock.return_value,
                                             maxBytes=maxBytes,
                                             backupCount=backup_count)
        self.assertEqual(self.log_handlers[0], handler_mock.return_value)


class LoggerTestCase(CommonLoggerTestsMixIn, test_base.BaseTestCase):
    def setUp(self):
        super(LoggerTestCase, self).setUp()
        self.log = log.getLogger(None)


class BaseTestCase(test_base.BaseTestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.context_fixture = self.useFixture(
            fixture_context.ClearRequestContext())
        self.config_fixture = self.useFixture(
            fixture_config.Config(cfg.ConfigOpts()))
        self.config = self.config_fixture.config
        self.CONF = self.config_fixture.conf
        log.register_options(self.CONF)
        log.setup(self.CONF, 'base')


class LogTestBase(BaseTestCase):
    """Base test class that provides some convenience functions."""
    def _add_handler_with_cleanup(self, log_instance, handler=None,
                                  formatter=None):
        """Add a log handler to a log instance.

        This function should be used to add handlers to loggers in test cases
        instead of directly adding them to ensure that the handler is
        correctly removed at the end of the test.  Otherwise the handler may
        be left on the logger and interfere with subsequent tests.

        :param log_instance: The log instance to which the handler will be
            added.
        :param handler: The handler class to be added.  Must be the class
            itself, not an instance.
        :param formatter: The formatter class to set on the handler.  Must be
            the class itself, not an instance.
        """
        self.stream = io.StringIO()
        if handler is None:
            handler = logging.StreamHandler
        self.handler = handler(self.stream)
        if formatter is None:
            formatter = formatters.ContextFormatter
        self.handler.setFormatter(formatter())
        log_instance.logger.addHandler(self.handler)
        self.addCleanup(log_instance.logger.removeHandler, self.handler)

    def _set_log_level_with_cleanup(self, log_instance, level):
        """Set the log level of a logger for the duration of a test.

        Use this function to set the log level of a logger and add the
        necessary cleanup to reset it back to default at the end of the test.

        :param log_instance: The logger whose level will be changed.
        :param level: The new log level to use.
        """
        self.level = log_instance.logger.getEffectiveLevel()
        log_instance.logger.setLevel(level)
        self.addCleanup(log_instance.logger.setLevel, self.level)


class LogHandlerTestCase(BaseTestCase):
    def test_log_path_logdir(self):
        path = os.path.join('some', 'path')
        binary = 'foo-bar'
        expected = os.path.join(path, '%s.log' % binary)
        self.config(log_dir=path, log_file=None)
        self.assertEqual(log._get_log_file_path(self.config_fixture.conf,
                         binary=binary),
                         expected)

    def test_log_path_logfile(self):
        path = os.path.join('some', 'path')
        binary = 'foo-bar'
        expected = os.path.join(path, '%s.log' % binary)
        self.config(log_file=expected)
        self.assertEqual(log._get_log_file_path(self.config_fixture.conf,
                         binary=binary),
                         expected)

    def test_log_path_none(self):
        prefix = 'foo-bar'
        self.config(log_dir=None, log_file=None)
        self.assertIsNone(log._get_log_file_path(self.config_fixture.conf,
                          binary=prefix))

    def test_log_path_logfile_overrides_logdir(self):
        path = os.path.join(os.sep, 'some', 'path')
        prefix = 'foo-bar'
        expected = os.path.join(path, '%s.log' % prefix)
        self.config(log_dir=os.path.join('some', 'other', 'path'),
                    log_file=expected)
        self.assertEqual(log._get_log_file_path(self.config_fixture.conf,
                         binary=prefix),
                         expected)

    def test_iter_loggers(self):
        mylog = logging.getLogger("abc.cde")
        loggers = list(log._iter_loggers())
        self.assertIn(logging.getLogger(), loggers)
        self.assertIn(mylog, loggers)


class SysLogHandlersTestCase(BaseTestCase):
    """Test the standard Syslog handler."""
    def setUp(self):
        super(SysLogHandlersTestCase, self).setUp()
        self.facility = logging.handlers.SysLogHandler.LOG_USER
        self.logger = logging.handlers.SysLogHandler(facility=self.facility)

    def test_standard_format(self):
        """Ensure syslog msg isn't modified for standard handler."""
        logrecord = logging.LogRecord('name', logging.WARNING, '/tmp', 1,
                                      'Message', None, None)
        expected = logrecord
        self.assertEqual(expected.getMessage(),
                         self.logger.format(logrecord))


@testtools.skipUnless(syslog, "syslog is not available")
class OSSysLogHandlerTestCase(BaseTestCase):
    def test_handler(self):
        handler = handlers.OSSysLogHandler()
        syslog.syslog = mock.Mock()
        handler.emit(
            logging.LogRecord("foo", logging.INFO,
                              "path", 123, "hey!",
                              None, None))
        self.assertTrue(syslog.syslog.called)

    def test_syslog_binary_name(self):
        # There is no way to test the actual output written to the
        # syslog (e.g. /var/log/syslog) to confirm binary_name value
        # is actually present
        syslog.openlog = mock.Mock()
        handlers.OSSysLogHandler()
        syslog.openlog.assert_called_with(handlers._get_binary_name(),
                                          0, syslog.LOG_USER)

    def test_find_facility(self):
        self.assertEqual(syslog.LOG_USER, log._find_facility("user"))
        self.assertEqual(syslog.LOG_LPR, log._find_facility("LPR"))
        self.assertEqual(syslog.LOG_LOCAL3, log._find_facility("log_local3"))
        self.assertEqual(syslog.LOG_UUCP, log._find_facility("LOG_UUCP"))
        self.assertRaises(TypeError,
                          log._find_facility,
                          "fougere")

    def test_syslog(self):
        msg_unicode = u"Benoît Knecht & François Deppierraz login failure"
        handler = handlers.OSSysLogHandler()
        syslog.syslog = mock.Mock()
        handler.emit(
            logging.LogRecord("name", logging.INFO, "path", 123,
                              msg_unicode, None, None))
        syslog.syslog.assert_called_once_with(syslog.LOG_INFO, msg_unicode)


class OSJournalHandlerTestCase(BaseTestCase):
    """Test systemd journal logging.

    This is a lightweight test for testing systemd journal logging. It
    mocks out the journal interface itself, which allows us to not
    have to have systemd-python installed (which is not possible to
    install on non Linux environments).

    Real world testing is also encouraged.

    """
    def setUp(self):
        super(OSJournalHandlerTestCase, self).setUp()
        self.config(use_journal=True)
        self.journal = mock.patch("oslo_log.handlers.journal").start()
        self.addCleanup(self.journal.stop)
        log.setup(self.CONF, 'testing')

    def test_emit(self):
        logger = log.getLogger('nova-test.foo')
        local_context = _fake_new_context()
        logger.info("Foo", context=local_context)
        self.assertEqual(
            mock.call(mock.ANY, CODE_FILE=mock.ANY, CODE_FUNC='test_emit',
                      CODE_LINE=mock.ANY, LOGGER_LEVEL='INFO',
                      LOGGER_NAME='nova-test.foo', PRIORITY=6,
                      SYSLOG_IDENTIFIER=mock.ANY,
                      REQUEST_ID=mock.ANY,
                      PROJECT_NAME='mytenant',
                      PROCESS_NAME='MainProcess',
                      THREAD_NAME='MainThread',
                      USER_NAME='myuser'),
            self.journal.send.call_args)
        args, kwargs = self.journal.send.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], str)
        self.assertIsInstance(kwargs['CODE_LINE'], int)
        self.assertIsInstance(kwargs['PRIORITY'], int)
        del kwargs['CODE_LINE'], kwargs['PRIORITY']
        for key, arg in kwargs.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(arg, (bytes, str))

    def test_emit_exception(self):
        logger = log.getLogger('nova-exception.foo')
        local_context = _fake_new_context()
        try:
            raise Exception("Some exception")
        except Exception:
            logger.exception("Foo", context=local_context)
        self.assertEqual(
            mock.call(mock.ANY, CODE_FILE=mock.ANY,
                      CODE_FUNC='test_emit_exception',
                      CODE_LINE=mock.ANY, LOGGER_LEVEL='ERROR',
                      LOGGER_NAME='nova-exception.foo', PRIORITY=3,
                      SYSLOG_IDENTIFIER=mock.ANY,
                      REQUEST_ID=mock.ANY,
                      EXCEPTION_INFO=mock.ANY,
                      EXCEPTION_TEXT=mock.ANY,
                      PROJECT_NAME='mytenant',
                      PROCESS_NAME='MainProcess',
                      THREAD_NAME='MainThread',
                      USER_NAME='myuser'),
            self.journal.send.call_args)
        args, kwargs = self.journal.send.call_args
        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], str)
        self.assertIsInstance(kwargs['CODE_LINE'], int)
        self.assertIsInstance(kwargs['PRIORITY'], int)
        del kwargs['CODE_LINE'], kwargs['PRIORITY']
        for key, arg in kwargs.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(arg, (bytes, str))


class LogLevelTestCase(BaseTestCase):
    def setUp(self):
        super(LogLevelTestCase, self).setUp()
        levels = self.CONF.default_log_levels
        info_level = 'nova-test'
        warn_level = 'nova-not-debug'
        other_level = 'nova-below-debug'
        trace_level = 'nova-trace'
        levels.append(info_level + '=INFO')
        levels.append(warn_level + '=WARN')
        levels.append(other_level + '=7')
        levels.append(trace_level + '=TRACE')
        self.config(default_log_levels=levels)
        log.setup(self.CONF, 'testing')
        self.log = log.getLogger(info_level)
        self.log_no_debug = log.getLogger(warn_level)
        self.log_below_debug = log.getLogger(other_level)
        self.log_trace = log.getLogger(trace_level)

    def test_is_enabled_for(self):
        self.assertTrue(self.log.isEnabledFor(logging.INFO))
        self.assertFalse(self.log_no_debug.isEnabledFor(logging.DEBUG))
        self.assertTrue(self.log_below_debug.isEnabledFor(logging.DEBUG))
        self.assertTrue(self.log_below_debug.isEnabledFor(7))
        self.assertTrue(self.log_trace.isEnabledFor(log.TRACE))

    def test_has_level_from_flags(self):
        self.assertEqual(logging.INFO, self.log.logger.getEffectiveLevel())

    def test_has_level_from_flags_for_trace(self):
        self.assertEqual(log.TRACE, self.log_trace.logger.getEffectiveLevel())

    def test_child_log_has_level_of_parent_flag(self):
        logger = log.getLogger('nova-test.foo')
        self.assertEqual(logging.INFO, logger.logger.getEffectiveLevel())

    def test_child_log_has_level_of_parent_flag_for_trace(self):
        logger = log.getLogger('nova-trace.foo')
        self.assertEqual(log.TRACE, logger.logger.getEffectiveLevel())

    def test_get_loggers(self):
        log._loggers['sentinel_log'] = mock.sentinel.sentinel_log
        res = log.get_loggers()
        self.assertDictEqual(log._loggers, res)


class JSONFormatterTestCase(LogTestBase):
    def setUp(self):
        super(JSONFormatterTestCase, self).setUp()
        self.log = log.getLogger('test-json')
        self._add_handler_with_cleanup(self.log,
                                       formatter=formatters.JSONFormatter)
        self._set_log_level_with_cleanup(self.log, logging.DEBUG)

    def test_json_w_context_in_extras(self):
        test_msg = 'This is a %(test)s line'
        test_data = {'test': 'log'}
        local_context = _fake_context()
        self.log.debug(test_msg, test_data, key='value', context=local_context)
        self._validate_json_data('test_json_w_context_in_extras', test_msg,
                                 test_data, local_context)

    def test_json_w_fetched_global_context(self):
        test_msg = 'This is a %(test)s line'
        test_data = {'test': 'log'}
        local_context = _fake_context()
        # NOTE we're not passing the context explicitly here. But it'll add the
        # context to the extras anyway since the call to fake_context adds the
        # context to the thread. The context will be fetched with the
        # _update_record_with_context call that's done in the formatter.
        self.log.debug(test_msg, test_data, key='value')
        self._validate_json_data('test_json_w_fetched_global_context',
                                 test_msg, test_data, local_context)

    def _validate_json_data(self, testname, test_msg, test_data, ctx):
        data = jsonutils.loads(self.stream.getvalue())
        self.assertTrue(data)
        self.assertIn('extra', data)
        self.assertIn('context', data)
        extra = data['extra']
        context = data['context']
        self.assertNotIn('context', extra)
        self.assertEqual('value', extra['key'])
        self.assertEqual(ctx.user, context['user'])
        self.assertEqual(ctx.user_name, context['user_name'])
        self.assertEqual(ctx.project_name, context['project_name'])
        self.assertEqual('test-json', data['name'])
        self.assertIn('request_id', context)
        self.assertEqual(ctx.request_id, context['request_id'])
        self.assertIn('global_request_id', context)
        self.assertEqual(ctx.global_request_id, context['global_request_id'])

        self.assertEqual(test_msg % test_data, data['message'])
        self.assertEqual(test_msg, data['msg'])
        self.assertEqual(test_data, data['args'])

        self.assertEqual('test_log.py', data['filename'])
        self.assertEqual(testname, data['funcname'])

        self.assertEqual('DEBUG', data['levelname'])
        self.assertEqual(logging.DEBUG, data['levelno'])
        self.assertFalse(data['traceback'])

    def test_json_exception(self):
        test_msg = 'This is %s'
        test_data = 'exceptional'
        try:
            raise Exception('This is exceptional')
        except Exception:
            self.log.exception(test_msg, test_data)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertTrue(data)
        self.assertIn('extra', data)
        self.assertEqual('test-json', data['name'])

        self.assertEqual(test_msg % test_data, data['message'])
        self.assertEqual(test_msg, data['msg'])
        self.assertEqual([test_data], data['args'])

        self.assertEqual('ERROR', data['levelname'])
        self.assertEqual(logging.ERROR, data['levelno'])
        self.assertTrue(data['traceback'])

    def test_json_with_extra(self):
        test_msg = 'This is a %(test)s line'
        test_data = {'test': 'log'}
        extra_data = {'special_user': 'user1',
                      'special_tenant': 'unicorns'}
        self.log.debug(test_msg, test_data, key='value', extra=extra_data)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertTrue(data)
        self.assertIn('extra', data)
        for k, v in extra_data.items():
            self.assertIn(k, data['extra'])
            self.assertEqual(v, data['extra'][k])

    def test_json_with_extra_keys(self):
        test_msg = 'This is a %(test)s line'
        test_data = {'test': 'log'}
        extra_keys = ['special_tenant', 'special_user']
        special_tenant = 'unicorns'
        special_user = 'user2'
        self.log.debug(test_msg, test_data, key='value',
                       extra_keys=extra_keys, special_tenant=special_tenant,
                       special_user=special_user)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertTrue(data)
        self.assertIn('extra', data)
        self.assertIn(extra_keys[0], data['extra'])
        self.assertEqual(special_tenant, data['extra'][extra_keys[0]])
        self.assertIn(extra_keys[1], data['extra'])
        self.assertEqual(special_user, data['extra'][extra_keys[1]])

    def test_can_process_strings(self):
        expected = b'\\u2622'
        # see ContextFormatterTestCase.test_can_process_strings
        expected = '\\\\xe2\\\\x98\\\\xa2'
        self.log.info(b'%s', u'\u2622'.encode('utf8'))
        self.assertIn(expected, self.stream.getvalue())

    def test_exception(self):
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        try:
            raise RuntimeError('test_exception')
        except RuntimeError:
            self.log.warning('testing', context=ctxt)
        data = jsonutils.loads(self.stream.getvalue())
        self.assertIn('error_summary', data)
        self.assertEqual('RuntimeError: test_exception',
                         data['error_summary'])

    def test_no_exception(self):
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        self.log.info('testing', context=ctxt)
        data = jsonutils.loads(self.stream.getvalue())
        self.assertIn('error_summary', data)
        self.assertEqual('', data['error_summary'])

    def test_exception_without_exc_info_passed(self):
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        try:
            raise RuntimeError('test_exception\ntraceback\nfrom\nremote error')
        except RuntimeError:
            self.log.warning('testing', context=ctxt)
        data = jsonutils.loads(self.stream.getvalue())
        self.assertIn('error_summary', data)
        self.assertEqual('RuntimeError: test_exception', data['error_summary'])

    def test_exception_with_exc_info_passed(self):
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        try:
            raise RuntimeError('test_exception\ntraceback\nfrom\nremote error')
        except RuntimeError:
            self.log.exception('testing', context=ctxt)
        data = jsonutils.loads(self.stream.getvalue())
        self.assertIn('error_summary', data)
        self.assertEqual('RuntimeError: test_exception'
                         '\ntraceback\nfrom\nremote error',
                         data['error_summary'])

    def test_fallback(self):

        class MyObject(object):
            def __str__(self):
                return 'str'

            def __repr__(self):
                return 'repr'

        obj = MyObject()
        self.log.debug('obj=%s', obj)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertEqual('obj=str', data['message'])
        # Bug #1593641: If an object of record.args cannot be serialized,
        # convert it using repr() to prevent serialization error on logging.
        self.assertEqual(['repr'], data['args'])

    def test_extra_args_filtered(self):
        test_msg = 'This is a %(test)s line %%(unused)'
        test_data = {'test': 'log', 'unused': 'removeme'}
        self.log.debug(test_msg, test_data)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertNotIn('unused', data['args'])

    def test_entire_dict(self):
        test_msg = 'This is a %s dict'
        test_data = {'test': 'log', 'other': 'value'}
        self.log.debug(test_msg, test_data)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertEqual(test_data, data['args'])


def get_fake_datetime(retval):
    class FakeDateTime(datetime.datetime):
        @classmethod
        def fromtimestamp(cls, timestamp):
            return retval

    return FakeDateTime


class DictStreamHandler(logging.StreamHandler):
    """Serialize dict in order to avoid TypeError in python 3. It is needed for
    FluentFormatterTestCase.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            jsonutils.dump(msg, self.stream)
            self.stream.flush()
        except AttributeError:
            self.handleError(record)


class FluentFormatterTestCase(LogTestBase):
    def setUp(self):
        super(FluentFormatterTestCase, self).setUp()
        self.log = log.getLogger('test-fluent')
        self._add_handler_with_cleanup(self.log,
                                       handler=DictStreamHandler,
                                       formatter=formatters.FluentFormatter)
        self._set_log_level_with_cleanup(self.log, logging.DEBUG)

    def test_fluent(self):
        test_msg = 'This is a %(test)s line'
        test_data = {'test': 'log'}
        local_context = _fake_context()
        self.log.debug(test_msg, test_data, key='value', context=local_context)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertIn('lineno', data)
        self.assertIn('extra', data)
        extra = data['extra']
        context = data['context']
        self.assertEqual('value', extra['key'])
        self.assertEqual(local_context.user, context['user'])
        self.assertEqual('test-fluent', data['name'])

        self.assertIn('request_id', context)
        self.assertEqual(local_context.request_id, context['request_id'])
        self.assertIn('global_request_id', context)
        self.assertEqual(local_context.global_request_id,
                         context['global_request_id'])

        self.assertEqual(test_msg % test_data, data['message'])

        self.assertEqual('test_log.py', data['filename'])
        self.assertEqual('test_fluent', data['funcname'])

        self.assertEqual('DEBUG', data['level'])
        self.assertFalse(data['traceback'])

    def test_exception(self):
        local_context = _fake_context()
        try:
            raise RuntimeError('test_exception')
        except RuntimeError:
            self.log.warning('testing', context=local_context)
        data = jsonutils.loads(self.stream.getvalue())
        self.assertIn('error_summary', data)
        self.assertEqual('RuntimeError: test_exception',
                         data['error_summary'])

    def test_no_exception(self):
        local_context = _fake_context()
        self.log.info('testing', context=local_context)
        data = jsonutils.loads(self.stream.getvalue())
        self.assertIn('error_summary', data)
        self.assertEqual('', data['error_summary'])

    def test_json_exception(self):
        test_msg = 'This is %s'
        test_data = 'exceptional'
        try:
            raise Exception('This is exceptional')
        except Exception:
            self.log.exception(test_msg, test_data)

        data = jsonutils.loads(self.stream.getvalue())
        self.assertTrue(data)
        self.assertIn('extra', data)
        self.assertEqual('test-fluent', data['name'])

        self.assertEqual(test_msg % test_data, data['message'])

        self.assertEqual('ERROR', data['level'])
        self.assertTrue(data['traceback'])


class ContextFormatterTestCase(LogTestBase):
    def setUp(self):
        super(ContextFormatterTestCase, self).setUp()
        self.config(logging_context_format_string="HAS CONTEXT "
                                                  "[%(request_id)s]: "
                                                  "%(message)s",
                    logging_default_format_string="NOCTXT: %(message)s",
                    logging_debug_format_suffix="--DBG")
        self.log = log.getLogger('')  # obtain root logger instead of 'unknown'
        self._add_handler_with_cleanup(self.log)
        self._set_log_level_with_cleanup(self.log, logging.DEBUG)
        self.trans_fixture = self.useFixture(fixture_trans.Translation())

    def test_uncontextualized_log(self):
        message = 'foo'
        self.log.info(message)
        self.assertEqual("NOCTXT: %s\n" % message, self.stream.getvalue())

    def test_contextualized_log(self):
        ctxt = _fake_context()
        message = 'bar'
        self.log.info(message, context=ctxt)
        expected = 'HAS CONTEXT [%s]: %s\n' % (ctxt.request_id, message)
        self.assertEqual(expected, self.stream.getvalue())

    def test_context_is_taken_from_tls_variable(self):
        ctxt = _fake_context()
        message = 'bar'
        self.log.info(message)
        expected = "HAS CONTEXT [%s]: %s\n" % (ctxt.request_id, message)
        self.assertEqual(expected, self.stream.getvalue())

    def test_contextual_information_is_imparted_to_3rd_party_log_records(self):
        ctxt = _fake_context()
        sa_log = logging.getLogger('sqlalchemy.engine')
        sa_log.setLevel(logging.INFO)
        message = 'emulate logging within sqlalchemy'
        sa_log.info(message)

        expected = ('HAS CONTEXT [%s]: %s\n' % (ctxt.request_id, message))
        self.assertEqual(expected, self.stream.getvalue())

    def test_message_logging_3rd_party_log_records(self):
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        sa_log = logging.getLogger('sqlalchemy.engine')
        sa_log.setLevel(logging.INFO)
        message = self.trans_fixture.lazy('test ' + chr(128))
        sa_log.info(message)

        expected = ('HAS CONTEXT [%s]: %s\n' % (ctxt.request_id,
                                                str(message)))
        self.assertEqual(expected, self.stream.getvalue())

    def test_debugging_log(self):
        message = 'baz'
        self.log.debug(message)
        self.assertEqual("NOCTXT: %s --DBG\n" % message,
                         self.stream.getvalue())

    def test_message_logging(self):
        # NOTE(luisg): Logging message objects with unicode objects
        # may cause trouble by the logging mechanism trying to coerce
        # the Message object, with a wrong encoding. This test case
        # tests that problem does not occur.
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        message = self.trans_fixture.lazy('test ' + chr(128))
        self.log.info(message, context=ctxt)
        expected = "HAS CONTEXT [%s]: %s\n" % (ctxt.request_id,
                                               str(message))
        self.assertEqual(expected, self.stream.getvalue())

    def test_exception_logging(self):
        # NOTE(dhellmann): If there is an exception and %(error_summary)s
        # does not appear in the format string, ensure that it is
        # appended to the end of the log lines.
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        message = self.trans_fixture.lazy('test ' + chr(128))
        try:
            raise RuntimeError('test_exception_logging')
        except RuntimeError:
            self.log.warning(message, context=ctxt)
        expected = 'RuntimeError: test_exception_logging\n'
        self.assertTrue(self.stream.getvalue().endswith(expected))

    def test_skip_logging_builtin_exceptions(self):
        # NOTE(dhellmann): Several of the built-in exception types
        # should not be automatically added to the log output.
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        message = self.trans_fixture.lazy('test ' + chr(128))
        ignored_exceptions = [
            ValueError, TypeError, KeyError, AttributeError, ImportError
        ]
        for ignore in ignored_exceptions:
            try:
                raise ignore('test_exception_logging')
            except ignore as e:
                self.log.warning(message, context=ctxt)
                expected = '{}: {}'.format(e.__class__.__name__, e)
            self.assertNotIn(expected, self.stream.getvalue())

    def test_exception_logging_format_string(self):
        # NOTE(dhellmann): If the format string includes
        # %(error_summary)s then ensure the exception message ends up in
        # that position in the output.
        self.config(logging_context_format_string="A %(error_summary)s B")
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        message = self.trans_fixture.lazy('test ' + chr(128))
        try:
            raise RuntimeError('test_exception_logging')
        except RuntimeError:
            self.log.warning(message, context=ctxt)
        expected = 'A RuntimeError: test_exception_logging'
        self.assertTrue(self.stream.getvalue().startswith(expected))

    def test_no_exception_logging_format_string(self):
        # NOTE(dhellmann): If there is no exception but the format
        # string includes %(error_summary)s then ensure the "-" is
        # inserted.
        self.config(logging_context_format_string="%(error_summary)s")
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        message = self.trans_fixture.lazy('test ' + chr(128))
        self.log.info(message, context=ctxt)
        expected = '-\n'
        self.assertTrue(self.stream.getvalue().startswith(expected))

    def test_unicode_conversion_in_adapter(self):
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        message = "Exception is (%s)"
        ex = Exception(self.trans_fixture.lazy('test' + chr(128)))
        self.log.debug(message, ex, context=ctxt)
        message = str(message) % ex
        expected = "HAS CONTEXT [%s]: %s --DBG\n" % (ctxt.request_id,
                                                     message)
        self.assertEqual(expected, self.stream.getvalue())

    def test_unicode_conversion_in_formatter(self):
        ctxt = _fake_context()
        ctxt.request_id = str('99')
        no_adapt_log = logging.getLogger('no_adapt')
        no_adapt_log.setLevel(logging.INFO)
        message = "Exception is (%s)"
        ex = Exception(self.trans_fixture.lazy('test' + chr(128)))
        no_adapt_log.info(message, ex)
        message = str(message) % ex
        expected = "HAS CONTEXT [%s]: %s\n" % (ctxt.request_id,
                                               message)
        self.assertEqual(expected, self.stream.getvalue())

    def test_user_identity_logging(self):
        self.config(logging_context_format_string="HAS CONTEXT "
                                                  "[%(request_id)s "
                                                  "%(user_identity)s]: "
                                                  "%(message)s")
        ctxt = _fake_context()
        ctxt.request_id = u'99'
        message = 'test'
        self.log.info(message, context=ctxt)
        expected = ("HAS CONTEXT [%s %s %s %s %s %s]: %s\n" %
                    (ctxt.request_id, ctxt.user, ctxt.tenant, ctxt.domain,
                     ctxt.user_domain, ctxt.project_domain,
                     str(message)))
        self.assertEqual(expected, self.stream.getvalue())

    def test_user_identity_logging_set_format(self):
        self.config(logging_context_format_string="HAS CONTEXT "
                                                  "[%(request_id)s "
                                                  "%(user_identity)s]: "
                                                  "%(message)s",
                    logging_user_identity_format="%(user)s "
                                                 "%(tenant)s")
        ctxt = _fake_context()
        ctxt.request_id = u'99'
        message = 'test'
        self.log.info(message, context=ctxt)
        expected = ("HAS CONTEXT [%s %s %s]: %s\n" %
                    (ctxt.request_id, ctxt.user, ctxt.tenant,
                     str(message)))
        self.assertEqual(expected, self.stream.getvalue())

    @mock.patch("datetime.datetime",
                get_fake_datetime(
                    datetime.datetime(2015, 12, 16, 13, 54, 26, 517893)))
    @mock.patch("dateutil.tz.tzlocal", new=mock.Mock(return_value=tz.tzutc()))
    def test_rfc5424_isotime_format(self):
        self.config(logging_default_format_string="%(isotime)s %(message)s")

        message = "test"
        expected = "2015-12-16T13:54:26.517893+00:00 %s\n" % message

        self.log.info(message)

        self.assertEqual(expected, self.stream.getvalue())

    @mock.patch("datetime.datetime",
                get_fake_datetime(
                    datetime.datetime(2015, 12, 16, 13, 54, 26)))
    @mock.patch("time.time", new=mock.Mock(return_value=1450274066.000000))
    @mock.patch("dateutil.tz.tzlocal", new=mock.Mock(return_value=tz.tzutc()))
    def test_rfc5424_isotime_format_no_microseconds(self):
        self.config(logging_default_format_string="%(isotime)s %(message)s")

        message = "test"
        expected = "2015-12-16T13:54:26.000000+00:00 %s\n" % message

        self.log.info(message)

        self.assertEqual(expected, self.stream.getvalue())

    def test_can_process_strings(self):
        expected = b'\xe2\x98\xa2'
        # logging format string should be unicode string
        # or it will fail and inserting byte string in unicode string
        # causes such formatting
        expected = '\\xe2\\x98\\xa2'
        self.log.info(b'%s', u'\u2622'.encode('utf8'))
        self.assertIn(expected, self.stream.getvalue())

    def test_dict_args_with_unicode(self):
        msg = '%(thing)s'
        arg = {'thing': '\xc6\x91\xc6\xa1\xc6\xa1'}
        self.log.info(msg, arg)
        self.assertIn(arg['thing'], self.stream.getvalue())


class ExceptionLoggingTestCase(LogTestBase):
    """Test that Exceptions are logged."""

    def test_excepthook_logs_exception(self):
        product_name = 'somename'
        exc_log = log.getLogger(product_name)

        self._add_handler_with_cleanup(exc_log)
        excepthook = log._create_logging_excepthook(product_name)

        try:
            raise Exception('Some error happened')
        except Exception:
            excepthook(*sys.exc_info())

        expected_string = ("CRITICAL somename [-] Unhandled error: "
                           "Exception: Some error happened")
        self.assertIn(expected_string, self.stream.getvalue(),
                      message="Exception is not logged")

    def test_excepthook_installed(self):
        log.setup(self.CONF, "test_excepthook_installed")
        self.assertTrue(sys.excepthook != sys.__excepthook__)

    @mock.patch("datetime.datetime",
                get_fake_datetime(
                    datetime.datetime(2015, 12, 16, 13, 54, 26, 517893)))
    @mock.patch("dateutil.tz.tzlocal", new=mock.Mock(return_value=tz.tzutc()))
    def test_rfc5424_isotime_format(self):
        self.config(
            logging_default_format_string="%(isotime)s %(message)s",
            logging_exception_prefix="%(isotime)s ",
        )

        product_name = 'somename'
        exc_log = log.getLogger(product_name)

        self._add_handler_with_cleanup(exc_log)
        excepthook = log._create_logging_excepthook(product_name)

        message = 'Some error happened'
        try:
            raise Exception(message)
        except Exception:
            excepthook(*sys.exc_info())

        expected_string = ("2015-12-16T13:54:26.517893+00:00 "
                           "Exception: %s" % message)
        self.assertIn(expected_string,
                      self.stream.getvalue())


class FancyRecordTestCase(LogTestBase):
    """Test how we handle fancy record keys that are not in the
    base python logging.
    """

    def setUp(self):
        super(FancyRecordTestCase, self).setUp()
        # NOTE(sdague): use the different formatters to demonstrate format
        # string with valid fancy keys and without. Slightly hacky, but given
        # the way log objects layer up seemed to be most concise approach
        self.config(logging_context_format_string="%(color)s "
                                                  "[%(request_id)s]: "
                                                  "%(instance)s"
                                                  "%(resource)s"
                                                  "%(message)s",
                    logging_default_format_string="%(missing)s: %(message)s")
        self.colorlog = log.getLogger()
        self._add_handler_with_cleanup(self.colorlog, handlers.ColorHandler)
        self._set_log_level_with_cleanup(self.colorlog, logging.DEBUG)

    def test_unsupported_key_in_log_msg(self):
        # NOTE(sdague): exception logging bypasses the main stream
        # and goes to stderr. Suggests on a better way to do this are
        # welcomed.
        error = sys.stderr
        sys.stderr = io.StringIO()

        self.colorlog.info("foo")
        self.assertNotEqual(-1,
                            sys.stderr.getvalue().find("KeyError: 'missing'"))

        sys.stderr = error

    def _validate_keys(self, ctxt, keyed_log_string):
        infocolor = handlers.ColorHandler.LEVEL_COLORS[logging.INFO]
        warncolor = handlers.ColorHandler.LEVEL_COLORS[logging.WARN]
        info_msg = 'info'
        warn_msg = 'warn'
        infoexpected = "%s %s %s" % (infocolor, keyed_log_string, info_msg)
        warnexpected = "%s %s %s" % (warncolor, keyed_log_string, warn_msg)

        self.colorlog.info(info_msg, context=ctxt)
        self.assertIn(infoexpected, self.stream.getvalue())
        self.assertEqual('\033[00;36m', infocolor)

        self.colorlog.warn(warn_msg, context=ctxt)
        self.assertIn(infoexpected, self.stream.getvalue())
        self.assertIn(warnexpected, self.stream.getvalue())
        self.assertEqual('\033[01;33m', warncolor)

    def test_fancy_key_in_log_msg(self):
        ctxt = _fake_context()
        self._validate_keys(ctxt, '[%s]:' % ctxt.request_id)

    def test_instance_key_in_log_msg(self):
        ctxt = _fake_context()
        ctxt.resource_uuid = '1234'
        self._validate_keys(ctxt, ('[%s]: [instance: %s]' %
                                   (ctxt.request_id, ctxt.resource_uuid)))

    def test_resource_key_in_log_msg(self):
        color = handlers.ColorHandler.LEVEL_COLORS[logging.INFO]
        ctxt = _fake_context()
        resource = 'resource-202260f9-1224-490d-afaf-6a744c13141f'
        fake_resource = {'name': resource}
        message = 'info'
        self.colorlog.info(message, context=ctxt, resource=fake_resource)
        expected = ('%s [%s]: [%s] %s\033[00m\n' %
                    (color, ctxt.request_id, resource, message))
        self.assertEqual(expected, self.stream.getvalue())

    def test_resource_key_dict_in_log_msg(self):
        color = handlers.ColorHandler.LEVEL_COLORS[logging.INFO]
        ctxt = _fake_context()
        type = 'fake_resource'
        resource_id = '202260f9-1224-490d-afaf-6a744c13141f'
        fake_resource = {'type': type,
                         'id': resource_id}
        message = 'info'
        self.colorlog.info(message, context=ctxt, resource=fake_resource)
        expected = ('%s [%s]: [%s-%s] %s\033[00m\n' %
                    (color, ctxt.request_id, type, resource_id, message))
        self.assertEqual(expected, self.stream.getvalue())


class InstanceRecordTestCase(LogTestBase):
    def setUp(self):
        super(InstanceRecordTestCase, self).setUp()
        self.config(logging_context_format_string="[%(request_id)s]: "
                                                  "%(instance)s"
                                                  "%(resource)s"
                                                  "%(message)s",
                    logging_default_format_string="%(instance)s"
                                                  "%(resource)s"
                                                  "%(message)s")
        self.log = log.getLogger()
        self._add_handler_with_cleanup(self.log)
        self._set_log_level_with_cleanup(self.log, logging.DEBUG)

    def test_instance_dict_in_context_log_msg(self):
        ctxt = _fake_context()
        uuid = 'C9B7CCC6-8A12-4C53-A736-D7A1C36A62F3'
        fake_resource = {'uuid': uuid}
        message = 'info'
        self.log.info(message, context=ctxt, instance=fake_resource)
        expected = '[instance: %s]' % uuid
        self.assertIn(expected, self.stream.getvalue())

    def test_instance_dict_in_default_log_msg(self):
        uuid = 'C9B7CCC6-8A12-4C53-A736-D7A1C36A62F3'
        fake_resource = {'uuid': uuid}
        message = 'info'
        self.log.info(message, instance=fake_resource)
        expected = '[instance: %s]' % uuid
        self.assertIn(expected, self.stream.getvalue())

    def test_instance_uuid_as_arg_in_context_log_msg(self):
        ctxt = _fake_context()
        uuid = 'C9B7CCC6-8A12-4C53-A736-D7A1C36A62F3'
        message = 'info'
        self.log.info(message, context=ctxt, instance_uuid=uuid)
        expected = '[instance: %s]' % uuid
        self.assertIn(expected, self.stream.getvalue())

    def test_instance_uuid_as_arg_in_default_log_msg(self):
        uuid = 'C9B7CCC6-8A12-4C53-A736-D7A1C36A62F3'
        message = 'info'
        self.log.info(message, instance_uuid=uuid)
        expected = '[instance: %s]' % uuid
        self.assertIn(expected, self.stream.getvalue())

    def test_instance_uuid_from_context_in_context_log_msg(self):
        ctxt = _fake_context()
        ctxt.instance_uuid = 'CCCCCCCC-8A12-4C53-A736-D7A1C36A62F3'
        message = 'info'
        self.log.info(message, context=ctxt)
        expected = '[instance: %s]' % ctxt.instance_uuid
        self.assertIn(expected, self.stream.getvalue())

    def test_resource_uuid_from_context_in_context_log_msg(self):
        ctxt = _fake_context()
        ctxt.resource_uuid = 'RRRRRRRR-8A12-4C53-A736-D7A1C36A62F3'
        message = 'info'
        self.log.info(message, context=ctxt)
        expected = '[instance: %s]' % ctxt.resource_uuid
        self.assertIn(expected, self.stream.getvalue())

    def test_instance_from_context_in_context_log_msg(self):
        # NOTE: instance when passed in a context object is just a uuid.
        # When passed to the log record, it is a dict.
        ctxt = _fake_context()
        ctxt.instance = 'IIIIIIII-8A12-4C53-A736-D7A1C36A62F3'
        message = 'info'
        self.log.info(message, context=ctxt)
        expected = '[instance: %s]' % ctxt.instance
        self.assertIn(expected, self.stream.getvalue())


class TraceLevelTestCase(LogTestBase):
    def setUp(self):
        super(TraceLevelTestCase, self).setUp()
        self.config(logging_context_format_string="%(message)s")
        self.mylog = log.getLogger()
        self._add_handler_with_cleanup(self.mylog)
        self._set_log_level_with_cleanup(self.mylog, log.TRACE)

    def test_trace_log_msg(self):
        ctxt = _fake_context()
        message = 'my trace message'
        self.mylog.trace(message, context=ctxt)
        self.assertEqual('%s\n' % message, self.stream.getvalue())


class DomainTestCase(LogTestBase):
    def setUp(self):
        super(DomainTestCase, self).setUp()
        self.config(logging_context_format_string="[%(request_id)s]: "
                                                  "%(user_identity)s "
                                                  "%(message)s")
        self.mylog = log.getLogger()
        self._add_handler_with_cleanup(self.mylog)
        self._set_log_level_with_cleanup(self.mylog, logging.DEBUG)

    def _validate_keys(self, ctxt, keyed_log_string):
        info_message = 'info'
        infoexpected = "%s %s\n" % (keyed_log_string, info_message)
        warn_message = 'warn'
        warnexpected = "%s %s\n" % (keyed_log_string, warn_message)

        self.mylog.info(info_message, context=ctxt)
        self.assertEqual(infoexpected, self.stream.getvalue())

        self.mylog.warn(warn_message, context=ctxt)
        self.assertEqual(infoexpected + warnexpected, self.stream.getvalue())

    def test_domain_in_log_msg(self):
        ctxt = _fake_context()
        user_identity = ctxt.get_logging_values()['user_identity']
        self.assertIn(ctxt.domain, user_identity)
        self.assertIn(ctxt.project_domain, user_identity)
        self.assertIn(ctxt.user_domain, user_identity)
        self._validate_keys(ctxt, ('[%s]: %s' %
                                   (ctxt.request_id, user_identity)))


class SetDefaultsTestCase(BaseTestCase):
    class TestConfigOpts(cfg.ConfigOpts):
        def __call__(self, args=None):
            return cfg.ConfigOpts.__call__(self,
                                           args=args,
                                           prog='test',
                                           version='1.0',
                                           usage='%(prog)s FOO BAR',
                                           default_config_files=[])

    def setUp(self):
        super(SetDefaultsTestCase, self).setUp()
        self.conf = self.TestConfigOpts()
        self.conf.register_opts(_options.log_opts)
        self.conf.register_cli_opts(_options.logging_cli_opts)

        self._orig_defaults = dict([(o.dest, o.default)
                                    for o in _options.log_opts])
        self.addCleanup(self._restore_log_defaults)

    def _restore_log_defaults(self):
        for opt in _options.log_opts:
            opt.default = self._orig_defaults[opt.dest]

    def test_default_log_level_to_none(self):
        log.set_defaults(logging_context_format_string=None,
                         default_log_levels=None)
        self.conf([])
        self.assertEqual(_options.DEFAULT_LOG_LEVELS,
                         self.conf.default_log_levels)

    def test_default_log_level_method(self):
        self.assertEqual(_options.DEFAULT_LOG_LEVELS,
                         log.get_default_log_levels())

    def test_change_default(self):
        my_default = '%(asctime)s %(levelname)s %(name)s [%(request_id)s '\
                     '%(user_id)s %(project)s] %(instance)s'\
                     '%(message)s'
        log.set_defaults(logging_context_format_string=my_default)
        self.conf([])
        self.assertEqual(self.conf.logging_context_format_string, my_default)

    def test_change_default_log_level(self):
        package_log_level = 'foo=bar'
        log.set_defaults(default_log_levels=[package_log_level])
        self.conf([])
        self.assertEqual([package_log_level], self.conf.default_log_levels)
        self.assertIsNotNone(self.conf.logging_context_format_string)

    def test_tempest_set_log_file(self):
        log_file = 'foo.log'
        log.tempest_set_log_file(log_file)
        self.addCleanup(log.tempest_set_log_file, None)
        log.set_defaults()
        self.conf([])
        self.assertEqual(log_file, self.conf.log_file)

    def test_log_file_defaults_to_none(self):
        log.set_defaults()
        self.conf([])
        self.assertIsNone(self.conf.log_file)


@testtools.skipIf(platform.system() != 'Linux',
                  'pyinotify library works on Linux platform only.')
class FastWatchedFileHandlerTestCase(BaseTestCase):

    def setUp(self):
        super(FastWatchedFileHandlerTestCase, self).setUp()

    def _config(self):
        os_level, log_path = tempfile.mkstemp()
        log_dir_path = os.path.dirname(log_path)
        log_file_path = os.path.basename(log_path)
        self.CONF(['--log-dir', log_dir_path, '--log-file', log_file_path])
        self.config(use_stderr=False)
        self.config(watch_log_file=True)
        log.setup(self.CONF, 'test', 'test')
        return log_path

    def test_instantiate(self):
        self._config()
        logger = log._loggers[None].logger
        self.assertEqual(1, len(logger.handlers))
        from oslo_log import watchers
        self.assertIsInstance(logger.handlers[0],
                              watchers.FastWatchedFileHandler)

    def test_log(self):
        log_path = self._config()
        logger = log._loggers[None].logger
        text = 'Hello World!'
        logger.info(text)
        with open(log_path, 'r') as f:
            file_content = f.read()
        self.assertIn(text, file_content)

    def test_move(self):
        log_path = self._config()
        os_level_dst, log_path_dst = tempfile.mkstemp()
        os.rename(log_path, log_path_dst)
        time.sleep(6)
        self.assertTrue(os.path.exists(log_path))

    def test_remove(self):
        log_path = self._config()
        os.remove(log_path)
        time.sleep(6)
        self.assertTrue(os.path.exists(log_path))


class MutateTestCase(BaseTestCase):
    def setUp(self):
        super(MutateTestCase, self).setUp()
        if hasattr(log._load_log_config, 'old_time'):
            del log._load_log_config.old_time

    def setup_confs(self, *confs):
        paths = self.create_tempfiles(
            ('conf_%d' % i, conf) for i, conf in enumerate(confs))
        self.CONF(['--config-file', paths[0]])
        return paths

    def test_debug(self):
        paths = self.setup_confs(
            "[DEFAULT]\ndebug = false\n",
            "[DEFAULT]\ndebug = true\n")
        log_root = log.getLogger(None).logger
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        self.assertEqual(False, self.CONF.debug)
        self.assertEqual(log.INFO, log_root.getEffectiveLevel())

        shutil.copy(paths[1], paths[0])
        self.CONF.mutate_config_files()

        self.assertEqual(True, self.CONF.debug)
        self.assertEqual(log.DEBUG, log_root.getEffectiveLevel())

    @mock.patch.object(logging.config, "fileConfig")
    def test_log_config_append(self, mock_fileConfig):
        logini = self.create_tempfiles([('log.ini', MIN_LOG_INI)])[0]
        paths = self.setup_confs(
            "[DEFAULT]\nlog_config_append = no_exist\n",
            "[DEFAULT]\nlog_config_append = %s\n" % logini)
        self.assertRaises(log.LogConfigError, log.setup, self.CONF, '')
        self.assertFalse(mock_fileConfig.called)

        shutil.copy(paths[1], paths[0])
        self.CONF.mutate_config_files()

        mock_fileConfig.assert_called_once_with(
            logini, disable_existing_loggers=False)

    @mock.patch.object(logging.config, "fileConfig")
    def test_log_config_append_no_touch(self, mock_fileConfig):
        logini = self.create_tempfiles([('log.ini', MIN_LOG_INI)])[0]
        self.setup_confs("[DEFAULT]\nlog_config_append = %s\n" % logini)
        log.setup(self.CONF, '')
        mock_fileConfig.assert_called_once_with(
            logini, disable_existing_loggers=False)
        mock_fileConfig.reset_mock()

        self.CONF.mutate_config_files()

        self.assertFalse(mock_fileConfig.called)

    @mock.patch.object(logging.config, "fileConfig")
    def test_log_config_append_touch(self, mock_fileConfig):
        logini = self.create_tempfiles([('log.ini', MIN_LOG_INI)])[0]
        self.setup_confs("[DEFAULT]\nlog_config_append = %s\n" % logini)
        log.setup(self.CONF, '')
        mock_fileConfig.assert_called_once_with(
            logini, disable_existing_loggers=False)
        mock_fileConfig.reset_mock()

        # No thread sync going on here, just ensure the mtimes are different
        time.sleep(1)
        os.utime(logini, None)
        self.CONF.mutate_config_files()

        mock_fileConfig.assert_called_once_with(
            logini, disable_existing_loggers=False)

    def mk_log_config(self, data):
        """Turns a dictConfig-like structure into one suitable for fileConfig.

        The schema is not validated as this is a test helper not production
        code. Garbage in, garbage out. Particularly, don't try to use filters,
        fileConfig doesn't support them.

        Handler args must be passed like 'args': (1, 2). dictConfig passes
        keys by keyword name and fileConfig passes them by position so
        accepting the dictConfig form makes it nigh impossible to produce the
        fileConfig form.

        I traverse dicts by sorted keys for output stability but it doesn't
        matter if defaulted keys are out of order.
        """
        lines = []
        for section in ['formatters', 'handlers', 'loggers']:
            items = data.get(section, {})
            keys = sorted(items)
            skeys = ",".join(keys)
            if section == 'loggers' and 'root' in data:
                skeys = ("root," + skeys) if skeys else "root"
            lines.extend(["[%s]" % section,
                          "keys=%s" % skeys])
            for key in keys:
                lines.extend(["",
                              "[%s_%s]" % (section[:-1], key)])
                item = items[key]
                lines.extend("%s=%s" % (k, item[k]) for k in sorted(item))
                if section == 'handlers':
                    if 'args' not in item:
                        lines.append("args=()")
                elif section == 'loggers':
                    lines.append("qualname=%s" % key)
                    if 'handlers' not in item:
                        lines.append("handlers=")
            lines.append("")
        root = data.get('root', {})
        if root:
            lines.extend(["[logger_root]"])
            lines.extend("%s=%s" % (k, root[k]) for k in sorted(root))
            if 'handlers' not in root:
                lines.append("handlers=")
        return "\n".join(lines)

    def test_mk_log_config_full(self):
        data = {'loggers': {'aaa': {'level': 'INFO'},
                            'bbb': {'level': 'WARN',
                                    'propagate': False}},
                'handlers': {'aaa': {'level': 'INFO'},
                             'bbb': {'level': 'WARN',
                                     'propagate': False,
                                     'args': (1, 2)}},
                'formatters': {'aaa': {'level': 'INFO'},
                               'bbb': {'level': 'WARN',
                                       'propagate': False}},
                'root': {'level': 'INFO',
                         'handlers': 'aaa'},
                }
        full = """[formatters]
keys=aaa,bbb

[formatter_aaa]
level=INFO

[formatter_bbb]
level=WARN
propagate=False

[handlers]
keys=aaa,bbb

[handler_aaa]
level=INFO
args=()

[handler_bbb]
args=(1, 2)
level=WARN
propagate=False

[loggers]
keys=root,aaa,bbb

[logger_aaa]
level=INFO
qualname=aaa
handlers=

[logger_bbb]
level=WARN
propagate=False
qualname=bbb
handlers=

[logger_root]
handlers=aaa
level=INFO"""
        self.assertEqual(full, self.mk_log_config(data))

    def test_mk_log_config_empty(self):
        """Ensure mk_log_config tolerates missing bits"""
        empty = """[formatters]
keys=

[handlers]
keys=

[loggers]
keys=
"""
        self.assertEqual(empty, self.mk_log_config({}))

    @contextmanager
    def mutate_conf(self, conf1, conf2):
        loginis = self.create_tempfiles([
            ('log1.ini', self.mk_log_config(conf1)),
            ('log2.ini', self.mk_log_config(conf2))])
        confs = self.setup_confs(
            "[DEFAULT]\nlog_config_append = %s\n" % loginis[0],
            "[DEFAULT]\nlog_config_append = %s\n" % loginis[1])
        log.setup(self.CONF, '')

        yield loginis, confs
        shutil.copy(confs[1], confs[0])
        # prevent the mtime ever matching
        os.utime(self.CONF.log_config_append, (0, 0))
        self.CONF.mutate_config_files()

    @mock.patch.object(logging.config, "fileConfig")
    def test_log_config_append_change_file(self, mock_fileConfig):
        with self.mutate_conf({}, {}) as (loginis, confs):
            mock_fileConfig.assert_called_once_with(
                loginis[0], disable_existing_loggers=False)
            mock_fileConfig.reset_mock()

        mock_fileConfig.assert_called_once_with(
            loginis[1], disable_existing_loggers=False)

    def set_root_stream(self):
        root = logging.getLogger()
        self.assertEqual(1, len(root.handlers))
        handler = root.handlers[0]
        handler.stream = io.StringIO()
        return handler.stream

    def test_remove_handler(self):
        fake_handler = {'class': 'logging.StreamHandler',
                        'args': ()}
        conf1 = {'root': {'handlers': 'fake'},
                 'handlers': {'fake': fake_handler}}
        conf2 = {'root': {'handlers': ''}}
        with self.mutate_conf(conf1, conf2) as (loginis, confs):
            stream = self.set_root_stream()
            root = logging.getLogger()
            root.error("boo")
            self.assertEqual("boo\n", stream.getvalue())
        stream.truncate(0)
        root.error("boo")
        self.assertEqual("", stream.getvalue())

    def test_remove_logger(self):
        fake_handler = {'class': 'logging.StreamHandler'}
        fake_logger = {'level': 'WARN'}
        conf1 = {'root': {'handlers': 'fake'},
                 'handlers': {'fake': fake_handler},
                 'loggers': {'a.a': fake_logger}}
        conf2 = {'root': {'handlers': 'fake'},
                 'handlers': {'fake': fake_handler}}
        stream = io.StringIO()
        with self.mutate_conf(conf1, conf2) as (loginis, confs):
            stream = self.set_root_stream()
            log = logging.getLogger("a.a")
            log.info("info")
            log.warn("warn")
            self.assertEqual("warn\n", stream.getvalue())
        stream = self.set_root_stream()
        log.info("info")
        log.warn("warn")
        self.assertEqual("info\nwarn\n", stream.getvalue())


class LogConfigOptsTestCase(BaseTestCase):

    def setUp(self):
        super(LogConfigOptsTestCase, self).setUp()

    def test_print_help(self):
        f = io.StringIO()
        self.CONF([])
        self.CONF.print_help(file=f)
        for option in ['debug', 'log-config', 'watch-log-file']:
            self.assertIn(option, f.getvalue())

    def test_debug(self):
        self.CONF(['--debug'])
        self.assertEqual(True, self.CONF.debug)

    def test_logging_opts(self):
        self.CONF([])

        self.assertIsNone(self.CONF.log_config_append)
        self.assertIsNone(self.CONF.log_file)
        self.assertIsNone(self.CONF.log_dir)

        self.assertEqual(_options._DEFAULT_LOG_DATE_FORMAT,
                         self.CONF.log_date_format)

        self.assertEqual(False, self.CONF.use_syslog)
        self.assertEqual(False, self.CONF.use_json)

    def test_log_file(self):
        log_file = '/some/path/foo-bar.log'
        self.CONF(['--log-file', log_file])
        self.assertEqual(log_file, self.CONF.log_file)

    def test_log_dir_handlers(self):
        log_dir = tempfile.mkdtemp()
        self.CONF(['--log-dir', log_dir])
        self.CONF.set_default('use_stderr', False)
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        logger = log._loggers[None].logger
        self.assertEqual(1, len(logger.handlers))
        self.assertIsInstance(logger.handlers[0],
                              logging.handlers.WatchedFileHandler)

    def test_log_publish_errors_handlers(self):
        fake_handler = mock.MagicMock()
        with mock.patch('oslo_utils.importutils.import_object',
                        return_value=fake_handler) as mock_import:
            log_dir = tempfile.mkdtemp()
            self.CONF(['--log-dir', log_dir])
            self.CONF.set_default('use_stderr', False)
            self.CONF.set_default('publish_errors', True)
            log._setup_logging_from_conf(self.CONF, 'test', 'test')
            logger = log._loggers[None].logger
            self.assertEqual(2, len(logger.handlers))
            self.assertIsInstance(logger.handlers[0],
                                  logging.handlers.WatchedFileHandler)
            self.assertEqual(fake_handler, logger.handlers[1])
            mock_import.assert_called_once_with(
                'oslo_messaging.notify.log_handler.PublishErrorsHandler',
                logging.ERROR)

    def test_logfile_deprecated(self):
        logfile = '/some/other/path/foo-bar.log'
        self.CONF(['--logfile', logfile])
        self.assertEqual(logfile, self.CONF.log_file)

    def test_log_dir(self):
        log_dir = '/some/path/'
        self.CONF(['--log-dir', log_dir])
        self.assertEqual(log_dir, self.CONF.log_dir)

    def test_logdir_deprecated(self):
        logdir = '/some/other/path/'
        self.CONF(['--logdir', logdir])
        self.assertEqual(logdir, self.CONF.log_dir)

    def test_default_formatter(self):
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        logger = log._loggers[None].logger
        for handler in logger.handlers:
            formatter = handler.formatter
            self.assertIsInstance(formatter,
                                  formatters.ContextFormatter)

    def test_json_formatter(self):
        self.CONF(['--use-json'])
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        logger = log._loggers[None].logger
        for handler in logger.handlers:
            formatter = handler.formatter
            self.assertIsInstance(formatter,
                                  formatters.JSONFormatter)

    def test_handlers_cleanup(self):
        """Test that all old handlers get removed from log_root."""
        old_handlers = [log.handlers.ColorHandler(),
                        log.handlers.ColorHandler()]
        log._loggers[None].logger.handlers = list(old_handlers)
        log._setup_logging_from_conf(self.CONF, 'test', 'test')
        handlers = log._loggers[None].logger.handlers
        self.assertEqual(1, len(handlers))
        self.assertNotIn(handlers[0], old_handlers)

    def test_list_opts(self):
        all_options = _options.list_opts()
        (group, options) = all_options[0]
        self.assertIsNone(group)
        self.assertEqual((_options.common_cli_opts +
                          _options.logging_cli_opts +
                          _options.generic_log_opts +
                          _options.log_opts +
                          _options.versionutils.deprecated_opts), options)


class LogConfigTestCase(BaseTestCase):
    def setUp(self):
        super(LogConfigTestCase, self).setUp()
        names = self.create_tempfiles([('logging', MIN_LOG_INI)])
        self.log_config_append = names[0]
        if hasattr(log._load_log_config, 'old_time'):
            del log._load_log_config.old_time

    def test_log_config_append_ok(self):
        self.config(log_config_append=self.log_config_append)
        log.setup(self.CONF, 'test_log_config_append')

    def test_log_config_append_not_exist(self):
        os.remove(self.log_config_append)
        self.config(log_config_append=self.log_config_append)
        self.assertRaises(log.LogConfigError, log.setup,
                          self.CONF,
                          'test_log_config_append')

    def test_log_config_append_invalid(self):
        names = self.create_tempfiles([('logging', 'squawk')])
        self.log_config_append = names[0]
        self.config(log_config_append=self.log_config_append)
        self.assertRaises(log.LogConfigError, log.setup,
                          self.CONF,
                          'test_log_config_append')

    def test_log_config_append_unreadable(self):
        os.chmod(self.log_config_append, 0)
        self.config(log_config_append=self.log_config_append)
        self.assertRaises(log.LogConfigError, log.setup,
                          self.CONF,
                          'test_log_config_append')

    def test_log_config_append_disable_existing_loggers(self):
        self.config(log_config_append=self.log_config_append)
        with mock.patch('logging.config.fileConfig') as fileConfig:
            log.setup(self.CONF, 'test_log_config_append')

        fileConfig.assert_called_once_with(self.log_config_append,
                                           disable_existing_loggers=False)


class SavingAdapter(log.KeywordArgumentAdapter):

    def __init__(self, *args, **kwds):
        super(log.KeywordArgumentAdapter, self).__init__(*args, **kwds)
        self.results = []

    def process(self, msg, kwargs):
        # Run the real adapter and save the inputs and outputs
        # before returning them so the test can examine both.
        results = super(SavingAdapter, self).process(msg, kwargs)
        self.results.append((msg, kwargs, results))
        return results


class KeywordArgumentAdapterTestCase(BaseTestCase):

    def setUp(self):
        super(KeywordArgumentAdapterTestCase, self).setUp()
        # Construct a mock that will look like a Logger configured to
        # emit messages at DEBUG or higher.
        self.mock_log = mock.Mock()
        self.mock_log.manager.disable = logging.NOTSET
        self.mock_log.isEnabledFor.return_value = True
        self.mock_log.getEffectiveLevel.return_value = logging.DEBUG

    def test_empty_kwargs(self):
        a = log.KeywordArgumentAdapter(self.mock_log, {})
        msg, kwargs = a.process('message', {})
        self.assertEqual({'extra': {'extra_keys': []}}, kwargs)

    def test_include_constructor_extras(self):
        key = 'foo'
        val = 'blah'
        data = {key: val}
        a = log.KeywordArgumentAdapter(self.mock_log, data)
        msg, kwargs = a.process('message', {})
        self.assertEqual({'extra': {key: val, 'extra_keys': [key]}},
                         kwargs)

    def test_pass_through_exc_info(self):
        a = log.KeywordArgumentAdapter(self.mock_log, {})
        exc_message = 'exception'
        msg, kwargs = a.process('message', {'exc_info': exc_message})
        self.assertEqual(
            {'extra': {'extra_keys': []},
             'exc_info': exc_message},
            kwargs)

    def test_update_extras(self):
        a = log.KeywordArgumentAdapter(self.mock_log, {})
        data = {'context': 'some context object',
                'instance': 'instance identifier',
                'resource_uuid': 'UUID for instance',
                'anything': 'goes'}
        expected = copy.copy(data)

        msg, kwargs = a.process('message', data)
        self.assertEqual(
            {'extra': {'anything': expected['anything'],
                       'context': expected['context'],
                       'extra_keys': sorted(expected.keys()),
                       'instance': expected['instance'],
                       'resource_uuid': expected['resource_uuid']}},
            kwargs)

    def test_pass_args_to_log(self):
        a = SavingAdapter(self.mock_log, {})

        message = 'message'
        exc_message = 'exception'
        val = 'value'
        a.log(logging.DEBUG, message, name=val, exc_info=exc_message)

        expected = {
            'exc_info': exc_message,
            'extra': {'name': val, 'extra_keys': ['name']},
        }

        actual = a.results[0]
        self.assertEqual(message, actual[0])
        self.assertEqual(expected, actual[1])
        results = actual[2]
        self.assertEqual(message, results[0])
        self.assertEqual(expected, results[1])

    def test_pass_args_via_debug(self):

        a = SavingAdapter(self.mock_log, {})
        message = 'message'
        exc_message = 'exception'
        val = 'value'
        a.debug(message, name=val, exc_info=exc_message)

        expected = {
            'exc_info': exc_message,
            'extra': {'name': val, 'extra_keys': ['name']},
        }

        actual = a.results[0]
        self.assertEqual(message, actual[0])
        self.assertEqual(expected, actual[1])
        results = actual[2]
        self.assertEqual(message, results[0])
        self.assertEqual(expected, results[1])


class UnicodeConversionTestCase(BaseTestCase):

    _MSG = u'Message with unicode char \ua000 in the middle'

    def test_ascii_to_unicode(self):
        msg = self._MSG
        enc_msg = msg.encode('utf-8')
        result = formatters._ensure_unicode(enc_msg)
        self.assertEqual(msg, result)
        self.assertIsInstance(result, str)

    def test_unicode_to_unicode(self):
        msg = self._MSG
        result = formatters._ensure_unicode(msg)
        self.assertEqual(msg, result)
        self.assertIsInstance(result, str)

    def test_exception_to_unicode(self):
        msg = self._MSG
        exc = Exception(msg)
        result = formatters._ensure_unicode(exc)
        self.assertEqual(msg, result)
        self.assertIsInstance(result, str)


class LoggerNameTestCase(LoggerTestCase):

    def test_oslo_dot(self):
        logger_name = 'oslo.subname'
        logger = log.getLogger(logger_name)
        self.assertEqual(logger_name, logger.logger.name)

    def test_oslo_underscore(self):
        logger_name = 'oslo_subname'
        expected = logger_name.replace('_', '.')
        logger = log.getLogger(logger_name)
        self.assertEqual(expected, logger.logger.name)


class IsDebugEnabledTestCase(test_base.BaseTestCase):
    def setUp(self):
        super(IsDebugEnabledTestCase, self).setUp()
        self.config_fixture = self.useFixture(
            fixture_config.Config(cfg.ConfigOpts()))
        self.config = self.config_fixture.config
        self.CONF = self.config_fixture.conf
        log.register_options(self.config_fixture.conf)

    def _test_is_debug_enabled(self, debug=False):
        self.config(debug=debug)
        self.assertEqual(debug, log.is_debug_enabled(self.CONF))

    def test_is_debug_enabled_off(self):
        self._test_is_debug_enabled()

    def test_is_debug_enabled_on(self):
        self._test_is_debug_enabled(debug=True)
