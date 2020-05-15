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
from manilaclient.v2 import share_group_snapshots as snapshots


class ShareGroupSnapshotTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupSnapshotTest, self).setUp()
        self.manager = snapshots.ShareGroupSnapshotManager(fake.FakeClient())
        self.share_group_snapshot = snapshots.ShareGroupSnapshot(
            self.manager, {'id': 'fake_id'})
        self.fake_kwargs = {'key': 'value'}

    def test_repr(self):
        result = six.text_type(self.share_group_snapshot)

        self.assertEqual('<Share Group Snapshot: fake_id>', result)

    def test_update(self):
        mock_manager_update = self.mock_object(self.manager, 'update')

        self.share_group_snapshot.update(**self.fake_kwargs)

        mock_manager_update.assert_called_once_with(
            self.share_group_snapshot, **self.fake_kwargs)

    def test_delete(self):
        mock_manager_delete = self.mock_object(self.manager, 'delete')

        self.share_group_snapshot.delete()

        mock_manager_delete.assert_called_once_with(self.share_group_snapshot)

    def test_reset_state(self):
        mock_manager_reset_state = self.mock_object(
            self.manager, 'reset_state')

        self.share_group_snapshot.reset_state('fake_state')

        mock_manager_reset_state.assert_called_once_with(
            self.share_group_snapshot, 'fake_state')


