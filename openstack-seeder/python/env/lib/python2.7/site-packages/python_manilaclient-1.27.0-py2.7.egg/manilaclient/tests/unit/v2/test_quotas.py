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
from manilaclient.v2 import quotas


@ddt.ddt
class QuotaSetsTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return quotas.QuotaSetManager(api=mock_microversion)

    def _get_resource_path(self, microversion):
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            return quotas.RESOURCE_PATH
        return quotas.RESOURCE_PATH_LEGACY

    @ddt.data("2.6", "2.7", "2.25", "2.38", "2.39")
    def test_tenant_quotas_get(self, microversion):
        tenant_id = 'test'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        version = api_versions.APIVersion(microversion)
        if version >= api_versions.APIVersion('2.25'):
            expected_url = "%s/test/detail" % resource_path
        else:
            expected_url = ("%s/test"
                            % resource_path)

        with mock.patch.object(manager, '_get',
                               mock.Mock(return_value='fake_get')):
            manager.get(tenant_id, detail=True)

            manager._get.assert_called_once_with(expected_url, "quota_set")

    @ddt.data("2.6", "2.7", "2.25", "2.38", "2.39")
    def test_user_quotas_get(self, microversion):
        tenant_id = 'test'
        user_id = 'fake_user'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        version = api_versions.APIVersion(microversion)
        if version >= api_versions.APIVersion('2.25'):
            expected_url = ("%s/test/detail?user_id=fake_user"
                            % resource_path)
        else:
            expected_url = ("%s/test?user_id=fake_user"
                            % resource_path)

        with mock.patch.object(manager, '_get',
                               mock.Mock(return_value='fake_get')):
            manager.get(tenant_id, user_id=user_id, detail=True)

            manager._get.assert_called_once_with(expected_url, "quota_set")

    def test_share_type_quotas_get(self):
        tenant_id = 'fake_tenant_id'
        share_type = 'fake_share_type'
        manager = self._get_manager('2.39')
        resource_path = self._get_resource_path('2.39')
        expected_url = ("%s/%s/detail?share_type=%s"
                        % (resource_path, tenant_id, share_type))

        with mock.patch.object(manager, '_get',
                               mock.Mock(return_value='fake_get')):
            manager.get(tenant_id, share_type=share_type, detail=True)

            manager._get.assert_called_once_with(expected_url, "quota_set")

    @ddt.data("2.6", "2.7", "2.38", "2.39")
    def test_tenant_quotas_defaults(self, microversion):
        tenant_id = 'test'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        expected_url = "%s/test/defaults" % resource_path
        with mock.patch.object(manager, '_get',
                               mock.Mock(return_value='fake_get')):
            manager.defaults(tenant_id)

            manager._get.assert_called_once_with(expected_url, "quota_set")

    @ddt.data(
        ("2.6", {}), ("2.6", {"force": True}),
        ("2.7", {}), ("2.7", {"force": True}),
        ("2.38", {}), ("2.38", {"force": True}),
        ("2.39", {}), ("2.39", {"force": True}),
    )
    @ddt.unpack
    def test_update_quota(self, microversion, extra_data):
        tenant_id = 'test'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        expected_url = "%s/test" % resource_path
        expected_body = {
            'quota_set': {
                'tenant_id': tenant_id,
                'shares': 1,
                'snapshots': 2,
                'gigabytes': 3,
                'snapshot_gigabytes': 4,
                'share_networks': 5,
            },
        }
        expected_body['quota_set'].update(extra_data)
        with mock.patch.object(manager, '_update',
                               mock.Mock(return_value='fake_update')):
            manager.update(
                tenant_id, shares=1, snapshots=2, gigabytes=3,
                snapshot_gigabytes=4, share_networks=5, **extra_data)

            manager._update.assert_called_once_with(
                expected_url, expected_body, "quota_set")

    @ddt.data("2.6", "2.7", "2.38", "2.39", "2.40")
    def test_update_user_quota(self, microversion):
        tenant_id = 'test'
        user_id = 'fake_user'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        expected_url = "%s/test?user_id=fake_user" % resource_path
        expected_body = {
            'quota_set': {
                'tenant_id': tenant_id,
                'shares': 1,
                'snapshots': 2,
                'gigabytes': 3,
                'snapshot_gigabytes': 4,
                'share_networks': 5,
            },
        }
        kwargs = {
            'shares': expected_body['quota_set']['shares'],
            'snapshots': expected_body['quota_set']['snapshots'],
            'gigabytes': expected_body['quota_set']['gigabytes'],
            'snapshot_gigabytes': expected_body['quota_set'][
                'snapshot_gigabytes'],
            'share_networks': expected_body['quota_set']['share_networks'],
            'user_id': user_id,
        }
        if microversion == '2.40':
            expected_body['quota_set']['share_groups'] = 6
            expected_body['quota_set']['share_group_snapshots'] = 7
            kwargs['share_groups'] = expected_body['quota_set'][
                'share_groups']
            kwargs['share_group_snapshots'] = expected_body['quota_set'][
                'share_group_snapshots']

        with mock.patch.object(manager, '_update',
                               mock.Mock(return_value='fake_update')):
            manager.update(tenant_id, **kwargs)

            manager._update.assert_called_once_with(
                expected_url, expected_body, "quota_set")

    def test_update_share_type_quota(self):
        tenant_id = 'fake_tenant_id'
        share_type = 'fake_share_type'
        manager = self._get_manager('2.39')
        resource_path = self._get_resource_path('2.39')
        expected_url = "%s/%s?share_type=%s" % (
            resource_path, tenant_id, share_type)
        expected_body = {
            'quota_set': {
                'tenant_id': tenant_id,
                'shares': 1,
                'snapshots': 2,
                'gigabytes': 3,
                'snapshot_gigabytes': 4,
            },
        }
        with mock.patch.object(manager, '_update',
                               mock.Mock(return_value='fake_update')):
            manager.update(
                tenant_id, shares=1, snapshots=2, gigabytes=3,
                snapshot_gigabytes=4, share_type=share_type)

            manager._update.assert_called_once_with(
                expected_url, expected_body, "quota_set")

    def test_update_share_type_quotas_for_share_networks(self):
        manager = self._get_manager("2.39")

        with mock.patch.object(manager, '_update',
                               mock.Mock(return_value='fake_delete')):
            self.assertRaises(
                ValueError,
                manager.update,
                'fake_tenant_id', share_type='fake_share_type',
                share_networks=13,
            )

            manager._update.assert_not_called()

    @ddt.data("2.6", "2.7", "2.38", "2.39")
    def test_quotas_delete(self, microversion):
        tenant_id = 'test'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        expected_url = "%s/test" % resource_path
        with mock.patch.object(manager, '_delete',
                               mock.Mock(return_value='fake_delete')):
            manager.delete(tenant_id)

            manager._delete.assert_called_once_with(expected_url)

    @ddt.data("2.6", "2.7", "2.38", "2.39")
    def test_user_quotas_delete(self, microversion):
        tenant_id = 'test'
        user_id = 'fake_user'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        expected_url = "%s/test?user_id=fake_user" % resource_path
        with mock.patch.object(manager, '_delete',
                               mock.Mock(return_value='fake_delete')):
            manager.delete(tenant_id, user_id=user_id)

            manager._delete.assert_called_once_with(expected_url)

    def test_share_type_quotas_delete(self):
        tenant_id = 'test'
        share_type = 'fake_st'
        manager = self._get_manager("2.39")
        resource_path = self._get_resource_path("2.39")
        expected_url = "%s/test?share_type=fake_st" % resource_path
        with mock.patch.object(manager, '_delete',
                               mock.Mock(return_value='fake_delete')):
            manager.delete(tenant_id, share_type=share_type)

            manager._delete.assert_called_once_with(expected_url)

    @ddt.data('get', 'update', 'delete')
    def test_share_type_quotas_using_old_microversion(self, operation):
        manager = self._get_manager("2.38")

        with mock.patch.object(manager, '_%s' % operation,
                               mock.Mock(return_value='fake_delete')):
            self.assertRaises(
                TypeError,
                getattr(manager, operation),
                'fake_tenant_id', share_type='fake_share_type',
            )

            getattr(manager, '_%s' % operation).assert_not_called()
