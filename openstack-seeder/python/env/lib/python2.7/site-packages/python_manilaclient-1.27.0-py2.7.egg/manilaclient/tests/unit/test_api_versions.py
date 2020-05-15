# Copyright 2015 Chuck Fouts
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

import ddt
import mock
import six

import manilaclient
from manilaclient import api_versions
from manilaclient.common import cliutils
from manilaclient import exceptions
from manilaclient.tests.unit import utils


@ddt.ddt
class APIVersionTestCase(utils.TestCase):
    def test_valid_version_strings(self):
        def _test_string(version, exp_major, exp_minor):
            v = api_versions.APIVersion(version)
            self.assertEqual(v.ver_major, exp_major)
            self.assertEqual(v.ver_minor, exp_minor)

        _test_string("1.1", 1, 1)
        _test_string("2.10", 2, 10)
        _test_string("5.234", 5, 234)
        _test_string("12.5", 12, 5)
        _test_string("2.0", 2, 0)
        _test_string("2.200", 2, 200)

    def test_null_version(self):
        v = api_versions.APIVersion()
        self.assertTrue(v.is_null())
        self.assertEqual(repr(v), "<APIVersion: null>")

    @ddt.data(
        "2",
        "200",
        "2.1.4",
        "200.23.66.3",
        "5 .3",
        "5. 3",
        "5.03",
        "02.1",
        "2.001",
        "",
        " 2.1",
        "2.1 ",
        "2.",
    )
    def test_invalid_version_strings(self, version):
        self.assertRaises(exceptions.UnsupportedVersion,
                          api_versions.APIVersion, version)

    def test_version_comparisons(self):
        v1 = api_versions.APIVersion("2.0")
        v2 = api_versions.APIVersion("2.5")
        v3 = api_versions.APIVersion("5.23")
        v4 = api_versions.APIVersion("2.0")
        v5 = api_versions.APIVersion("1.0")
        v_null = api_versions.APIVersion()

        self.assertLess(v1, v2)
        self.assertGreater(v3, v2)
        self.assertNotEqual(v1, v2)
        self.assertEqual(v1, v4)
        self.assertNotEqual(v1, v_null)
        self.assertLess(v5, v1)
        self.assertLess(v5, v2)
        self.assertEqual(v_null, v_null)
        self.assertRaises(TypeError, v1.__le__, "2.1")
        self.assertRaises(TypeError, v1.__eq__, "2.1")
        self.assertRaises(TypeError, v1.__gt__, "2.1")

    def test_version_matches(self):
        v1 = api_versions.APIVersion("2.0")
        v2 = api_versions.APIVersion("2.5")
        v3 = api_versions.APIVersion("2.45")
        v4 = api_versions.APIVersion("3.3")
        v5 = api_versions.APIVersion("3.23")
        v6 = api_versions.APIVersion("2.0")
        v7 = api_versions.APIVersion("3.3")
        v8 = api_versions.APIVersion("4.0")
        v_null = api_versions.APIVersion()

        v1_25 = api_versions.APIVersion("2.5")
        v1_32 = api_versions.APIVersion("3.32")
        v1_33 = api_versions.APIVersion("3.33")
        self.assertTrue(v2.matches(v1, v3))
        self.assertTrue(v2.matches(v1, v_null))

        self.assertTrue(v1_32.matches(v1_25, v1_33))

        self.assertTrue(v1.matches(v6, v2))
        self.assertTrue(v4.matches(v2, v7))
        self.assertTrue(v4.matches(v_null, v7))
        self.assertTrue(v4.matches(v_null, v8))
        self.assertFalse(v1.matches(v2, v3))
        self.assertFalse(v5.matches(v2, v4))
        self.assertFalse(v2.matches(v3, v1))

        self.assertRaises(ValueError, v_null.matches, v1, v3)

    def test_get_string(self):
        v1_string = "3.23"
        v1 = api_versions.APIVersion(v1_string)
        self.assertEqual(v1_string, v1.get_string())

        self.assertRaises(ValueError,
                          api_versions.APIVersion().get_string)

    @ddt.data("2.0",
              "2.5",
              "2.45",
              "3.3",
              "3.23",
              "2.0",
              "3.3",
              "4.0")
    def test_representation(self, version):
        version_major, version_minor = version.split('.')
        api_version = api_versions.APIVersion(version)
        self.assertEqual(six.text_type(api_version),
                         ("API Version Major: %s, Minor: %s" %
                          (version_major, version_minor)))
        self.assertEqual(repr(api_version), "<APIVersion: %s>" % version)

    def test_is_latest(self):
        v1 = api_versions.APIVersion("1.0")
        self.assertFalse(v1.is_latest())
        v_latest = api_versions.APIVersion(api_versions.MAX_VERSION)
        self.assertTrue(v_latest.is_latest())


