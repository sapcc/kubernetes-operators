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
import mock

from manilaclient import exceptions
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import security_services


class SecurityServiceTest(utils.TestCase):

    class _FakeSecurityService(object):
        id = 'fake_security_service_id'

    def setUp(self):
        super(SecurityServiceTest, self).setUp()
        self.manager = security_services.SecurityServiceManager(
            fakes.FakeClient())

    def test_create_all_fields(self):
        values = {
            'type': 'ldap',
            'dns_ip': 'fake dns ip',
            'ou': 'fake ou',
            'server': 'fake.ldap.server',
            'domain': 'fake.ldap.domain',
            'user': 'fake user',
            'password': 'fake password',
            'name': 'fake name',
            'description': 'fake description',
        }

        with mock.patch.object(self.manager, '_create', fakes.fake_create):
            result = self.manager.create(**values)

            self.assertEqual(result['url'], security_services.RESOURCES_PATH)
            self.assertEqual(result['resp_key'],
                             security_services.RESOURCE_NAME)
            self.assertIn(security_services.RESOURCE_NAME, result['body'])
            self.assertEqual(result['body'][security_services.RESOURCE_NAME],
                             values)

    def test_create_some_fields(self):
        values = {
            'type': 'ldap',
            'dns_ip': 'fake dns ip',
            'server': 'fake.ldap.server',
            'domain': 'fake.ldap.domain',
            'user': 'fake user',
        }

        with mock.patch.object(self.manager, '_create', fakes.fake_create):
            result = self.manager.create(**values)

            self.assertEqual(result['url'], security_services.RESOURCES_PATH)
            self.assertEqual(result['resp_key'],
                             security_services.RESOURCE_NAME)
            self.assertIn(security_services.RESOURCE_NAME, result['body'])
            self.assertEqual(result['body'][security_services.RESOURCE_NAME],
                             values)

    def test_delete(self):
        security_service = 'fake service'
        with mock.patch.object(self.manager, '_delete', mock.Mock()):
            self.manager.delete(security_service)
            self.manager._delete.assert_called_once_with(
                security_services.RESOURCE_PATH % security_service)

    def test_delete_by_object(self):
        security_service = self._FakeSecurityService()
        with mock.patch.object(self.manager, '_delete', mock.Mock()):
            self.manager.delete(security_service)
            self.manager._delete.assert_called_once_with(
                security_services.RESOURCE_PATH % security_service.id)

    def test_get(self):
        security_service = 'fake service'
        with mock.patch.object(self.manager, '_get', mock.Mock()):
            self.manager.get(security_service)
            self.manager._get.assert_called_once_with(
                security_services.RESOURCE_PATH % security_service,
                security_services.RESOURCE_NAME)

    def test_get_by_object(self):
        security_service = self._FakeSecurityService()
        with mock.patch.object(self.manager, '_get', mock.Mock()):
            self.manager.get(security_service)
            self.manager._get.assert_called_once_with(
                security_services.RESOURCE_PATH % security_service.id,
                security_services.RESOURCE_NAME)

    def test_list_summary(self):
        with mock.patch.object(self.manager, '_list',
                               mock.Mock(return_value=None)):
            self.manager.list(detailed=False)
            self.manager._list.assert_called_once_with(
                security_services.RESOURCES_PATH,
                security_services.RESOURCES_NAME)

    def test_list_detail(self):
        with mock.patch.object(self.manager, '_list',
                               mock.Mock(return_value=None)):
            self.manager.list(detailed=True)
            self.manager._list.assert_called_once_with(
                security_services.RESOURCES_PATH + '/detail',
                security_services.RESOURCES_NAME)

    def test_list_no_filters(self):
        with mock.patch.object(self.manager, '_list',
                               mock.Mock(return_value=None)):
            self.manager.list()
            self.manager._list.assert_called_once_with(
                security_services.RESOURCES_PATH + '/detail',
                security_services.RESOURCES_NAME)

    def test_list_with_filters(self):
        filters = {'all_tenants': 1, 'network': 'fake', 'status': 'ERROR'}
        expected_postfix = ('/detail?all_tenants=1&network=fake&status=ERROR')
        with mock.patch.object(self.manager, '_list',
                               mock.Mock(return_value=None)):
            self.manager.list(search_opts=filters)
            self.manager._list.assert_called_once_with(
                security_services.RESOURCES_PATH + expected_postfix,
                security_services.RESOURCES_NAME)

    def test_update(self):
        security_service = 'fake service'
        values = {
            'dns_ip': 'new dns ip',
            'ou': 'new ou',
            'server': 'new.ldap.server',
            'domain': 'new.ldap.domain',
            'user': 'new user',
            'password': 'fake password',
        }
        with mock.patch.object(self.manager, '_update', fakes.fake_update):
            result = self.manager.update(security_service, **values)
            self.assertEqual(
                result['url'],
                security_services.RESOURCE_PATH % security_service)
            self.assertEqual(
                result['resp_key'],
                security_services.RESOURCE_NAME)
            self.assertEqual(
                result['body'][security_services.RESOURCE_NAME],
                values)

    def test_update_by_object(self):
        security_service = self._FakeSecurityService()
        values = {'user': 'fake_user'}
        with mock.patch.object(self.manager, '_update', fakes.fake_update):
            result = self.manager.update(security_service, **values)
            self.assertEqual(
                result['url'],
                security_services.RESOURCE_PATH % security_service.id)
            self.assertEqual(
                result['resp_key'],
                security_services.RESOURCE_NAME)
            self.assertEqual(
                result['body'][security_services.RESOURCE_NAME],
                values)

    def test_update_no_fields_specified(self):
        security_service = 'fake service'
        self.assertRaises(exceptions.CommandError,
                          self.manager.update,
                          security_service)
