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

from cinderclient.v2 import volume_type_access

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes

cs = fakes.FakeClient()

PROJECT_UUID = '11111111-1111-1111-111111111111'


class TypeAccessTest(utils.TestCase):

    def test_list(self):
        access = cs.volume_type_access.list(volume_type='3')
        cs.assert_called('GET', '/types/3/os-volume-type-access')
        self._assert_request_id(access)
        for a in access:
            self.assertIsInstance(a, volume_type_access.VolumeTypeAccess)

    def test_add_project_access(self):
        access = cs.volume_type_access.add_project_access('3', PROJECT_UUID)
        cs.assert_called('POST', '/types/3/action',
                         {'addProjectAccess': {'project': PROJECT_UUID}})
        self._assert_request_id(access)

    def test_remove_project_access(self):
        access = cs.volume_type_access.remove_project_access('3', PROJECT_UUID)
        cs.assert_called('POST', '/types/3/action',
                         {'removeProjectAccess': {'project': PROJECT_UUID}})
        self._assert_request_id(access)
