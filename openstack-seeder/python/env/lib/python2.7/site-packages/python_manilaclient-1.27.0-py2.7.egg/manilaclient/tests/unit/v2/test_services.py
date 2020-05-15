# Copyright 2013 OpenStack Foundation
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

from manilaclient import api_versions
from manilaclient.tests.unit import utils
from manilaclient.v2 import services


@ddt.ddt
class ServicesTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return services.ServiceManager(api=mock_microversion)

    def _get_resource_path(self, microversion):
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            return services.RESOURCE_PATH
        return services.RESOURCE_PATH_LEGACY

    @ddt.data("2.6", "2.7")
    def test_list(self, microversion):
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        with mock.patch.object(manager, '_list',
                               mock.Mock(return_value='fake')):
            result = manager.list()

            manager._list.assert_called_once_with(
                resource_path, services.RESOURCE_NAME)
            self.assertEqual("fake", result)

    def test_list_services_with_one_search_opt(self):
        manager = self._get_manager("2.7")
        host = 'fake_host'
        query_string = "?host=%s" % host
        with mock.patch.object(manager, '_list',
                               mock.Mock(return_value=None)):
            manager.list({'host': host})
            manager._list.assert_called_once_with(
                services.RESOURCE_PATH + query_string,
                services.RESOURCE_NAME,
            )

    def test_list_services_with_two_search_opts(self):
        manager = self._get_manager("2.7")
        host = 'fake_host'
        binary = 'fake_binary'
        query_string = "?binary=%s&host=%s" % (binary, host)
        with mock.patch.object(manager, '_list',
                               mock.Mock(return_value=None)):
            manager.list({'binary': binary, 'host': host})
            manager._list.assert_called_once_with(
                services.RESOURCE_PATH + query_string,
                services.RESOURCE_NAME,
            )

    @ddt.data("2.6", "2.7")
    def test_enable_service(self, microversion):
        manager = self._get_manager(microversion)
        host = 'fake_host'
        binary = 'fake_binary'
        with mock.patch.object(manager, '_update'):
            manager.enable(binary=binary, host=host)

            manager._update.assert_called_once_with(
                self._get_resource_path(microversion) + '/enable',
                {"host": host, "binary": binary},
            )

    @ddt.data("2.6", "2.7")
    def test_disable_service(self, microversion):
        manager = self._get_manager(microversion)
        host = 'fake_host'
        binary = 'fake_binary'
        with mock.patch.object(manager, '_update'):
            manager.disable(binary=binary, host=host)

            manager._update.assert_called_once_with(
                self._get_resource_path(microversion) + '/disable',
                {"host": host, "binary": binary},
            )
