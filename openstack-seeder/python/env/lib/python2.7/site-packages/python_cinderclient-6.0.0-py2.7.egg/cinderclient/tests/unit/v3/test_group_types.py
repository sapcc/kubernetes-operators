# Copyright (c) 2016 EMC Corporation
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

from cinderclient import api_versions
from cinderclient import exceptions as exc
from cinderclient.v3 import group_types

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes

cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.11'))
pre_cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.10'))


class GroupTypesTest(utils.TestCase):

    def test_list_group_types(self):
        tl = cs.group_types.list()
        cs.assert_called('GET', '/group_types?is_public=None')
        self._assert_request_id(tl)
        for t in tl:
            self.assertIsInstance(t, group_types.GroupType)

    def test_list_group_types_pre_version(self):
        self.assertRaises(exc.VersionNotFoundForAPIMethod,
                          pre_cs.group_types.list)

    def test_list_group_types_not_public(self):
        t1 = cs.group_types.list(is_public=None)
        cs.assert_called('GET', '/group_types?is_public=None')
        self._assert_request_id(t1)

    def test_create(self):
        t = cs.group_types.create('test-type-3', 'test-type-3-desc')
        cs.assert_called('POST', '/group_types',
                         {'group_type': {
                          'name': 'test-type-3',
                          'description': 'test-type-3-desc',
                          'is_public': True
                          }})
        self.assertIsInstance(t, group_types.GroupType)
        self._assert_request_id(t)

    def test_create_non_public(self):
        t = cs.group_types.create('test-type-3', 'test-type-3-desc', False)
        cs.assert_called('POST', '/group_types',
                         {'group_type': {
                          'name': 'test-type-3',
                          'description': 'test-type-3-desc',
                          'is_public': False
                          }})
        self.assertIsInstance(t, group_types.GroupType)
        self._assert_request_id(t)

    def test_update(self):
        t = cs.group_types.update('1', 'test_type_1', 'test_desc_1', False)
        cs.assert_called('PUT',
                         '/group_types/1',
                         {'group_type': {'name': 'test_type_1',
                                         'description': 'test_desc_1',
                                         'is_public': False}})
        self.assertIsInstance(t, group_types.GroupType)
        self._assert_request_id(t)

    def test_get(self):
        t = cs.group_types.get('1')
        cs.assert_called('GET', '/group_types/1')
        self.assertIsInstance(t, group_types.GroupType)
        self._assert_request_id(t)

    def test_default(self):
        t = cs.group_types.default()
        cs.assert_called('GET', '/group_types/default')
        self.assertIsInstance(t, group_types.GroupType)
        self._assert_request_id(t)

    def test_set_key(self):
        t = cs.group_types.get(1)
        res = t.set_keys({'k': 'v'})
        cs.assert_called('POST',
                         '/group_types/1/group_specs',
                         {'group_specs': {'k': 'v'}})
        self._assert_request_id(res)

    def test_set_key_pre_version(self):
        t = group_types.GroupType(pre_cs, {'id': 1})
        self.assertRaises(exc.VersionNotFoundForAPIMethod,
             t.set_keys, {'k': 'v'})

    def test_unset_keys(self):
        t = cs.group_types.get(1)
        res = t.unset_keys(['k'])
        cs.assert_called('DELETE', '/group_types/1/group_specs/k')
        self._assert_request_id(res)

    def test_delete(self):
        t = cs.group_types.delete(1)
        cs.assert_called('DELETE', '/group_types/1')
        self._assert_request_id(t)
