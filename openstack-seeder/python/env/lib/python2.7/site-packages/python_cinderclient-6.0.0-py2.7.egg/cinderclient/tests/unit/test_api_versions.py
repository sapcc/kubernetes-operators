# Copyright 2016 Mirantis
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

import ddt
import mock
import six

from cinderclient import api_versions
from cinderclient import client as base_client
from cinderclient import exceptions
from cinderclient.v3 import client

from cinderclient.tests.unit import test_utils
from cinderclient.tests.unit import utils


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
        self.assertFalse(v)

    def test_not_null_version(self):
        v = api_versions.APIVersion('1.1')
        self.assertTrue(v)

    @ddt.data("2", "200", "2.1.4", "200.23.66.3", "5 .3", "5. 3", "5.03",
              "02.1", "2.001", "", " 2.1", "2.1 ")
    def test_invalid_version_strings(self, version_string):
        self.assertRaises(exceptions.UnsupportedVersion,
                          api_versions.APIVersion, version_string)

    def test_version_comparisons(self):
        v1 = api_versions.APIVersion("2.0")
        v2 = api_versions.APIVersion("2.5")
        v3 = api_versions.APIVersion("5.23")
        v4 = api_versions.APIVersion("2.0")
        v_null = api_versions.APIVersion()

        self.assertLess(v1, v2)
        self.assertGreater(v3, v2)
        self.assertNotEqual(v1, v2)
        self.assertEqual(v1, v4)
        self.assertNotEqual(v1, v_null)
        self.assertEqual(v_null, v_null)
        self.assertRaises(TypeError, v1.__le__, "2.1")

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

        self.assertTrue(v2.matches(v1, v3))
        self.assertTrue(v2.matches(v1, v_null))
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


class ManagerTest(utils.TestCase):
    def test_api_version(self):
        # The function manager.return_api_version has two versions,
        # when called with api version 3.1 it should return the
        # string '3.1' and when called with api version 3.2 or higher
        # it should return the string '3.2'.
        version = api_versions.APIVersion('3.1')
        api = client.Client(api_version=version)
        manager = test_utils.FakeManagerWithApi(api)
        self.assertEqual('3.1', manager.return_api_version())

        version = api_versions.APIVersion('3.2')
        api = client.Client(api_version=version)
        manager = test_utils.FakeManagerWithApi(api)
        self.assertEqual('3.2', manager.return_api_version())

        # pick up the highest version
        version = api_versions.APIVersion('3.3')
        api = client.Client(api_version=version)
        manager = test_utils.FakeManagerWithApi(api)
        self.assertEqual('3.2', manager.return_api_version())

        version = api_versions.APIVersion('3.0')
        api = client.Client(api_version=version)
        manager = test_utils.FakeManagerWithApi(api)
        # An exception will be returned here because the function
        # return_api_version doesn't support version 3.0
        self.assertRaises(exceptions.VersionNotFoundForAPIMethod,
                          manager.return_api_version)


class UpdateHeadersTestCase(utils.TestCase):
    def test_api_version_is_null(self):
        headers = {}
        api_versions.update_headers(headers, api_versions.APIVersion())
        self.assertEqual({}, headers)

    def test_api_version_is_major(self):
        headers = {}
        api_versions.update_headers(headers, api_versions.APIVersion("7.0"))
        self.assertEqual({}, headers)

    def test_api_version_is_not_null(self):
        api_version = api_versions.APIVersion("2.3")
        headers = {}
        api_versions.update_headers(headers, api_version)
        self.assertEqual(
            {"OpenStack-API-Version": "volume " + api_version.get_string()},
            headers)


class GetAPIVersionTestCase(utils.TestCase):
    def test_get_available_client_versions(self):
        output = api_versions.get_available_major_versions()
        self.assertNotEqual([], output)

    def test_wrong_format(self):
        self.assertRaises(exceptions.UnsupportedVersion,
                          api_versions.get_api_version, "something_wrong")

    def test_wrong_major_version(self):
        self.assertRaises(exceptions.UnsupportedVersion,
                          api_versions.get_api_version, "4")

    @mock.patch("cinderclient.api_versions.get_available_major_versions")
    @mock.patch("cinderclient.api_versions.APIVersion")
    def test_only_major_part_is_presented(self, mock_apiversion,
                                          mock_get_majors):
        mock_get_majors.return_value = [
            str(mock_apiversion.return_value.ver_major)]
        version = 7
        self.assertEqual(mock_apiversion.return_value,
                         api_versions.get_api_version(version))
        mock_apiversion.assert_called_once_with("%s.0" % str(version))

    @mock.patch("cinderclient.api_versions.get_available_major_versions")
    @mock.patch("cinderclient.api_versions.APIVersion")
    def test_major_and_minor_parts_is_presented(self, mock_apiversion,
                                                mock_get_majors):
        version = "2.7"
        mock_get_majors.return_value = [
            str(mock_apiversion.return_value.ver_major)]
        self.assertEqual(mock_apiversion.return_value,
                         api_versions.get_api_version(version))
        mock_apiversion.assert_called_once_with(version)