class GetAPIVersionTestCase(utils.TestCase):

    def test_wrong_format(self):
        self.assertRaises(exceptions.UnsupportedVersion,
                          api_versions.get_api_version, "something_wrong")

    def test_wrong_major_version(self):
        self.assertRaises(exceptions.UnsupportedVersion,
                          api_versions.get_api_version, "1")

    @mock.patch("manilaclient.api_versions.APIVersion")
    def test_major_and_minor_parts_is_presented(self, mock_apiversion):
        version = "2.7"
        self.assertEqual(mock_apiversion.return_value,
                         api_versions.get_api_version(version))
        mock_apiversion.assert_called_once_with(version)


class WrapsTestCase(utils.TestCase):

    def _get_obj_with_vers(self, vers):
        return mock.MagicMock(api_version=api_versions.APIVersion(vers))

    def _side_effect_of_vers_method(self, *args, **kwargs):
        m = mock.MagicMock(start_version=args[1], end_version=args[2])
        m.name = args[0]
        return m

    @mock.patch("manilaclient.utils.get_function_name")
    @mock.patch("manilaclient.api_versions.VersionedMethod")
    def test_end_version_is_none(self, mock_versioned_method, mock_name):
        func_name = 'foo'
        mock_name.return_value = func_name
        mock_versioned_method.side_effect = self._side_effect_of_vers_method

        @api_versions.wraps('2.2')
        def foo(*args, **kwargs):
            pass

        foo(self._get_obj_with_vers('2.4'))

        mock_versioned_method.assert_called_once_with(
            func_name, api_versions.APIVersion('2.2'),
            api_versions.APIVersion(api_versions.MAX_VERSION), mock.ANY)

    @mock.patch("manilaclient.utils.get_function_name")
    @mock.patch("manilaclient.api_versions.VersionedMethod")
    def test_start_and_end_version_are_presented(self, mock_versioned_method,
                                                 mock_name):
        func_name = "foo"
        mock_name.return_value = func_name
        mock_versioned_method.side_effect = self._side_effect_of_vers_method

        @api_versions.wraps("2.2", "2.6")
        def foo(*args, **kwargs):
            pass

        foo(self._get_obj_with_vers("2.4"))

        mock_versioned_method.assert_called_once_with(
            func_name, api_versions.APIVersion("2.2"),
            api_versions.APIVersion("2.6"), mock.ANY)

    @mock.patch("manilaclient.utils.get_function_name")
    @mock.patch("manilaclient.api_versions.VersionedMethod")
    def test_api_version_doesnt_match(self, mock_versioned_method, mock_name):
        func_name = "foo"
        mock_name.return_value = func_name
        mock_versioned_method.side_effect = self._side_effect_of_vers_method

        @api_versions.wraps("2.2", "2.6")
        def foo(*args, **kwargs):
            pass

        self.assertRaises(exceptions.UnsupportedVersion,
                          foo, self._get_obj_with_vers("2.1"))

        mock_versioned_method.assert_called_once_with(
            func_name, api_versions.APIVersion("2.2"),
            api_versions.APIVersion("2.6"), mock.ANY)

    def test_define_method_is_actually_called(self):
        checker = mock.MagicMock()

        @api_versions.wraps("2.2", "2.6")
        def some_func(*args, **kwargs):
            checker(*args, **kwargs)

        obj = self._get_obj_with_vers("2.4")
        some_args = ("arg_1", "arg_2")
        some_kwargs = {"key1": "value1", "key2": "value2"}

        some_func(obj, *some_args, **some_kwargs)

        checker.assert_called_once_with(*((obj,) + some_args), **some_kwargs)

    def test_cli_args_are_copied(self):

        @api_versions.wraps("2.2", "2.6")
        @cliutils.arg("name_1", help="Name of the something")
        @cliutils.arg("action_1", help="Some action")
        def some_func_1(cs, args):
            pass

        @cliutils.arg("name_2", help="Name of the something")
        @cliutils.arg("action_2", help="Some action")
        @api_versions.wraps("2.2", "2.6")
        def some_func_2(cs, args):
            pass

        args_1 = [(('name_1',), {'help': 'Name of the something'}),
                  (('action_1',), {'help': 'Some action'})]
        self.assertEqual(args_1, some_func_1.arguments)

        args_2 = [(('name_2',), {'help': 'Name of the something'}),
                  (('action_2',), {'help': 'Some action'})]
        self.assertEqual(args_2, some_func_2.arguments)


