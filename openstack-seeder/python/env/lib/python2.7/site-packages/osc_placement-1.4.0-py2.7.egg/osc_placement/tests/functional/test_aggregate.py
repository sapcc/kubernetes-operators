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


class TestAggregate(base.BaseTestCase):
    VERSION = '1.1'

    def test_fail_if_no_rp(self):
        self.assertCommandFailed(
            'too few arguments',
            self.openstack,
            'resource provider aggregate list')

    def test_fail_if_rp_not_found(self):
        self.assertCommandFailed(
            'No resource provider',
            self.resource_provider_aggregate_list,
            'fake-uuid')

    def test_return_empty_list_if_no_aggregates(self):
        rp = self.resource_provider_create()
        self.assertEqual(
            [], self.resource_provider_aggregate_list(rp['uuid']))

    def test_success_set_aggregate(self):
        rp = self.resource_provider_create()
        aggs = {str(uuid.uuid4()) for _ in range(2)}
        rows = self.resource_provider_aggregate_set(
            rp['uuid'], *aggs)

        self.assertEqual(aggs, {r['uuid'] for r in rows})
        rows = self.resource_provider_aggregate_list(rp['uuid'])
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        self.resource_provider_aggregate_set(rp['uuid'])
        rows = self.resource_provider_aggregate_list(rp['uuid'])
        self.assertEqual([], rows)

    def test_set_aggregate_fail_if_no_rp(self):
        self.assertCommandFailed(
            'too few arguments',
            self.openstack,
            'resource provider aggregate set')

    def test_success_set_multiple_aggregates(self):
        # each rp is associated with two aggregates
        rps = [self.resource_provider_create() for _ in range(2)]
        aggs = {str(uuid.uuid4()) for _ in range(2)}
        for rp in rps:
            rows = self.resource_provider_aggregate_set(rp['uuid'], *aggs)
            self.assertEqual(aggs, {r['uuid'] for r in rows})
        # remove association for the first aggregate
        rows = self.resource_provider_aggregate_set(rps[0]['uuid'])
        self.assertEqual([], rows)
        # second rp should be in aggregates
        rows = self.resource_provider_aggregate_list(rps[1]['uuid'])
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        # cleanup
        rows = self.resource_provider_aggregate_set(rps[1]['uuid'])
        self.assertEqual([], rows)

    def test_success_set_large_number_aggregates(self):
        rp = self.resource_provider_create()
        aggs = {str(uuid.uuid4()) for _ in range(100)}
        rows = self.resource_provider_aggregate_set(
            rp['uuid'], *aggs)
        self.assertEqual(aggs, {r['uuid'] for r in rows})
        rows = self.resource_provider_aggregate_set(rp['uuid'])
        self.assertEqual([], rows)

    def test_fail_if_incorrect_aggregate_uuid(self):
        rp = self.resource_provider_create()
        self.assertCommandFailed(
            "is not a 'uuid'",
            self.resource_provider_aggregate_set,
            rp['uuid'], 'abc', 'efg')
