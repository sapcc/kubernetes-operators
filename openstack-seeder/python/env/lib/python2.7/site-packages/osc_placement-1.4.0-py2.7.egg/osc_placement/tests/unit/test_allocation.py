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

from osc_lib import exceptions
from oslotest import base
import six

from osc_placement.resources import allocation


class TestAllocation(base.BaseTestCase):
    def test_parse_allocations(self):
        rp1 = str(uuid.uuid4())
        rp2 = str(uuid.uuid4())
        allocations = [
            'rp={},VCPU=4,MEMORY_MB=16324'.format(rp1),
            'rp={},VCPU=4,DISK_GB=4096'.format(rp2)]
        expected = {
            rp1: {'VCPU': 4, 'MEMORY_MB': 16324},
            rp2: {'VCPU': 4, 'DISK_GB': 4096},
        }
        self.assertDictEqual(
            expected, allocation.parse_allocations(allocations))

    def test_merge_allocations(self):
        rp1 = str(uuid.uuid4())
        allocations = [
            'rp={},VCPU=4,MEMORY_MB=16324'.format(rp1),
            'rp={},VCPU=4,DISK_GB=4096'.format(rp1)]
        expected = {
            rp1: {'VCPU': 4, 'MEMORY_MB': 16324, 'DISK_GB': 4096}}
        self.assertEqual(expected, allocation.parse_allocations(allocations))

    def test_fail_if_cannot_merge_allocations(self):
        rp1 = str(uuid.uuid4())
        allocations = [
            'rp={},VCPU=4,MEMORY_MB=16324'.format(rp1),
            'rp={},VCPU=8,DISK_GB=4096'.format(rp1)]
        ex = self.assertRaises(
            exceptions.CommandError, allocation.parse_allocations, allocations)
        self.assertEqual(
            'Conflict detected for resource provider %s resource class VCPU' %
            rp1, six.text_type(ex))

    def test_fail_if_incorrect_format(self):
        allocations = ['incorrect_format']
        self.assertRaisesRegexp(
            ValueError,
            'Incorrect allocation',
            allocation.parse_allocations, allocations)
        allocations = ['=,']
        self.assertRaisesRegexp(
            ValueError,
            '2 is required',
            allocation.parse_allocations, allocations)
        allocations = ['abc=155']
        self.assertRaisesRegexp(
            ValueError,
            'Incorrect allocation',
            allocation.parse_allocations, allocations)
        allocations = ['abc=155,xyz=999']
        self.assertRaisesRegexp(
            ValueError,
            'parameter is required',
            allocation.parse_allocations, allocations)