@ddt.ddt
class DiscoverVersionTestCase(utils.TestCase):
    def setUp(self):
        super(DiscoverVersionTestCase, self).setUp()
        self.orig_max = api_versions.MAX_VERSION
        self.orig_min = api_versions.MIN_VERSION or None
        self.addCleanup(self._clear_fake_version)
        self.fake_client = mock.MagicMock()

    def _clear_fake_version(self):
        api_versions.MAX_VERSION = self.orig_max
        api_versions.MIN_VERSION = self.orig_min

    def _mock_returned_server_version(self, server_version,
                                      server_min_version):
        version_mock = mock.MagicMock(version=server_version,
                                      min_version=server_min_version,
                                      status='CURRENT')
        val = [version_mock]
        if not server_version and not server_min_version:
            val = []
        self.fake_client.services.server_api_version.return_value = val

    @ddt.data(
        ("3.1", "3.3", "3.4", "3.7", "3.3", True),   # Server too new
        ("3.9", "3.10", "3.0", "3.3", "3.10", True),   # Server too old
        ("3.3", "3.9", "3.7", "3.17", "3.9", False),  # Requested < server
        # downgraded because of server:
        ("3.5", "3.8", "3.0", "3.7", "3.8", False, "3.7"),
        # downgraded because of client:
        ("3.5", "3.8", "3.0", "3.9", "3.9", False, "3.8"),
        # downgraded because of both:
        ("3.5", "3.7", "3.0", "3.8", "3.9", False, "3.7"),
        ("3.5", "3.5", "3.0", "3.5", "3.5", False),  # Server & client same
        ("3.5", "3.5", "3.0", "3.5", "3.5", False, "2.0", []),  # Pre-micro
        ("3.1", "3.11", "3.4", "3.7", "3.7", False),  # Requested in range
        ("3.1", "3.11", None, None, "3.7", False),  # Server w/o support
        ("3.5", "3.5", "3.0", "3.5", "1.0", True)    # Requested too old
    )
    @ddt.unpack
    def test_microversion(self, client_min, client_max, server_min, server_max,
                          requested_version, exp_range, end_version=None,
                          ret_val=None):
        if ret_val is not None:
            self.fake_client.services.server_api_version.return_value = ret_val
        else:
            self._mock_returned_server_version(server_max, server_min)

        api_versions.MAX_VERSION = client_max
        api_versions.MIN_VERSION = client_min

        if exp_range:
            self.assertRaisesRegex(exceptions.UnsupportedVersion,
                                   ".*range is '%s' to '%s'.*" %
                                   (server_min, server_max),
                                   api_versions.discover_version,
                                   self.fake_client,
                                   api_versions.APIVersion(requested_version))
        else:
            discovered_version = api_versions.discover_version(
                self.fake_client,
                api_versions.APIVersion(requested_version))

            version = requested_version
            if server_min is None and server_max is None:
                version = api_versions.DEPRECATED_VERSION
            elif end_version is not None:
                version = end_version
            self.assertEqual(version,
                             discovered_version.get_string())
            self.assertTrue(
                self.fake_client.services.server_api_version.called)

    def test_get_highest_version(self):
        self._mock_returned_server_version("3.14", "3.0")
        highest_version = api_versions.get_highest_version(self.fake_client)
        self.assertEqual("3.14", highest_version.get_string())
        self.assertTrue(self.fake_client.services.server_api_version.called)

    def test_get_highest_version_bad_client(self):
        """Tests that we gracefully handle the wrong version of client."""
        v2_client = base_client.Client('2.0')
        ex = self.assertRaises(exceptions.UnsupportedVersion,
                               api_versions.get_highest_version, v2_client)
        self.assertIn('Invalid client version 2.0 to get', six.text_type(ex))
