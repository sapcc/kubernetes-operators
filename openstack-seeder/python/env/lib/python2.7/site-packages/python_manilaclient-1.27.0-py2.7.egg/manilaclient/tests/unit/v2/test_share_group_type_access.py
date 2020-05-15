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
from manilaclient.v2 import share_group_type_access as type_access


@ddt.ddt
class ShareGroupTypeAccessTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupTypeAccessTest, self).setUp()
        self.manager = type_access.ShareGroupTypeAccessManager(
            fake.FakeClient())
        fake_group_type_access_info = {'id': fake.ShareGroupTypeAccess.id}
        self.share_group_type_access = type_access.ShareGroupTypeAccess(
            self.manager, fake_group_type_access_info, loaded=True)

    def test_repr(self):
        result = six.text_type(self.share_group_type_access)

        self.assertEqual(
            '<Share Group Type Access: %s>' % fake.ShareGroupTypeAccess.id,
            result)


@ddt.ddt
class ShareGroupTypeAccessManagerTest(utils.TestCase):

    def setUp(self):
        super(ShareGroupTypeAccessManagerTest, self).setUp()
        self.manager = type_access.ShareGroupTypeAccessManager(
            fake.FakeClient())

    def test_list(self):
        fake_share_group_type_access = fake.ShareGroupTypeAccess()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_type_access]))

        result = self.manager.list(fake.ShareGroupType(), search_opts=None)

        self.assertEqual([fake_share_group_type_access], result)
        mock_list.assert_called_once_with(
            type_access.RESOURCE_PATH % fake.ShareGroupType.id,
            type_access.RESOURCE_NAME)

    def test_list_public(self):
        fake_share_group_type_access = fake.ShareGroupTypeAccess()
        mock_list = self.mock_object(
            self.manager, '_list',
            mock.Mock(return_value=[fake_share_group_type_access]))
        fake_share_group_type = fake.ShareGroupType()
        fake_share_group_type.is_public = True

        result = self.manager.list(fake_share_group_type)

        self.assertIsNone(result)
        self.assertFalse(mock_list.called)

    def test_list_using_unsupported_microversion(self):
        fake_share_group_type_access = fake.ShareGroupTypeAccess()
        self.manager.api.api_version = manilaclient.API_MIN_VERSION

        self.assertRaises(
            exceptions.UnsupportedVersion,
            self.manager.list, fake_share_group_type_access)

    def test_add_project_access(self):
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.add_project_access(fake.ShareGroupType(), 'fake_project')

        expected_body = {
            'addProjectAccess': {
                'project': 'fake_project',
            }
        }
        mock_post.assert_called_once_with(
            type_access.RESOURCE_PATH_ACTION % fake.ShareGroupType.id,
            body=expected_body)

    def test_remove_project_access(self):
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.remove_project_access(
            fake.ShareGroupType(), 'fake_project')

        expected_body = {
            'removeProjectAccess': {
                'project': 'fake_project',
            }
        }
        mock_post.assert_called_once_with(
            type_access.RESOURCE_PATH_ACTION % fake.ShareGroupType.id,
            body=expected_body)
