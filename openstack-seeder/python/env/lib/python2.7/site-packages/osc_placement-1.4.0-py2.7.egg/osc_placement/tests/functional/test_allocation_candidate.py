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


def sorted_resources(resource):
    return ','.join(sorted(resource.split(',')))


class TestAllocationCandidate(base.BaseTestCase):
    VERSION = '1.10'

    def test_list_no_resource_specified_error(self):
        self.assertCommandFailed(
            'At least one --resource must be specified',
            self.openstack, 'allocation candidate list')

    def test_list_non_key_value_resource_specified_error(self):
        self.assertCommandFailed(
            'Arguments to --resource must be of form '
            '<resource_class>=<value>',
            self.openstack, 'allocation candidate list --resource VCPU')

    def test_list_empty(self):
        self.assertEqual([], self.allocation_candidate_list(
            resources=['MEMORY_MB=999999999']))

    def test_list_one(self):
        rp = self.resource_provider_create()
        self.resource_inventory_set(rp['uuid'], 'MEMORY_MB=1024')
        candidates = self.allocation_candidate_list(
            resources=('MEMORY_MB=256',))
        self.assertIn(
            rp['uuid'],
            [candidate['resource provider'] for candidate in candidates])

    def assertResourceEqual(self, r1, r2):
        self.assertEqual(sorted_resources(r1), sorted_resources(r2))

    def test_list_multiple(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=16384', 'DISK_GB=1024')
        candidates = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'))
        rps = {c['resource provider']: c for c in candidates}
        self.assertResourceEqual(
            'MEMORY_MB=1024,DISK_GB=80', rps[rp1['uuid']]['allocation'])
        self.assertResourceEqual(
            'MEMORY_MB=1024,DISK_GB=80', rps[rp2['uuid']]['allocation'])
        self.assertResourceEqual(
            'MEMORY_MB=0/8192,DISK_GB=0/512',
            rps[rp1['uuid']]['inventory used/capacity'])
        self.assertResourceEqual(
            'MEMORY_MB=0/16384,DISK_GB=0/1024',
            rps[rp2['uuid']]['inventory used/capacity'])

    def test_list_shared(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(rp1['uuid'], 'MEMORY_MB=8192')
        self.resource_inventory_set(rp2['uuid'], 'DISK_GB=1024')
        agg = str(uuid.uuid4())
        self.resource_provider_aggregate_set(rp1['uuid'], agg)
        self.resource_provider_aggregate_set(rp2['uuid'], agg)
        self.resource_provider_trait_set(
            rp2['uuid'], 'MISC_SHARES_VIA_AGGREGATE')
        candidates = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'))
        rps = {c['resource provider']: c for c in candidates}
        self.assertResourceEqual(
            'MEMORY_MB=1024', rps[rp1['uuid']]['allocation'])
        self.assertResourceEqual(
            'DISK_GB=80', rps[rp2['uuid']]['allocation'])
        self.assertResourceEqual(
            'MEMORY_MB=0/8192', rps[rp1['uuid']]['inventory used/capacity'])
        self.assertResourceEqual(
            'DISK_GB=0/1024', rps[rp2['uuid']]['inventory used/capacity'])
        self.assertEqual(
            rps[rp2['uuid']]['#'], rps[rp1['uuid']]['#'])

    def test_fail_if_unknown_rc(self):
        self.assertCommandFailed(
            'No such resource',
            self.allocation_candidate_list,
            resources=('UNKNOWN=10',))


class TestAllocationCandidate112(TestAllocationCandidate):
    VERSION = '1.12'


class TestAllocationCandidate116(base.BaseTestCase):
    VERSION = '1.16'

    def test_list_limit(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')

        unlimited = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'))
        self.assertTrue(len(set([row['#'] for row in unlimited])) > 1)

        limited = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            limit=1)
        self.assertEqual(len(set([row['#'] for row in limited])), 1)


class TestAllocationCandidate117(base.BaseTestCase):
    VERSION = '1.17'

    def test_show_required_trait(self):
        rp1 = self.resource_provider_create()
        rp2 = self.resource_provider_create()
        self.resource_inventory_set(
            rp1['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_inventory_set(
            rp2['uuid'], 'MEMORY_MB=8192', 'DISK_GB=512')
        self.resource_provider_trait_set(
            rp1['uuid'], 'STORAGE_DISK_SSD', 'HW_NIC_SRIOV')
        self.resource_provider_trait_set(
            rp2['uuid'], 'STORAGE_DISK_HDD', 'HW_NIC_SRIOV')

        rps = self.allocation_candidate_list(
            resources=('MEMORY_MB=1024', 'DISK_GB=80'),
            required=('STORAGE_DISK_SSD',))

        candidate_dict = {rp['resource provider']: rp for rp in rps}
        self.assertIn(rp1['uuid'], candidate_dict)
        self.assertNotIn(rp2['uuid'], candidate_dict)
        self.assertEqual(
            set(candidate_dict[rp1['uuid']]['traits'].split(',')),
            set(['STORAGE_DISK_SSD', 'HW_NIC_SRIOV']))