@ddt.ddt
class ShareGroupSnapshotManagerTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupSnapshotManagerTest, self).setUp()
        self.manager = snapshots.ShareGroupSnapshotManager(fake.FakeClient())

    def test_create(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_create = self.mock_object(
            self.manager, '_create',
            mock.Mock(return_value=fake_share_group_snapshot))
        create_args = {
            'name': fake.ShareGroupSnapshot.name,
            'description': fake.ShareGroupSnapshot.description,
        }

        result = self.manager.create(fake.ShareGroupSnapshot, **create_args)

        self.assertIs(fake_share_group_snapshot, result)
        expected_body = {
            snapshots.RESOURCE_NAME: {
                'name': fake.ShareGroupSnapshot.name,
                'description': fake.ShareGroupSnapshot.description,
                'share_group_id': fake.ShareGroupSnapshot().id,
            },
        }
        mock_create.assert_called_once_with(
            snapshots.RESOURCES_PATH, expected_body, snapshots.RESOURCE_NAME)

    def test_create_minimal_args(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_create = self.mock_object(
            self.manager, '_create',
            mock.Mock(return_value=fake_share_group_snapshot))

        result = self.manager.create(fake.ShareGroupSnapshot)

        self.assertIs(fake_share_group_snapshot, result)
        expected_body = {
            snapshots.RESOURCE_NAME: {
                'share_group_id': fake.ShareGroupSnapshot().id,
            },
        }
        mock_create.assert_called_once_with(
            snapshots.RESOURCES_PATH, expected_body, snapshots.RESOURCE_NAME)

    def test_create_using_unsupported_microversion(self):
        self.manager.api.api_version = manilaclient.API_MIN_VERSION

        self.assertRaises(
            exceptions.UnsupportedVersion,
            self.manager.create, fake.ShareGroupSnapshot)

    def test_get(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_get = self.mock_object(
            self.manager, '_get',
            mock.Mock(return_value=fake_share_group_snapshot))

        result = self.manager.get(fake.ShareGroupSnapshot.id)

        self.assertIs(fake_share_group_snapshot, result)
        mock_get.assert_called_once_with(
            snapshots.RESOURCE_PATH % fake.ShareGroupSnapshot.id,
            snapshots.RESOURCE_NAME)

    def test_list(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_snapshot]))

        result = self.manager.list()

        self.assertEqual([fake_share_group_snapshot], result)
        mock_list.assert_called_once_with(
            snapshots.RESOURCES_PATH + '/detail',
            snapshots.RESOURCES_NAME)

    def test_list_no_detail(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_snapshot]))

        result = self.manager.list(detailed=False)

        self.assertEqual([fake_share_group_snapshot], result)
        mock_list.assert_called_once_with(
            snapshots.RESOURCES_PATH, snapshots.RESOURCES_NAME)

    def test_list_with_filters(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_snapshot]))
        filters = {'all_tenants': 1, 'status': 'ERROR'}

        result = self.manager.list(detailed=False, search_opts=filters)

        self.assertEqual([fake_share_group_snapshot], result)
        expected_path = (snapshots.RESOURCES_PATH +
                         '?all_tenants=1&status=ERROR')
        mock_list.assert_called_once_with(
            expected_path, snapshots.RESOURCES_NAME)

    def test_list_with_sorting(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_snapshot]))

        result = self.manager.list(
            detailed=False, sort_dir='asc', sort_key='name')

        self.assertEqual([fake_share_group_snapshot], result)
        expected_path = (
            snapshots.RESOURCES_PATH + '?sort_dir=asc&sort_key=name')
        mock_list.assert_called_once_with(
            expected_path, snapshots.RESOURCES_NAME)

    @ddt.data({'sort_key': 'name', 'sort_dir': 'invalid'},
              {'sort_key': 'invalid', 'sort_dir': 'asc'})
    @ddt.unpack
    def test_list_with_invalid_sorting(self, sort_key, sort_dir):
        self.assertRaises(
            ValueError,
            self.manager.list, sort_dir=sort_dir, sort_key=sort_key)

    def test_update(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_get = self.mock_object(
            self.manager, '_get',
            mock.Mock(return_value=fake_share_group_snapshot))
        mock_update = self.mock_object(
            self.manager, '_update',
            mock.Mock(return_value=fake_share_group_snapshot))
        update_args = {
            'name': fake.ShareGroupSnapshot.name,
            'description': fake.ShareGroupSnapshot.description,
        }

        result = self.manager.update(fake.ShareGroupSnapshot(), **update_args)

        self.assertIs(fake_share_group_snapshot, result)
        self.assertFalse(mock_get.called)
        mock_update.assert_called_once_with(
            snapshots.RESOURCE_PATH % fake.ShareGroupSnapshot.id,
            {snapshots.RESOURCE_NAME: update_args},
            snapshots.RESOURCE_NAME)

    def test_update_no_data(self):
        fake_share_group_snapshot = fake.ShareGroupSnapshot()
        mock_get = self.mock_object(
            self.manager, '_get',
            mock.Mock(return_value=fake_share_group_snapshot))
        mock_update = self.mock_object(
            self.manager, '_update',
            mock.Mock(return_value=fake_share_group_snapshot))
        update_args = {}

        result = self.manager.update(fake.ShareGroupSnapshot(), **update_args)

        self.assertIs(fake_share_group_snapshot, result)
        mock_get.assert_called_once_with(
            snapshots.RESOURCE_PATH % fake.ShareGroupSnapshot.id,
            snapshots.RESOURCE_NAME)
        self.assertFalse(mock_update.called)

    def test_delete(self):
        mock_delete = self.mock_object(self.manager, '_delete')
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.delete(fake.ShareGroupSnapshot())

        mock_delete.assert_called_once_with(
            snapshots.RESOURCE_PATH % fake.ShareGroupSnapshot.id)
        self.assertFalse(mock_post.called)

    def test_delete_force(self):
        mock_delete = self.mock_object(self.manager, '_delete')
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.delete(fake.ShareGroupSnapshot.id, force=True)

        self.assertFalse(mock_delete.called)
        mock_post.assert_called_once_with(
            snapshots.RESOURCE_PATH_ACTION % fake.ShareGroupSnapshot.id,
            body={'force_delete': None})

    def test_reset_state(self):
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.reset_state(fake.ShareGroupSnapshot(), 'fake_state')

        mock_post.assert_called_once_with(
            snapshots.RESOURCE_PATH_ACTION % fake.ShareGroupSnapshot.id,
            body={'reset_status': {'status': 'fake_state'}})