class DiscoverVersionTestCase(utils.TestCase):
    def setUp(self):
        super(DiscoverVersionTestCase, self).setUp()
        self.orig_max = manilaclient.API_MAX_VERSION
        self.orig_min = manilaclient.API_MIN_VERSION
        self.addCleanup(self._clear_fake_version)
        self.fake_client = mock.MagicMock()

    def _clear_fake_version(self):
        manilaclient.API_MAX_VERSION = self.orig_max
        manilaclient.API_MIN_VERSION = self.orig_min

    def _mock_returned_server_version(self, server_version,
                                      server_min_version):
        version_mock = mock.MagicMock(version=server_version,
                                      min_version=server_min_version,
                                      status='CURRENT')
        val = [version_mock]
        self.fake_client.services.server_api_version.return_value = val

    def test_server_is_too_new(self):
        self._mock_returned_server_version('2.7', '2.4')
        manilaclient.API_MAX_VERSION = api_versions.APIVersion("2.3")
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.1")

        self.assertRaisesRegex(exceptions.UnsupportedVersion,
                               ".*range is '2.4' to '2.7'.*",
                               api_versions.discover_version,
                               self.fake_client,
                               api_versions.APIVersion("2.3"))
        self.assertTrue(self.fake_client.services.server_api_version.called)

    def test_server_is_too_old(self):
        self._mock_returned_server_version('2.2', '2.0')
        manilaclient.API_MAX_VERSION = api_versions.APIVersion("2.10")
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.9")

        self.assertRaises(exceptions.UnsupportedVersion,
                          api_versions.discover_version,
                          self.fake_client,
                          api_versions.APIVersion("2.10"))
        self.assertTrue(self.fake_client.services.server_api_version.called)

    def test_requested_version_is_less_than_server_max(self):
        self._mock_returned_server_version('2.17', '2.14')
        max_version = api_versions.APIVersion('2.15')
        manilaclient.API_MAX_VERSION = max_version
        manilaclient.API_MIN_VERSION = api_versions.APIVersion('2.12')
        version = api_versions.discover_version(self.fake_client, max_version)

        self.assertEqual(api_versions.APIVersion('2.15'), version)

    def test_requested_version_is_downgraded(self):
        server_end_version = '2.7'
        self._mock_returned_server_version(server_end_version, '2.0')
        max_version = api_versions.APIVersion("2.8")
        manilaclient.API_MAX_VERSION = max_version
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.5")
        version = api_versions.discover_version(self.fake_client, max_version)

        self.assertEqual(api_versions.APIVersion(server_end_version), version)

    def test_server_and_client_max_are_same(self):
        self._mock_returned_server_version('2.5', '2.0')
        manilaclient.API_MAX_VERSION = api_versions.APIVersion("2.5")
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.5")

        discovered_version = api_versions.discover_version(
            self.fake_client,
            manilaclient.API_MAX_VERSION)
        self.assertEqual("2.5", discovered_version.get_string())
        self.assertTrue(self.fake_client.services.server_api_version.called)

    def test_pre_microversion_server(self):
        self.fake_client.services.server_api_version.return_value = []
        manilaclient.API_MAX_VERSION = api_versions.APIVersion("2.5")
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.5")
        discovered_version = api_versions.discover_version(
            self.fake_client,
            manilaclient.API_MAX_VERSION)
        self.assertEqual("1.0", discovered_version.get_string())
        self.assertTrue(self.fake_client.services.server_api_version.called)

    def test_requested_version_in_range(self):
        self._mock_returned_server_version('2.7', '2.4')
        manilaclient.API_MAX_VERSION = api_versions.APIVersion("2.11")
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.1")

        discovered_version = api_versions.discover_version(
            self.fake_client,
            api_versions.APIVersion('2.7'))
        self.assertEqual('2.7', discovered_version.get_string())
        self.assertTrue(self.fake_client.services.server_api_version.called)

    def test_server_without_microversion(self):
        self._mock_returned_server_version(None, None)
        manilaclient.API_MAX_VERSION = api_versions.APIVersion("2.11")
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.1")

        discovered_version = api_versions.discover_version(
            self.fake_client,
            api_versions.APIVersion('2.7'))
        self.assertEqual(api_versions.DEPRECATED_VERSION,
                         discovered_version.get_string())

        self.assertTrue(self.fake_client.services.server_api_version.called)

    def test_requested_version_is_too_old(self):
        self._mock_returned_server_version('2.5', '2.0')
        manilaclient.API_MAX_VERSION = api_versions.APIVersion("2.5")
        manilaclient.API_MIN_VERSION = api_versions.APIVersion("2.5")

        self.assertRaisesRegex(exceptions.UnsupportedVersion,
                               ".*range is '2.0' to '2.5'.*",
                               api_versions.discover_version,
                               self.fake_client,
                               api_versions.APIVersion("1.0"))
