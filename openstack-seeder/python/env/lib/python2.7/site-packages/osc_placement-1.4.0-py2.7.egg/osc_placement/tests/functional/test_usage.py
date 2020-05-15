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

import operator
import subprocess
import uuid

from osc_placement.tests.functional import base


class TestUsage(base.BaseTestCase):
    def test_usage_show(self):
        consumer_uuid = str(uuid.uuid4())
        rp = self.resource_provider_create()
        self.resource_inventory_set(
            rp['uuid'],
            'VCPU=4',
            'VCPU:max_unit=4',
            'MEMORY_MB=1024',
            'MEMORY_MB:max_unit=1024')

        self.assertEqual([{'resource_class': 'MEMORY_MB', 'usage': 0},
                          {'resource_class': 'VCPU', 'usage': 0}],
                         sorted(self.resource_provider_show_usage(rp['uuid']),
                                key=operator.itemgetter('resource_class')))

        self.resource_allocation_set(
            consumer_uuid,
            ['rp={},VCPU=2'.format(rp['uuid']),
             'rp={},MEMORY_MB=512'.format(rp['uuid'])]
        )
        self.assertEqual([{'resource_class': 'MEMORY_MB', 'usage': 512},
                          {'resource_class': 'VCPU', 'usage': 2}],
                         sorted(self.resource_provider_show_usage(rp['uuid']),
                                key=operator.itemgetter('resource_class')))

    def test_usage_not_found(self):
        rp_uuid = str(uuid.uuid4())

        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_provider_show_usage,
                                rp_uuid)
        self.assertIn(
            'No resource provider with uuid {} found'.format(rp_uuid),
            exc.output.decode('utf-8')
        )

    def test_usage_empty(self):
        rp = self.resource_provider_create()

        self.assertEqual([], self.resource_provider_show_usage(rp['uuid']))


class TestResourceUsage(base.BaseTestCase):
    VERSION = '1.9'

    def test_usage_by_project_id_user_id(self):
        c1 = str(uuid.uuid4())
        c2 = str(uuid.uuid4())
        c3 = str(uuid.uuid4())
        p1 = str(uuid.uuid4())
        p2 = str(uuid.uuid4())
        u1 = str(uuid.uuid4())
        u2 = str(uuid.uuid4())

        rp = self.resource_provider_create()
        self.resource_inventory_set(rp['uuid'], 'VCPU=16')
        self.resource_allocation_set(
            c1, ['rp={},VCPU=2'.format(rp['uuid'])], project_id=p1, user_id=u1)
        self.resource_allocation_set(
            c2, ['rp={},VCPU=4'.format(rp['uuid'])], project_id=p2, user_id=u1)
        self.resource_allocation_set(
            c3, ['rp={},VCPU=6'.format(rp['uuid'])], project_id=p1, user_id=u2)

        # Show usage on the resource provider for all consumers.
        self.assertEqual(
            12, self.resource_provider_show_usage(uuid=rp['uuid'])[0]['usage'])
        # Show usage for project p1.
        self.assertEqual(
            8, self.resource_show_usage(project_id=p1)[0]['usage'])
        # Show usage for project p1 and user u1.
        self.assertEqual(
            2, self.resource_show_usage(
                project_id=p1, user_id=u1)[0]['usage'])
        # Show usage for project p2.
        self.assertEqual(
            4, self.resource_show_usage(project_id=p2)[0]['usage'])
