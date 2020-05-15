# Copyright 2010 Jacob Kaplan-Moss
# Copyright 2011 OpenStack Foundation
# Copyright 2014 Mirantis, Inc.
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
from manilaclient import extension
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_snapshots


extensions = [
    extension.Extension('share_snapshots', share_snapshots),
]
cs = fakes.FakeClient(extensions=extensions)


@ddt.ddt
class ShareSnapshotsTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return share_snapshots.ShareSnapshotManager(api=mock_microversion)

    def test_create_share_snapshot(self):
        cs.share_snapshots.create(1234)
        cs.assert_called('POST', '/snapshots')

    @ddt.data(
        type('SnapshotUUID', (object, ), {'uuid': '1234'}),
        type('SnapshotID', (object, ), {'id': '1234'}),
        '1234')
    def test_get_share_snapshot(self, snapshot):
        snapshot = cs.share_snapshots.get(snapshot)
        cs.assert_called('GET', '/snapshots/1234')

    @ddt.data(
        type('SnapshotUUID', (object, ), {'uuid': '1234'}),
        type('SnapshotID', (object, ), {'id': '1234'}),
        '1234')
    def test_update_share_snapshot(self, snapshot):
        data = dict(foo='bar', quuz='foobar')
        snapshot = cs.share_snapshots.update(snapshot, **data)
        cs.assert_called('PUT', '/snapshots/1234', {'snapshot': data})

    @ddt.data(
        ("2.6", type('SnapshotUUID', (object, ), {'uuid': '1234'})),
        ("2.7", type('SnapshotUUID', (object, ), {'uuid': '1234'})),
        ("2.6", type('SnapshotID', (object, ), {'id': '1234'})),
        ("2.7", type('SnapshotID', (object, ), {'id': '1234'})),
        ("2.6", "1234"),
        ("2.7", "1234"),
    )
    @ddt.unpack
    def test_reset_snapshot_state(self, microversion, snapshot):
        manager = self._get_manager(microversion)
        state = 'available'
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            action_name = "reset_status"
        else:
            action_name = "os-reset_status"

        with mock.patch.object(manager, "_action", mock.Mock()):
            manager.reset_state(snapshot, state)

            manager._action.assert_called_once_with(
                action_name, snapshot, {"status": state})

    def test_delete_share_snapshot(self):
        snapshot = cs.share_snapshots.get(1234)
        cs.share_snapshots.delete(snapshot)
        cs.assert_called('DELETE', '/snapshots/1234')

    @ddt.data(
        ("2.6", type('SnapshotUUID', (object, ), {"uuid": "1234"})),
        ("2.6", "1234"),
        ("2.7", type('SnapshotUUID', (object, ), {"uuid": "1234"})),
        ("2.7", "1234"),
    )
    @ddt.unpack
    def test_force_delete_share_snapshot(self, microversion, snapshot):
        manager = self._get_manager(microversion)
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            action_name = "force_delete"
        else:
            action_name = "os-force_delete"

        with mock.patch.object(manager, "_action", mock.Mock()):
            manager.force_delete(snapshot)

            manager._action.assert_called_once_with(action_name, "1234")

    def test_list_share_snapshots_index(self):
        cs.share_snapshots.list(detailed=False)
        cs.assert_called('GET', '/snapshots')

    def test_list_share_snapshots_index_with_search_opts(self):
        search_opts = {'fake_str': 'fake_str_value', 'fake_int': 1}
        cs.share_snapshots.list(detailed=False, search_opts=search_opts)
        cs.assert_called(
            'GET', '/snapshots?fake_int=1&fake_str=fake_str_value')

    def test_list_share_snapshots_sort_by_asc_and_share_id(self):
        cs.share_snapshots.list(
            detailed=False, sort_key='share_id', sort_dir='asc')
        cs.assert_called('GET', '/snapshots?sort_dir=asc&sort_key=share_id')

    def test_list_share_snapshots_sort_by_desc_and_status(self):
        cs.share_snapshots.list(
            detailed=False, sort_key='status', sort_dir='desc')
        cs.assert_called('GET', '/snapshots?sort_dir=desc&sort_key=status')

    def test_list_share_snapshots_by_improper_direction(self):
        self.assertRaises(ValueError, cs.share_snapshots.list, sort_dir='fake')

    def test_list_share_snapshots_by_improper_key(self):
        self.assertRaises(ValueError, cs.share_snapshots.list, sort_key='fake')

    def test_list_share_snapshots_detail(self):
        cs.share_snapshots.list(detailed=True)
        cs.assert_called('GET', '/snapshots/detail')

    def test_manage_snapshot(self):
        share_id = "1234"
        provider_location = "fake_location"
        driver_options = {}
        name = "foo_name"
        description = "bar_description"
        expected_body = {
            "share_id": share_id,
            "provider_location": provider_location,
            "driver_options": driver_options,
            "name": name,
            "description": description,
        }
        version = api_versions.APIVersion("2.12")
        mock_microversion = mock.Mock(api_version=version)
        manager = share_snapshots.ShareSnapshotManager(api=mock_microversion)

        with mock.patch.object(manager, "_create",
                               mock.Mock(return_value="fake")):

            result = manager.manage(share_id, provider_location,
                                    driver_options=driver_options,
                                    name=name, description=description)

            self.assertEqual(manager._create.return_value, result)
            manager._create.assert_called_once_with(
                "/snapshots/manage", {"snapshot": expected_body}, "snapshot")

    def test_unmanage_snapshot(self):
        snapshot = "fake_snapshot"
        version = api_versions.APIVersion("2.12")
        mock_microversion = mock.Mock(api_version=version)
        manager = share_snapshots.ShareSnapshotManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.unmanage(snapshot)

            manager._action.assert_called_once_with("unmanage", snapshot)
            self.assertEqual("fake", result)

    def test_allow_access(self):
        snapshot = "fake_snapshot"
        access_type = "fake_type"
        access_to = "fake_to"

        access = ("foo", {"snapshot_access": "fake"})
        version = api_versions.APIVersion("2.32")
        mock_microversion = mock.Mock(api_version=version)
        manager = share_snapshots.ShareSnapshotManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value=access)):
            result = manager.allow(snapshot, access_type, access_to)
            self.assertEqual("fake", result)
            manager._action.assert_called_once_with(
                "allow_access", snapshot,
                {'access_type': access_type, 'access_to': access_to})

    def test_deny_access(self):
        snapshot = "fake_snapshot"
        access_id = "fake_id"

        version = api_versions.APIVersion("2.32")
        mock_microversion = mock.Mock(api_version=version)
        manager = share_snapshots.ShareSnapshotManager(api=mock_microversion)

        with mock.patch.object(manager, "_action"):
            manager.deny(snapshot, access_id)
            manager._action.assert_called_once_with(
                "deny_access", snapshot, {'access_id': access_id})

    def test_access_list(self):
        cs.share_snapshots.access_list(1234)
        cs.assert_called('GET', '/snapshots/1234/access-list')
