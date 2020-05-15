# Copyright (C) 2012 - 2014 EMC Corporation.
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

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes


cs = fakes.FakeClient()


class cgsnapshotsTest(utils.TestCase):

    def test_delete_cgsnapshot(self):
        v = cs.cgsnapshots.list()[0]
        vol = v.delete()
        self._assert_request_id(vol)
        cs.assert_called('DELETE', '/cgsnapshots/1234')
        vol = cs.cgsnapshots.delete('1234')
        cs.assert_called('DELETE', '/cgsnapshots/1234')
        self._assert_request_id(vol)
        vol = cs.cgsnapshots.delete(v)
        cs.assert_called('DELETE', '/cgsnapshots/1234')
        self._assert_request_id(vol)

    def test_create_cgsnapshot(self):
        vol = cs.cgsnapshots.create('cgsnap')
        cs.assert_called('POST', '/cgsnapshots')
        self._assert_request_id(vol)

    def test_create_cgsnapshot_with_cg_id(self):
        vol = cs.cgsnapshots.create('1234')
        expected = {'cgsnapshot': {'status': 'creating',
                                   'description': None,
                                   'user_id': None,
                                   'name': None,
                                   'consistencygroup_id': '1234',
                                   'project_id': None}}
        cs.assert_called('POST', '/cgsnapshots', body=expected)
        self._assert_request_id(vol)

    def test_update_cgsnapshot(self):
        v = cs.cgsnapshots.list()[0]
        expected = {'cgsnapshot': {'name': 'cgs2'}}
        vol = v.update(name='cgs2')
        cs.assert_called('PUT', '/cgsnapshots/1234', body=expected)
        self._assert_request_id(vol)
        vol = cs.cgsnapshots.update('1234', name='cgs2')
        cs.assert_called('PUT', '/cgsnapshots/1234', body=expected)
        self._assert_request_id(vol)
        vol = cs.cgsnapshots.update(v, name='cgs2')
        cs.assert_called('PUT', '/cgsnapshots/1234', body=expected)
        self._assert_request_id(vol)

    def test_update_cgsnapshot_no_props(self):
        cs.cgsnapshots.update('1234')

    def test_list_cgsnapshot(self):
        lst = cs.cgsnapshots.list()
        cs.assert_called('GET', '/cgsnapshots/detail')
        self._assert_request_id(lst)

    def test_list_cgsnapshot_detailed_false(self):
        lst = cs.cgsnapshots.list(detailed=False)
        cs.assert_called('GET', '/cgsnapshots')
        self._assert_request_id(lst)

    def test_list_cgsnapshot_with_search_opts(self):
        lst = cs.cgsnapshots.list(search_opts={'foo': 'bar'})
        cs.assert_called('GET', '/cgsnapshots/detail?foo=bar')
        self._assert_request_id(lst)

    def test_list_cgsnapshot_with_empty_search_opt(self):
        lst = cs.cgsnapshots.list(search_opts={'foo': 'bar', '123': None})
        cs.assert_called('GET', '/cgsnapshots/detail?foo=bar')
        self._assert_request_id(lst)

    def test_get_cgsnapshot(self):
        cgsnapshot_id = '1234'
        vol = cs.cgsnapshots.get(cgsnapshot_id)
        cs.assert_called('GET', '/cgsnapshots/%s' % cgsnapshot_id)
        self._assert_request_id(vol)
