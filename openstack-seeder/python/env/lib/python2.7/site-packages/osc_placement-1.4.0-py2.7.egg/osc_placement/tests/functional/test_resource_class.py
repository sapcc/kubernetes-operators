# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

from osc_placement.tests.functional import base


CUSTOM_RC = 'CUSTOM_GPU_DEVICE_{}'.format(
    str(uuid.uuid4()).replace('-', '').upper())


class TestResourceClass(base.BaseTestCase):
    VERSION = '1.2'

    def test_list(self):
        rcs = self.resource_class_list()
        names = [rc['name'] for rc in rcs]
        self.assertIn('VCPU', names)
        self.assertIn('MEMORY_MB', names)
        self.assertIn('DISK_GB', names)

    def test_fail_create_if_incorrect_class(self):
        self.assertCommandFailed('JSON does not validate',
                                 self.resource_class_create, 'fake_class')
        self.assertCommandFailed('JSON does not validate',
                                 self.resource_class_create, 'CUSTOM_lower')
        self.assertCommandFailed('JSON does not validate',
                                 self.resource_class_create,
                                 'CUSTOM_GPU.INTEL')

    def test_create(self):
        self.resource_class_create(CUSTOM_RC)
        rcs = self.resource_class_list()
        names = [rc['name'] for rc in rcs]
        self.assertIn(CUSTOM_RC, names)
        self.resource_class_delete(CUSTOM_RC)

    def test_fail_show_if_unknown_class(self):
        self.assertCommandFailed('No such resource class',
                                 self.resource_class_show, 'UNKNOWN')

    def test_show(self):
        rc = self.resource_class_show('VCPU')
        self.assertEqual('VCPU', rc['name'])

    def test_fail_delete_unknown_class(self):
        self.assertCommandFailed('No such resource class',
                                 self.resource_class_delete, 'UNKNOWN')

    def test_fail_delete_standard_class(self):
        self.assertCommandFailed('Cannot delete standard resource class',
                                 self.resource_class_delete, 'VCPU')


class TestResourceClass17(base.BaseTestCase):
    VERSION = '1.7'

    def test_set_resource_class(self):
        self.resource_class_create(CUSTOM_RC)
        self.resource_class_set(CUSTOM_RC)
        self.resource_class_set(CUSTOM_RC + '1')
        rcs = self.resource_class_list()
        names = [rc['name'] for rc in rcs]
        self.assertIn(CUSTOM_RC, names)
        self.assertIn(CUSTOM_RC + '1', names)
        self.resource_class_delete(CUSTOM_RC)
        self.resource_class_delete(CUSTOM_RC + '1')
