# Copyright (C) 2016 EMC Corporation.
#
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

from cinderclient import api_versions
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes

cs = fakes.FakeClient(api_versions.APIVersion('3.14'))


@ddt.ddt
class GroupSnapshotsTest(utils.TestCase):

    def test_delete_group_snapshot(self):
        s1 = cs.group_snapshots.list()[0]
        snap = s1.delete()
        self._assert_request_id(snap)
        cs.assert_called('DELETE', '/group_snapshots/1234')
        snap = cs.group_snapshots.delete('1234')
        cs.assert_called('DELETE', '/group_snapshots/1234')
        self._assert_request_id(snap)
        snap = cs.group_snapshots.delete(s1)
        cs.assert_called('DELETE', '/group_snapshots/1234')
        self._assert_request_id(snap)

    def test_create_group_snapshot(self):
        snap = cs.group_snapshots.create('group_snap')
        cs.assert_called('POST', '/group_snapshots')
        self._assert_request_id(snap)

    def test_create_group_snapshot_with_group_id(self):
        snap = cs.group_snapshots.create('1234')
        expected = {'group_snapshot': {'description': None,
                                       'name': None,
                                       'group_id': '1234'}}
        cs.assert_called('POST', '/group_snapshots', body=expected)
        self._assert_request_id(snap)

    def test_update_group_snapshot(self):
        s1 = cs.group_snapshots.list()[0]
        expected = {'group_snapshot': {'name': 'grp_snap2'}}
        snap = s1.update(name='grp_snap2')
        cs.assert_called('PUT', '/group_snapshots/1234', body=expected)
        self._assert_request_id(snap)
        snap = cs.group_snapshots.update('1234', name='grp_snap2')
        cs.assert_called('PUT', '/group_snapshots/1234', body=expected)
        self._assert_request_id(snap)
        snap = cs.group_snapshots.update(s1, name='grp_snap2')
        cs.assert_called('PUT', '/group_snapshots/1234', body=expected)
        self._assert_request_id(snap)

    def test_update_group_snapshot_no_props(self):
        ret = cs.group_snapshots.update('1234')
        self.assertIsNone(ret)

    def test_list_group_snapshot(self):
        lst = cs.group_snapshots.list()
        cs.assert_called('GET', '/group_snapshots/detail')
        self._assert_request_id(lst)

    @ddt.data(
        {'detailed': True, 'url': '/group_snapshots/detail'},
        {'detailed': False, 'url': '/group_snapshots'}
    )
    @ddt.unpack
    def test_list_group_snapshot_detailed(self, detailed, url):
        lst = cs.group_snapshots.list(detailed=detailed)
        cs.assert_called('GET', url)
        self._assert_request_id(lst)

    @ddt.data(
        {'foo': 'bar'},
        {'foo': 'bar', '123': None}
    )
    def test_list_group_snapshot_with_search_opts(self, opts):
        lst = cs.group_snapshots.list(search_opts=opts)
        cs.assert_called('GET', '/group_snapshots/detail?foo=bar')
        self._assert_request_id(lst)

    def test_get_group_snapshot(self):
        group_snapshot_id = '1234'
        snap = cs.group_snapshots.get(group_snapshot_id)
        cs.assert_called('GET', '/group_snapshots/%s' % group_snapshot_id)
        self._assert_request_id(snap)
