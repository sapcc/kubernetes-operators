# Copyright 2015 Chuck Fouts.
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
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_replicas

FAKE_REPLICA = 'fake_replica'


@ddt.ddt
class ShareReplicasTest(utils.TestCase):

    class _FakeShareReplica(object):
        id = 'fake_share_replica_id'

    def setUp(self):
        super(ShareReplicasTest, self).setUp()
        microversion = api_versions.APIVersion("2.11")
        self.manager = share_replicas.ShareReplicaManager(
            fakes.FakeClient(api_version=microversion))

    def test_create(self):
        values = {
            'availability_zone': 'az1',
            'share': 's1',
        }
        self._create_common(values)

    def test_create_with_share_network(self):
        values = {
            'availability_zone': 'az1',
            'share': 's1',
            'share_network': 'sn1',
        }
        self._create_common(values)

    def _create_common(self, values):

        with mock.patch.object(self.manager, '_create', fakes.fake_create):
            result = self.manager.create(**values)

            values['share_id'] = values.pop('share')
            body_expected = {share_replicas.RESOURCE_NAME: values}
            self.assertEqual(share_replicas.RESOURCES_PATH, result['url'])
            self.assertEqual(share_replicas.RESOURCE_NAME, result['resp_key'])
            self.assertEqual(body_expected, result['body'])

    def test_delete_str(self):
        with mock.patch.object(self.manager, '_delete', mock.Mock()):
            self.manager.delete(FAKE_REPLICA)
            self.manager._delete.assert_called_once_with(
                share_replicas.RESOURCE_PATH % FAKE_REPLICA)

    def test_delete_obj(self):
        replica = self._FakeShareReplica
        with mock.patch.object(self.manager, '_delete', mock.Mock()):
            self.manager.delete(replica)
            self.manager._delete.assert_called_once_with(
                share_replicas.RESOURCE_PATH % replica.id)

    def test_delete_with_force(self):
        with mock.patch.object(self.manager, '_action', mock.Mock()):
            self.manager.delete(FAKE_REPLICA, force=True)
            self.manager._action.assert_called_once_with(
                'force_delete', FAKE_REPLICA)

    def test_get(self):
        with mock.patch.object(self.manager, '_get', mock.Mock()):
            self.manager.get(FAKE_REPLICA)
            self.manager._get.assert_called_once_with(
                share_replicas.RESOURCE_PATH % FAKE_REPLICA,
                share_replicas.RESOURCE_NAME)

    def test_promote(self):
        with mock.patch.object(self.manager, '_action', mock.Mock()):
            self.manager.promote(FAKE_REPLICA)
            self.manager._action.assert_called_once_with(
                'promote', FAKE_REPLICA)

    def test_list(self):
        with mock.patch.object(self.manager, '_list', mock.Mock()):
            self.manager.list(search_opts=None)
            self.manager._list.assert_called_once_with(
                share_replicas.RESOURCES_PATH + '/detail',
                share_replicas.RESOURCES_NAME)

    def test_list_with_share(self):
        with mock.patch.object(self.manager, '_list', mock.Mock()):
            self.manager.list('share_id')
            share_uri = '?share_id=share_id'
            self.manager._list.assert_called_once_with(
                (share_replicas.RESOURCES_PATH + '/detail' + share_uri),
                share_replicas.RESOURCES_NAME)

    def test_resync(self):
        with mock.patch.object(self.manager, '_action', mock.Mock()):
            self.manager.resync(FAKE_REPLICA)
            self.manager._action.assert_called_once_with(
                'resync', FAKE_REPLICA)

    @ddt.data('reset_status', 'reset_replica_state')
    def test_reset_state_actions(self, action):
        attr = 'status' if action == 'reset_status' else 'replica_state'
        method = getattr(self.manager, action.replace('status', 'state'))
        with mock.patch.object(self.manager, '_action', mock.Mock()):
            method(FAKE_REPLICA, 'some_status')
            self.manager._action.assert_called_once_with(
                action, FAKE_REPLICA, {attr: 'some_status'})
