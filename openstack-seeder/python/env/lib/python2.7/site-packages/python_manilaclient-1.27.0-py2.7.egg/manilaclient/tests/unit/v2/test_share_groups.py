# Copyright 2016 Clinton Knight
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

import ddt
import six

import manilaclient
from manilaclient import exceptions
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes as fake
from manilaclient.v2 import share_groups


@ddt.ddt
class ShareGroupTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupTest, self).setUp()
        self.manager = share_groups.ShareGroupManager(fake.FakeClient())
        self.share_group = share_groups.ShareGroup(
            self.manager, {'id': 'fake_id'})
        self.fake_kwargs = {'key': 'value'}

    def test_repr(self):
        result = six.text_type(self.share_group)

        self.assertEqual('<Share Group: fake_id>', result)

    def test_update(self):
        mock_manager_update = self.mock_object(self.manager, 'update')

        self.share_group.update(**self.fake_kwargs)

        mock_manager_update.assert_called_once_with(
            self.share_group, **self.fake_kwargs)

    def test_delete(self):
        mock_manager_delete = self.mock_object(self.manager, 'delete')

        self.share_group.delete()

        mock_manager_delete.assert_called_once_with(
            self.share_group, force=False)

    @ddt.data(True, False)
    def test_delete_force(self, force):
        mock_manager_delete = self.mock_object(self.manager, 'delete')

        self.share_group.delete(force=force)

        mock_manager_delete.assert_called_once_with(
            self.share_group, force=force)

    def test_reset_state(self):
        mock_manager_reset_state = self.mock_object(
            self.manager, 'reset_state')

        self.share_group.reset_state('fake_state')

        mock_manager_reset_state.assert_called_once_with(
            self.share_group, 'fake_state')


