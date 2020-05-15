# Copyright 2016 Huawei inc.
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
from manilaclient import exceptions
from manilaclient import extension
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_snapshot_instances


extensions = [
    extension.Extension('share_snapshot_instances', share_snapshot_instances),
]
cs = fakes.FakeClient(extensions=extensions)


@ddt.ddt
class SnapshotInstancesTest(utils.TestCase):

    def setUp(self):
        super(SnapshotInstancesTest, self).setUp()
        microversion = api_versions.APIVersion("2.19")
        mock_microversion = mock.Mock(api_version=microversion)
        self.manager = share_snapshot_instances.ShareSnapshotInstanceManager(
            api=mock_microversion)

    @ddt.data(True, False)
    def test_list(self, detailed):
        if detailed:
            url = '/snapshot-instances/detail'
        else:
            url = '/snapshot-instances'
        self.mock_object(self.manager, '_list', mock.Mock())
        self.manager.list(detailed=detailed, search_opts=None)
        self.manager._list.assert_called_once_with(url, 'snapshot_instances')

    @ddt.data(True, False)
    def test_list_with_snapshot(self, detailed):
        if detailed:
            url = '/snapshot-instances/detail'
        else:
            url = '/snapshot-instances'
        self.mock_object(self.manager, '_list', mock.Mock())
        self.manager.list(detailed=detailed, snapshot='snapshot_id')
        self.manager._list.assert_called_once_with(
            (url + '?snapshot_id=snapshot_id'), 'snapshot_instances',)

    def test_get(self):
        self.mock_object(self.manager, '_get', mock.Mock())
        self.manager.get('fake_snapshot_instance')
        self.manager._get.assert_called_once_with(
            '/snapshot-instances/' + 'fake_snapshot_instance',
            'snapshot_instance')

    def test_reset_instance_state(self):
        state = 'available'

        self.mock_object(self.manager, '_action', mock.Mock())
        self.manager.reset_state('fake_instance', state)
        self.manager._action.assert_called_once_with(
            "reset_status", 'fake_instance', {"status": state})

    @ddt.data('get', 'list', 'reset_state')
    def test_upsupported_microversion(self, method_name):
        unsupported_microversions = ('1.0', '2.18')
        arguments = {
            'instance': 'FAKE_INSTANCE',
        }
        if method_name in ('list'):
            arguments.clear()

        for microversion in unsupported_microversions:
            microversion = api_versions.APIVersion(microversion)
            mock_microversion = mock.Mock(api_version=microversion)
            manager = share_snapshot_instances.ShareSnapshotInstanceManager(
                api=mock_microversion)
            method = getattr(manager, method_name)
            self.assertRaises(exceptions.UnsupportedVersion,
                              method, **arguments)
