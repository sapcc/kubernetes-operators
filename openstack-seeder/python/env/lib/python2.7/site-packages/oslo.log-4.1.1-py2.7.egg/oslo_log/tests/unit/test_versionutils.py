# Copyright (c) 2013 OpenStack Foundation
# All Rights Reserved.
#
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

from unittest import mock

from oslotest import base as test_base
from testtools import matchers

from oslo_log import versionutils


class DeprecatedTestCase(test_base.BaseTestCase):
    def assert_deprecated(self, mock_reporter, no_removal=False,
                          **expected_details):
        if 'in_favor_of' in expected_details:
            if no_removal is False:
                expected_msg = versionutils._deprecated_msg_with_alternative
            else:
                expected_msg = getattr(
                    versionutils,
                    '_deprecated_msg_with_alternative_no_removal')
        else:
            if no_removal is False:
                expected_msg = versionutils._deprecated_msg_no_alternative
            else:
                expected_msg = getattr(
                    versionutils,
                    '_deprecated_msg_with_no_alternative_no_removal')
        # The first argument is the logger, and we don't care about
        # that, so ignore it with ANY.
        mock_reporter.assert_called_with(mock.ANY,
                                         expected_msg,
                                         expected_details)

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecating_a_function_returns_correct_value(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.ICEHOUSE)
        def do_outdated_stuff(data):
            return data

        expected_rv = 'expected return value'
        retval = do_outdated_stuff(expected_rv)

        self.assertThat(retval, matchers.Equals(expected_rv))

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecating_a_method_returns_correct_value(self, mock_reporter):

        class C(object):
            @versionutils.deprecated(as_of=versionutils.deprecated.ICEHOUSE)
            def outdated_method(self, *args):
                return args

        retval = C().outdated_method(1, 'of anything')

        self.assertThat(retval, matchers.Equals((1, 'of anything')))

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_unknown_future_release(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.BEXAR,
                                 in_favor_of='different_stuff()')
        def do_outdated_stuff():
            return

        do_outdated_stuff()

        self.assert_deprecated(mock_reporter,
                               what='do_outdated_stuff()',
                               in_favor_of='different_stuff()',
                               as_of='Bexar',
                               remove_in='D')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_known_future_release(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY,
                                 in_favor_of='different_stuff()')
        def do_outdated_stuff():
            return

        do_outdated_stuff()

        self.assert_deprecated(mock_reporter,
                               what='do_outdated_stuff()',
                               in_favor_of='different_stuff()',
                               as_of='Grizzly',
                               remove_in='Icehouse')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_without_replacement(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY)
        def do_outdated_stuff():
            return

        do_outdated_stuff()

        self.assert_deprecated(mock_reporter,
                               what='do_outdated_stuff()',
                               as_of='Grizzly',
                               remove_in='Icehouse')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_custom_what(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY,
                                 what='v2.0 API',
                                 in_favor_of='v3 API')
        def do_outdated_stuff():
            return

        do_outdated_stuff()

        self.assert_deprecated(mock_reporter,
                               what='v2.0 API',
                               in_favor_of='v3 API',
                               as_of='Grizzly',
                               remove_in='Icehouse')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_removed_next_release(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY,
                                 remove_in=1)
        def do_outdated_stuff():
            return

        do_outdated_stuff()

        self.assert_deprecated(mock_reporter,
                               what='do_outdated_stuff()',
                               as_of='Grizzly',
                               remove_in='Havana')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_removed_plus_3(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY,
                                 remove_in=+3)
        def do_outdated_stuff():
            return

        do_outdated_stuff()

        self.assert_deprecated(mock_reporter,
                               what='do_outdated_stuff()',
                               as_of='Grizzly',
                               remove_in='Juno')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_removed_zero(self, mock_reporter):
        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY,
                                 remove_in=0)
        def do_outdated_stuff():
            return

        do_outdated_stuff()
        self.assert_deprecated(mock_reporter,
                               no_removal=True,
                               what='do_outdated_stuff()',
                               as_of='Grizzly',
                               remove_in='Grizzly')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_removed_none(self, mock_reporter):
        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY,
                                 remove_in=None)
        def do_outdated_stuff():
            return

        do_outdated_stuff()
        self.assert_deprecated(mock_reporter,
                               no_removal=True,
                               what='do_outdated_stuff()',
                               as_of='Grizzly',
                               remove_in='Grizzly')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_with_removed_zero_and_alternative(self, mock_reporter):
        @versionutils.deprecated(as_of=versionutils.deprecated.GRIZZLY,
                                 in_favor_of='different_stuff()',
                                 remove_in=0)
        def do_outdated_stuff():
            return

        do_outdated_stuff()
        self.assert_deprecated(mock_reporter,
                               no_removal=True,
                               what='do_outdated_stuff()',
                               as_of='Grizzly',
                               in_favor_of='different_stuff()',
                               remove_in='Grizzly')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_class_without_init(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.JUNO,
                                 remove_in=+1)
        class OutdatedClass(object):
            pass
        obj = OutdatedClass()

        self.assertIsInstance(obj, OutdatedClass)
        self.assert_deprecated(mock_reporter,
                               what='OutdatedClass()',
                               as_of='Juno',
                               remove_in='Kilo')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_class_with_init(self, mock_reporter):
        mock_arguments = mock.MagicMock()
        args = (1, 5, 7)
        kwargs = {'first': 10, 'second': 20}

        @versionutils.deprecated(as_of=versionutils.deprecated.JUNO,
                                 remove_in=+1)
        class OutdatedClass(object):
            def __init__(self, *args, **kwargs):
                """It is __init__ method."""
                mock_arguments.args = args
                mock_arguments.kwargs = kwargs
                super(OutdatedClass, self).__init__()
        obj = OutdatedClass(*args, **kwargs)

        self.assertIsInstance(obj, OutdatedClass)
        self.assertEqual('__init__', obj.__init__.__name__)
        self.assertEqual('It is __init__ method.', obj.__init__.__doc__)
        self.assertEqual(args, mock_arguments.args)
        self.assertEqual(kwargs, mock_arguments.kwargs)
        self.assert_deprecated(mock_reporter,
                               what='OutdatedClass()',
                               as_of='Juno',
                               remove_in='Kilo')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_exception_old(self, mock_log):
        @versionutils.deprecated(as_of=versionutils.deprecated.ICEHOUSE,
                                 remove_in=+1)
        class OldException(Exception):
            pass

        try:
            raise OldException()
        except OldException:
            pass

        self.assert_deprecated(mock_log, what='OldException()',
                               as_of='Icehouse', remove_in='Juno')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_exception_new(self, mock_log):
        @versionutils.deprecated(as_of=versionutils.deprecated.ICEHOUSE,
                                 remove_in=+1)
        class OldException(Exception):
            pass

        class NewException(OldException):
            pass

        try:
            raise NewException()
        except NewException:
            pass

        mock_log.assert_not_called()

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_exception_unrelated(self, mock_log):
        @versionutils.deprecated(as_of=versionutils.deprecated.ICEHOUSE,
                                 remove_in=+1)
        class OldException(Exception):
            pass

        class UnrelatedException(Exception):
            pass

        try:
            raise UnrelatedException()
        except UnrelatedException:
            pass

        mock_log.assert_not_called()

    @mock.patch.object(versionutils.CONF, 'register_opts')
    def test_register_options(self, mock_register_opts):
        # Calling register_options registers the config options.

        versionutils.register_options()

        mock_register_opts.assert_called_once_with(
            versionutils.deprecated_opts)

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_mitaka_plus_two(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.MITAKA,
                                 remove_in=+2)
        class OutdatedClass(object):
            pass
        obj = OutdatedClass()

        self.assertIsInstance(obj, OutdatedClass)
        self.assert_deprecated(mock_reporter,
                               what='OutdatedClass()',
                               as_of='Mitaka',
                               remove_in='Ocata')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_newton_plus_two(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.NEWTON,
                                 remove_in=+2)
        class OutdatedClass(object):
            pass
        obj = OutdatedClass()

        self.assertIsInstance(obj, OutdatedClass)
        self.assert_deprecated(mock_reporter,
                               what='OutdatedClass()',
                               as_of='Newton',
                               remove_in='Pike')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_ocata_plus_two(self, mock_reporter):

        @versionutils.deprecated(as_of=versionutils.deprecated.OCATA,
                                 remove_in=+2)
        class OutdatedClass(object):
            pass
        obj = OutdatedClass()

        self.assertIsInstance(obj, OutdatedClass)
        self.assert_deprecated(mock_reporter,
                               what='OutdatedClass()',
                               as_of='Ocata',
                               remove_in='Queens')

    @mock.patch('oslo_log.versionutils.report_deprecated_feature')
    def test_deprecated_message(self, mock_reporter):

        versionutils.deprecation_warning('outdated_stuff',
                                         as_of=versionutils.deprecated.KILO,
                                         in_favor_of='different_stuff',
                                         remove_in=+2)

        self.assert_deprecated(mock_reporter,
                               what='outdated_stuff',
                               in_favor_of='different_stuff',
                               as_of='Kilo',
                               remove_in='Mitaka')
