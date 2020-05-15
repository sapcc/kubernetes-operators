# Copyright (c) 2013 OpenStack Foundation
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

from cinderclient.v2 import volume_types

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes

cs = fakes.FakeClient()


class TypesTest(utils.TestCase):

    def test_list_types(self):
        tl = cs.volume_types.list()
        cs.assert_called('GET', '/types?is_public=None')
        self._assert_request_id(tl)
        for t in tl:
            self.assertIsInstance(t, volume_types.VolumeType)

    def test_list_types_not_public(self):
        t1 = cs.volume_types.list(is_public=None)
        cs.assert_called('GET', '/types?is_public=None')
        self._assert_request_id(t1)

    def test_create(self):
        t = cs.volume_types.create('test-type-3', 'test-type-3-desc')
        cs.assert_called('POST', '/types',
                         {'volume_type': {
                          'name': 'test-type-3',
                          'description': 'test-type-3-desc',
                          'os-volume-type-access:is_public': True
                          }})
        self.assertIsInstance(t, volume_types.VolumeType)
        self._assert_request_id(t)

    def test_create_non_public(self):
        t = cs.volume_types.create('test-type-3', 'test-type-3-desc', False)
        cs.assert_called('POST', '/types',
                         {'volume_type': {
                          'name': 'test-type-3',
                          'description': 'test-type-3-desc',
                          'os-volume-type-access:is_public': False
                          }})
        self.assertIsInstance(t, volume_types.VolumeType)
        self._assert_request_id(t)

    def test_update(self):
        t = cs.volume_types.update('1', 'test_type_1', 'test_desc_1', False)
        cs.assert_called('PUT',
                         '/types/1',
                         {'volume_type': {'name': 'test_type_1',
                                          'description': 'test_desc_1',
                                          'is_public': False}})
        self.assertIsInstance(t, volume_types.VolumeType)
        self._assert_request_id(t)

    def test_update_name(self):
        """Test volume_type update shell command

        Verify that only name is updated and the description and
        is_public properties remains unchanged.
        """
        # create volume_type with is_public True
        t = cs.volume_types.create('test-type-3', 'test_type-3-desc', True)
        self.assertTrue(t.is_public)
        # update name only
        t1 = cs.volume_types.update(t.id, 'test-type-2')
        cs.assert_called('PUT',
                         '/types/3',
                         {'volume_type': {'name': 'test-type-2',
                                          'description': None}})
        # verify that name is updated and the description
        # and is_public are the same.
        self.assertEqual('test-type-2', t1.name)
        self.assertEqual('test_type-3-desc', t1.description)
        self.assertTrue(t1.is_public)

    def test_get(self):
        t = cs.volume_types.get('1')
        cs.assert_called('GET', '/types/1')
        self.assertIsInstance(t, volume_types.VolumeType)
        self._assert_request_id(t)

    def test_default(self):
        t = cs.volume_types.default()
        cs.assert_called('GET', '/types/default')
        self.assertIsInstance(t, volume_types.VolumeType)
        self._assert_request_id(t)

    def test_set_key(self):
        t = cs.volume_types.get(1)
        res = t.set_keys({'k': 'v'})
        cs.assert_called('POST',
                         '/types/1/extra_specs',
                         {'extra_specs': {'k': 'v'}})
        self._assert_request_id(res)

    def test_unset_keys(self):
        t = cs.volume_types.get(1)
        res = t.unset_keys(['k'])
        cs.assert_called('DELETE', '/types/1/extra_specs/k')
        self._assert_request_id(res)

    def test_unset_multiple_keys(self):
        t = cs.volume_types.get(1)
        res = t.unset_keys(['k', 'm'])
        cs.assert_called_anytime('DELETE', '/types/1/extra_specs/k')
        cs.assert_called_anytime('DELETE', '/types/1/extra_specs/m')
        self._assert_request_id(res, count=2)

    def test_delete(self):
        t = cs.volume_types.delete(1)
        cs.assert_called('DELETE', '/types/1')
        self._assert_request_id(t)
