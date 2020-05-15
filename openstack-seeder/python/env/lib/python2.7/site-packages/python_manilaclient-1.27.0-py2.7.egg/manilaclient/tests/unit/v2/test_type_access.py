# Copyright (c) 2013 OpenStack Foundation
# Copyright (c) 2015 Mirantis, Inc.
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
from manilaclient.v2 import share_type_access

PROJECT_UUID = '11111111-1111-1111-111111111111'


@ddt.ddt
class TypeAccessTest(utils.TestCase):

    def _get_share_type_access_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return share_type_access.ShareTypeAccessManager(
            api=mock_microversion)

    @ddt.data(
        ("1.0", "os-share-type-access"),
        ("2.0", "os-share-type-access"),
        ("2.6", "os-share-type-access"),
        ("2.7", "share_type_access"),
    )
    @ddt.unpack
    def test_list(self, microversion, action_name):
        fake_access_list = ['foo', 'bar']
        share_type = mock.Mock()
        share_type.uuid = '3'
        share_type.is_public = False
        manager = self._get_share_type_access_manager(microversion)

        with mock.patch.object(manager, '_list',
                               mock.Mock(return_value=fake_access_list)):
            access = manager.list(share_type=share_type, search_opts=None)

            manager._list.assert_called_once_with(
                "/types/3/%s" % action_name, "share_type_access")
            self.assertEqual(fake_access_list, access)

    @ddt.data("1.0", "2.0", "2.6", "2.7")
    def test_list_public(self, microversion):
        share_type = mock.Mock()
        share_type.uuid = '4'
        share_type.is_public = True
        manager = self._get_share_type_access_manager(microversion)

        with mock.patch.object(manager, '_list',
                               mock.Mock(return_value='fake')):
            access = manager.list(share_type=share_type)

            self.assertFalse(manager._list.called)
            self.assertIsNone(access)

    @ddt.data("1.0", "2.0", "2.6", "2.7")
    def test_add_project_access(self, microversion):
        share_type = mock.Mock()
        manager = self._get_share_type_access_manager(microversion)

        with mock.patch.object(manager, '_action',
                               mock.Mock(return_value='fake_action')):
            manager.add_project_access(share_type, PROJECT_UUID)

            manager._action.assert_called_once_with(
                'addProjectAccess', share_type, {'project': PROJECT_UUID})

    @ddt.data("1.0", "2.0", "2.6", "2.7")
    def test_remove_project_access(self, microversion):
        share_type = mock.Mock()
        manager = self._get_share_type_access_manager(microversion)

        with mock.patch.object(manager, '_action',
                               mock.Mock(return_value='fake_action')):
            manager.remove_project_access(share_type, PROJECT_UUID)

            manager._action.assert_called_once_with(
                'removeProjectAccess', share_type, {'project': PROJECT_UUID})