@ddt.ddt
class ShareGroupManagerTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupManagerTest, self).setUp()
        self.manager = share_groups.ShareGroupManager(fake.FakeClient())

    def test_create(self):
        fake_share_group = fake.ShareGroup()
        mock_create = self.mock_object(
            self.manager, '_create', mock.Mock(return_value=fake_share_group))
        create_args = {
            'name': fake.ShareGroup.name,
            'description': fake.ShareGroup.description,
            'availability_zone': fake.ShareGroup.availability_zone,
            'share_group_type': fake.ShareGroupType(),
            'share_types': [fake.ShareType()],
            'share_network': fake.ShareNetwork(),
        }

        result = self.manager.create(**create_args)

        self.assertIs(fake_share_group, result)
        expected_body = {
            share_groups.RESOURCE_NAME: {
                'name': fake.ShareGroup.name,
                'description': fake.ShareGroup.description,
                'share_group_type_id': fake.ShareGroupType().id,
                'share_network_id': fake.ShareNetwork().id,
                'share_types': [fake.ShareType().id],
                'availability_zone': fake.ShareGroup.availability_zone,
            },
        }
        mock_create.assert_called_once_with(
            share_groups.RESOURCES_PATH,
            expected_body,
            share_groups.RESOURCE_NAME)

    def test_create_default_type(self):
        fake_share_group = fake.ShareGroup()
        mock_create = self.mock_object(
            self.manager, '_create', mock.Mock(return_value=fake_share_group))
        create_args = {
            'name': fake.ShareGroup.name,
            'description': fake.ShareGroup.description,
            'availability_zone': fake.ShareGroup.availability_zone,
        }

        result = self.manager.create(**create_args)

        self.assertIs(fake_share_group, result)
        expected_body = {share_groups.RESOURCE_NAME: create_args}
        mock_create.assert_called_once_with(
            share_groups.RESOURCES_PATH,
            expected_body,
            share_groups.RESOURCE_NAME)

    def test_create_from_snapshot(self):
        fake_share_group = fake.ShareGroup()
        mock_create = self.mock_object(
            self.manager, '_create', mock.Mock(return_value=fake_share_group))
        create_args = {
            'name': fake.ShareGroup.name,
            'description': fake.ShareGroup.description,
            'availability_zone': fake.ShareGroup.availability_zone,
            'source_share_group_snapshot': fake.ShareGroupSnapshot(),
        }

        result = self.manager.create(**create_args)

        self.assertIs(fake_share_group, result)
        expected_body = {
            share_groups.RESOURCE_NAME: {
                'name': fake.ShareGroup.name,
                'description': fake.ShareGroup.description,
                'availability_zone': fake.ShareGroup.availability_zone,
                'source_share_group_snapshot_id': fake.ShareGroupSnapshot().id,
            },
        }
        mock_create.assert_called_once_with(
            share_groups.RESOURCES_PATH,
            expected_body,
            share_groups.RESOURCE_NAME)

    def test_create_using_unsupported_microversion(self):
        self.manager.api.api_version = manilaclient.API_MIN_VERSION

        self.assertRaises(exceptions.UnsupportedVersion, self.manager.create)

    def test_create_invalid_arguments(self):
        create_args = {
            'name': fake.ShareGroup.name,
            'description': fake.ShareGroup.description,
            'share_types': [fake.ShareType().id],
            'source_share_group_snapshot': fake.ShareGroupSnapshot(),
        }

        self.assertRaises(ValueError, self.manager.create, **create_args)

    def test_get(self):
        fake_share_group = fake.ShareGroup()
        mock_get = self.mock_object(
            self.manager, '_get', mock.Mock(return_value=fake_share_group))

        result = self.manager.get(fake.ShareGroup.id)

        self.assertIs(fake_share_group, result)
        mock_get.assert_called_once_with(
            share_groups.RESOURCE_PATH % fake.ShareGroup.id,
            share_groups.RESOURCE_NAME)

    def test_list(self):
        fake_share_group = fake.ShareGroup()
        mock_list = self.mock_object(
            self.manager, '_list', mock.Mock(return_value=[fake_share_group]))

        result = self.manager.list()

        self.assertEqual([fake_share_group], result)
        mock_list.assert_called_once_with(
            share_groups.RESOURCES_PATH + '/detail',
            share_groups.RESOURCES_NAME)

    def test_list_no_detail(self):
        fake_share_group = fake.ShareGroup()
        mock_list = self.mock_object(
            self.manager, '_list', mock.Mock(return_value=[fake_share_group]))

        result = self.manager.list(detailed=False)

        self.assertEqual([fake_share_group], result)
        mock_list.assert_called_once_with(
            share_groups.RESOURCES_PATH, share_groups.RESOURCES_NAME)

    def test_list_with_filters(self):
        fake_share_group = fake.ShareGroup()
        mock_list = self.mock_object(
            self.manager, '_list', mock.Mock(return_value=[fake_share_group]))
        filters = {'all_tenants': 1}

        result = self.manager.list(detailed=False, search_opts=filters)

        self.assertEqual([fake_share_group], result)
        expected_path = (share_groups.RESOURCES_PATH + '?all_tenants=1')
        mock_list.assert_called_once_with(
            expected_path, share_groups.RESOURCES_NAME)

    @ddt.data(
        ('name', 'name'),
        ('share_group_type', 'share_group_type_id'),
        ('share_network', 'share_network_id'),
    )
    @ddt.unpack
    def test_list_with_sorting(self, key, expected_key):
        fake_share_group = fake.ShareGroup()
        mock_list = self.mock_object(
            self.manager, '_list', mock.Mock(return_value=[fake_share_group]))

        result = self.manager.list(
            detailed=False, sort_dir='asc', sort_key=key)

        self.assertEqual([fake_share_group], result)
        expected_path = (
            share_groups.RESOURCES_PATH + '?sort_dir=asc&sort_key=' +
            expected_key)
        mock_list.assert_called_once_with(
            expected_path, share_groups.RESOURCES_NAME)

    @ddt.data(
        ('name', 'invalid'),
        ('invalid', 'asc'),
    )
    @ddt.unpack
    def test_list_with_invalid_sorting(self, sort_key, sort_dir):
        self.assertRaises(
            ValueError,
            self.manager.list, sort_dir=sort_dir, sort_key=sort_key)

    def test_update(self):
        fake_share_group = fake.ShareGroup()
        mock_get = self.mock_object(
            self.manager, '_get', mock.Mock(return_value=fake_share_group))
        mock_update = self.mock_object(
            self.manager, '_update', mock.Mock(return_value=fake_share_group))
        update_args = {
            'name': fake.ShareGroup.name,
            'description': fake.ShareGroup.description,
        }

        result = self.manager.update(fake.ShareGroup(), **update_args)

        self.assertIs(fake_share_group, result)
        self.assertFalse(mock_get.called)
        mock_update.assert_called_once_with(
            share_groups.RESOURCE_PATH % fake.ShareGroup.id,
            {share_groups.RESOURCE_NAME: update_args},
            share_groups.RESOURCE_NAME)

    def test_update_no_data(self):
        fake_share_group = fake.ShareGroup()
        mock_get = self.mock_object(
            self.manager, '_get', mock.Mock(return_value=fake_share_group))
        mock_update = self.mock_object(
            self.manager, '_update', mock.Mock(return_value=fake_share_group))
        update_args = {}

        result = self.manager.update(fake.ShareGroup(), **update_args)

        self.assertIs(fake_share_group, result)
        mock_get.assert_called_once_with(
            share_groups.RESOURCE_PATH % fake.ShareGroup.id,
            share_groups.RESOURCE_NAME)
        self.assertFalse(mock_update.called)

    def test_delete(self):
        mock_delete = self.mock_object(self.manager, '_delete')
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.delete(fake.ShareGroup())

        mock_delete.assert_called_once_with(
            share_groups.RESOURCE_PATH % fake.ShareGroup.id)
        self.assertFalse(mock_post.called)

    def test_delete_force(self):
        mock_delete = self.mock_object(self.manager, '_delete')
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.delete(fake.ShareGroup.id, force=True)

        self.assertFalse(mock_delete.called)
        mock_post.assert_called_once_with(
            share_groups.RESOURCE_PATH_ACTION % fake.ShareGroup.id,
            body={'force_delete': None})

    def test_reset_state(self):
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.reset_state(fake.ShareGroup(), 'fake_state')

        mock_post.assert_called_once_with(
            share_groups.RESOURCE_PATH_ACTION % fake.ShareGroup.id,
            body={'reset_status': {'status': 'fake_state'}})
