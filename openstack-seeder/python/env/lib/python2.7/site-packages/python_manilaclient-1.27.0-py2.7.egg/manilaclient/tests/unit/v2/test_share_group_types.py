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
from manilaclient.v2 import share_group_types as types


@ddt.ddt
class ShareGroupTypeTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupTypeTest, self).setUp()
        self.manager = types.ShareGroupTypeManager(fake.FakeClient())
        self.fake_group_specs = {'key1': 'value1', 'key2': 'value2'}
        self.fake_share_group_type_info = {
            'id': fake.ShareGroupType.id,
            'share_types': [fake.ShareType.id],
            'name': fake.ShareGroupType.name,
            'is_public': fake.ShareGroupType.is_public,
            'group_specs': self.fake_group_specs,
        }
        self.share_group_type = types.ShareGroupType(
            self.manager, self.fake_share_group_type_info, loaded=True)

    def test_repr(self):
        result = six.text_type(self.share_group_type)

        self.assertEqual(
            '<Share Group Type: %s>' % fake.ShareGroupType.name, result)

    @ddt.data((True, True), (False, False), (None, 'N/A'))
    @ddt.unpack
    def test_is_public(self, is_public, expected):
        fake_share_group_type_info = {'name': 'fake_name'}
        if is_public is not None:
            fake_share_group_type_info['is_public'] = is_public
        share_group_type = types.ShareGroupType(
            self.manager, fake_share_group_type_info, loaded=True)

        result = share_group_type.is_public

        self.assertEqual(expected, result)

    def test_get_keys(self):
        self.mock_object(self.manager.api.client, 'get')

        result = self.share_group_type.get_keys()

        self.assertEqual(self.fake_group_specs, result)
        self.assertFalse(self.manager.api.client.get.called)

    def test_get_keys_force_api_call(self):
        share_group_type = types.ShareGroupType(
            self.manager, self.fake_share_group_type_info, loaded=True)
        share_group_type._group_specs = {}
        self.manager.api.client.get = mock.Mock(return_value=(
            None, self.fake_share_group_type_info))

        result = share_group_type.get_keys(prefer_resource_data=False)

        self.assertEqual(self.fake_group_specs, result)
        self.manager.api.client.get.assert_called_once_with(
            types.GROUP_SPECS_RESOURCES_PATH % fake.ShareGroupType.id)

    def test_set_keys(self):
        mock_manager_create = self.mock_object(
            self.manager, '_create',
            mock.Mock(return_value=self.fake_group_specs))

        result = self.share_group_type.set_keys(self.fake_group_specs)

        self.assertEqual(result, self.fake_group_specs)
        expected_body = {'group_specs': self.fake_group_specs}
        mock_manager_create.assert_called_once_with(
            types.GROUP_SPECS_RESOURCES_PATH % fake.ShareGroupType.id,
            expected_body, types.GROUP_SPECS_RESOURCES_NAME, return_raw=True)

    def test_unset_keys(self):
        mock_manager_delete = self.mock_object(
            self.manager, '_delete', mock.Mock(return_value=None))

        result = self.share_group_type.unset_keys(self.fake_group_specs.keys())

        self.assertIsNone(result)
        mock_manager_delete.assert_has_calls([
            mock.call(types.GROUP_SPECS_RESOURCE_PATH %
                      (fake.ShareGroupType.id, 'key1')),
            mock.call(types.GROUP_SPECS_RESOURCE_PATH %
                      (fake.ShareGroupType.id, 'key2')),
        ], any_order=True)

    def test_unset_keys_error(self):
        mock_manager_delete = self.mock_object(
            self.manager, '_delete', mock.Mock(return_value='error'))

        result = self.share_group_type.unset_keys(
            sorted(self.fake_group_specs.keys()))

        self.assertEqual('error', result)
        mock_manager_delete.assert_called_once_with(
            types.GROUP_SPECS_RESOURCE_PATH % (fake.ShareGroupType.id, 'key1'))


@ddt.ddt
class ShareGroupTypeManagerTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupTypeManagerTest, self).setUp()
        self.manager = types.ShareGroupTypeManager(fake.FakeClient())
        self.fake_group_specs = {'key1': 'value1', 'key2': 'value2'}

    def test_create(self):
        fake_share_group_type = fake.ShareGroupType()
        mock_create = self.mock_object(
            self.manager, '_create',
            mock.Mock(return_value=fake_share_group_type))
        create_args = {
            'name': fake.ShareGroupType.name,
            'share_types': [fake.ShareType()],
            'is_public': False,
            'group_specs': self.fake_group_specs,
        }

        result = self.manager.create(**create_args)

        self.assertIs(fake_share_group_type, result)
        expected_body = {
            types.RESOURCE_NAME: {
                'name': fake.ShareGroupType.name,
                'share_types': [fake.ShareType().id],
                'is_public': False,
                'group_specs': self.fake_group_specs,
            },
        }
        mock_create.assert_called_once_with(
            types.RESOURCES_PATH, expected_body, types.RESOURCE_NAME)

    def test_create_no_share_type(self):
        create_args = {
            'name': fake.ShareGroupType.name,
            'share_types': [],
            'is_public': False,
            'group_specs': self.fake_group_specs,
        }

        self.assertRaises(ValueError, self.manager.create, **create_args)

    def test_create_using_unsupported_microversion(self):
        self.manager.api.api_version = manilaclient.API_MIN_VERSION

        self.assertRaises(exceptions.UnsupportedVersion, self.manager.create)

    def test_get(self):
        fake_share_group_type = fake.ShareGroupType()
        mock_get = self.mock_object(
            self.manager, '_get',
            mock.Mock(return_value=fake_share_group_type))

        result = self.manager.get(fake.ShareGroupType.id)

        self.assertIs(fake_share_group_type, result)
        mock_get.assert_called_once_with(
            types.RESOURCE_PATH % fake.ShareGroupType.id, types.RESOURCE_NAME)

    def test_list(self):
        fake_share_group_type = fake.ShareGroupType()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_type]))

        result = self.manager.list(search_opts=None)

        self.assertEqual([fake_share_group_type], result)
        mock_list.assert_called_once_with(
            types.RESOURCES_PATH + '?is_public=all', types.RESOURCES_NAME)

    def test_list_no_public(self):
        fake_share_group_type = fake.ShareGroupType()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_type]))

        result = self.manager.list(show_all=False)

        self.assertEqual([fake_share_group_type], result)
        mock_list.assert_called_once_with(
            types.RESOURCES_PATH, types.RESOURCES_NAME)

    def test_delete(self):
        mock_delete = self.mock_object(self.manager, '_delete')

        self.manager.delete(fake.ShareGroupType())

        mock_delete.assert_called_once_with(
            types.RESOURCE_PATH % fake.ShareGroupType.id)
