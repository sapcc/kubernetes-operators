# Copyright 2013 OpenStack Foundation.
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
import itertools
import mock

from manilaclient import api_versions
from manilaclient import exceptions
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_networks


@ddt.ddt
class ShareNetworkTest(utils.TestCase):

    class _FakeShareNetwork(object):
        id = 'fake_share_network_id'

    class _FakeSecurityService(object):
        id = 'fake_security_service_id'

    def setUp(self):
        super(ShareNetworkTest, self).setUp()
        self.manager = share_networks.ShareNetworkManager(fakes.FakeClient())
        self.values = {
            'nova_net_id': 'fake_nova_net_id',
            'neutron_net_id': 'fake net id',
            'neutron_subnet_id': 'fake subnet id',
            'name': 'fake name',
            'description': 'new whatever',
        }

    @ddt.data("2.25", "2.26")
    def test_create(self, microversion):
        api_version = api_versions.APIVersion(microversion)
        values = self.values.copy()
        if (api_version >= api_versions.APIVersion("2.26")):
            del(values['nova_net_id'])
        body_expected = {share_networks.RESOURCE_NAME: values}

        manager = share_networks.ShareNetworkManager(
            fakes.FakeClient(api_version=api_version))
        with mock.patch.object(manager, '_create', fakes.fake_create):
            result = manager.create(**values)

            self.assertEqual(result['url'], share_networks.RESOURCES_PATH)
            self.assertEqual(result['resp_key'], share_networks.RESOURCE_NAME)
            self.assertEqual(
                body_expected,
                result['body'])

    def test_delete_str(self):
        share_nw = 'fake share nw'
        with mock.patch.object(self.manager, '_delete', mock.Mock()):
            self.manager.delete(share_nw)
            self.manager._delete.assert_called_once_with(
                share_networks.RESOURCE_PATH % share_nw)

    def test_delete_obj(self):
        share_nw = self._FakeShareNetwork()
        with mock.patch.object(self.manager, '_delete', mock.Mock()):
            self.manager.delete(share_nw)
            self.manager._delete.assert_called_once_with(
                share_networks.RESOURCE_PATH % share_nw.id)

    def test_get(self):
        share_nw = 'fake share nw'
        with mock.patch.object(self.manager, '_get', mock.Mock()):
            self.manager.get(share_nw)
            self.manager._get.assert_called_once_with(
                share_networks.RESOURCE_PATH % share_nw,
                share_networks.RESOURCE_NAME)

    def test_list_not_detailed(self):
        with mock.patch.object(self.manager, '_list',
                               mock.Mock(return_value=None)):
            self.manager.list(detailed=False)
            self.manager._list.assert_called_once_with(
                share_networks.RESOURCES_PATH,
                share_networks.RESOURCES_NAME)

    def test_list(self):
        with mock.patch.object(self.manager, '_list',
                               mock.Mock(return_value=None)):
            self.manager.list()
            self.manager._list.assert_called_once_with(
                share_networks.RESOURCES_PATH + '/detail',
                share_networks.RESOURCES_NAME)

    def test_list_with_filters(self):
        filters = {'all_tenants': 1, 'status': 'ERROR'}
        expected_path = ("%s/detail?all_tenants=1&status="
                         "ERROR" % share_networks.RESOURCES_PATH)

        with mock.patch.object(self.manager, '_list',
                               mock.Mock(return_value=None)):
            self.manager.list(search_opts=filters)
            self.manager._list.assert_called_once_with(
                expected_path,
                share_networks.RESOURCES_NAME)

    @ddt.data(*itertools.product(
        ["2.25", "2.26"],
        ['fake share nw', _FakeShareNetwork()]
    ))
    @ddt.unpack
    def test_update_share_network(self, microversion, share_nw):
        api_version = api_versions.APIVersion(microversion)
        values = self.values.copy()
        if (api_version >= api_versions.APIVersion("2.26")):
            del(values['nova_net_id'])
        body_expected = {share_networks.RESOURCE_NAME: values}

        manager = share_networks.ShareNetworkManager(
            fakes.FakeClient(api_version=api_version))
        with mock.patch.object(manager, '_update', fakes.fake_update):
            result = manager.update(share_nw, **values)
            id = share_nw.id if hasattr(share_nw, 'id') else share_nw
            self.assertEqual(result['url'],
                             share_networks.RESOURCE_PATH % id)
            self.assertEqual(result['resp_key'], share_networks.RESOURCE_NAME)
            self.assertEqual(result['body'], body_expected)

    def test_update_with_exception(self):
        share_nw = 'fake share nw'
        self.assertRaises(exceptions.CommandError,
                          self.manager.update,
                          share_nw)

    def test_add_security_service(self):
        security_service = 'fake security service'
        share_nw = 'fake share nw'
        expected_path = (share_networks.RESOURCE_PATH + '/action') % share_nw
        expected_body = {
            'add_security_service': {
                'security_service_id': security_service,
            },
        }
        with mock.patch.object(self.manager, '_create', mock.Mock()):
            self.manager.add_security_service(share_nw, security_service)
            self.manager._create.assert_called_once_with(
                expected_path,
                expected_body,
                share_networks.RESOURCE_NAME)

    def test_add_security_service_to_share_nw_object(self):
        security_service = self._FakeSecurityService()
        share_nw = self._FakeShareNetwork()
        expected_path = ((share_networks.RESOURCE_PATH +
                          '/action') % share_nw.id)
        expected_body = {
            'add_security_service': {
                'security_service_id': security_service.id,
            },
        }
        with mock.patch.object(self.manager, '_create', mock.Mock()):
            self.manager.add_security_service(share_nw, security_service)
            self.manager._create.assert_called_once_with(
                expected_path,
                expected_body,
                share_networks.RESOURCE_NAME)

    def test_remove_security_service(self):
        security_service = 'fake security service'
        share_nw = 'fake share nw'
        expected_path = (share_networks.RESOURCE_PATH + '/action') % share_nw
        expected_body = {
            'remove_security_service': {
                'security_service_id': security_service,
            },
        }
        with mock.patch.object(self.manager, '_create', mock.Mock()):
            self.manager.remove_security_service(share_nw, security_service)
            self.manager._create.assert_called_once_with(
                expected_path,
                expected_body,
                share_networks.RESOURCE_NAME)

    def test_remove_security_service_from_share_nw_object(self):
        security_service = self._FakeSecurityService()
        share_nw = self._FakeShareNetwork()
        expected_path = ((share_networks.RESOURCE_PATH +
                          '/action') % share_nw.id)
        expected_body = {
            'remove_security_service': {
                'security_service_id': security_service.id,
            },
        }
        with mock.patch.object(self.manager, '_create', mock.Mock()):
            self.manager.remove_security_service(share_nw, security_service)
            self.manager._create.assert_called_once_with(
                expected_path,
                expected_body,
                share_networks.RESOURCE_NAME)
