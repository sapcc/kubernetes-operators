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

import subprocess
import uuid

from osc_placement.tests.functional import base


class TestAllocation(base.BaseTestCase):
    def setUp(self):
        super(TestAllocation, self).setUp()

        self.rp1 = self.resource_provider_create()
        self.inv_cpu1 = self.resource_inventory_set(
            self.rp1['uuid'],
            'VCPU=4',
            'VCPU:max_unit=4',
            'MEMORY_MB=1024',
            'MEMORY_MB:max_unit=1024')

    def test_allocation_show_not_found(self):
        consumer_uuid = str(uuid.uuid4())

        result = self.resource_allocation_show(consumer_uuid)
        self.assertEqual([], result)

    def test_allocation_create(self):
        consumer_uuid = str(uuid.uuid4())

        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])]
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 2,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)

        # Test that specifying --project-id and --user-id before microversion
        # 1.8 does not result in an error (they will be ignored). We have
        # to specify use_json=False because there will be a warning in the
        # output which can't be json-decoded.
        output = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])],
            project_id='fake-project', user_id='fake-user', use_json=False)
        self.assertIn(
            '--project-id and --user-id options do not affect allocation for '
            '--os-placement-api-version less than 1.8', output)

    def test_allocation_create_empty(self):
        consumer_uuid = str(uuid.uuid4())

        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_allocation_set,
                                consumer_uuid, [])
        self.assertIn('At least one resource allocation must be specified',
                      exc.output.decode('utf-8'))

    def test_allocation_delete(self):
        consumer_uuid = str(uuid.uuid4())

        self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])]
        )
        self.assertTrue(self.resource_allocation_show(consumer_uuid))

        self.resource_allocation_delete(consumer_uuid)
        self.assertEqual([], self.resource_allocation_show(consumer_uuid))

    def test_allocation_delete_not_found(self):
        consumer_uuid = str(uuid.uuid4())

        msg = "No allocations for consumer '{}'".format(consumer_uuid)
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_allocation_delete, consumer_uuid)
        self.assertIn(msg, exc.output.decode('utf-8'))


class TestAllocation18(base.BaseTestCase):
    VERSION = '1.8'

    def test_allocation_create(self):
        consumer_uuid = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        rp1 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'],
            'VCPU=4',
            'VCPU:max_unit=4',
            'MEMORY_MB=1024',
            'MEMORY_MB:max_unit=1024')
        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(rp1['uuid'])],
            project_id=project_id, user_id=user_id
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': rp1['uuid'],
             'generation': 2,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)


class TestAllocation112(base.BaseTestCase):
    VERSION = '1.12'

    def setUp(self):
        super(TestAllocation112, self).setUp()

        self.rp1 = self.resource_provider_create()
        self.inv_cpu1 = self.resource_inventory_set(
            self.rp1['uuid'],
            'VCPU=4',
            'VCPU:max_unit=4',
            'MEMORY_MB=1024',
            'MEMORY_MB:max_unit=1024')

    def test_allocation_update(self):
        consumer_uuid = str(uuid.uuid4())
        project_uuid = str(uuid.uuid4())
        user_uuid = str(uuid.uuid4())

        created_alloc = self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(self.rp1['uuid']),
             'rp={},MEMORY_MB=512'.format(self.rp1['uuid'])],
            project_id=project_uuid, user_id=user_uuid
        )
        retrieved_alloc = self.resource_allocation_show(consumer_uuid)

        expected = [
            {'resource_provider': self.rp1['uuid'],
             'generation': 2,
             'project_id': project_uuid,
             'user_id': user_uuid,
             'resources': {'VCPU': 2, 'MEMORY_MB': 512}}
        ]
        self.assertEqual(expected, created_alloc)
        self.assertEqual(expected, retrieved_alloc)
