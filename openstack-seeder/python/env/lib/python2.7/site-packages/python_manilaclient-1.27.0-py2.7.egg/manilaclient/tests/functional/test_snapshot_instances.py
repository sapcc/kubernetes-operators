# Copyright 2016 Huawei inc.
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

import ddt
from oslo_utils import uuidutils
import testtools

from manilaclient import config
from manilaclient.tests.functional import base
from manilaclient.tests.functional import utils

CONF = config.CONF


@ddt.ddt
@testtools.skipUnless(CONF.run_snapshot_tests,
                      'Snapshot tests disabled.')
@utils.skip_if_microversion_not_supported('2.19')
class SnapshotInstancesTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(SnapshotInstancesTest, cls).setUpClass()
        cls.share = cls.create_share(
            client=cls.get_user_client(),
            cleanup_in_class=True)
        cls.snapshot = cls.create_snapshot(share=cls.share['id'],
                                           client=cls.get_user_client(),
                                           cleanup_in_class=True)

    def test_list_all_snapshot_instances(self):
        snapshot_instances = self.admin_client.list_snapshot_instances()

        self.assertGreater(len(snapshot_instances), 0)
        expected_keys = ('ID', 'Snapshot ID', 'Status')
        for si in snapshot_instances:
            for key in expected_keys:
                self.assertIn(key, si)
            self.assertTrue(uuidutils.is_uuid_like(si['ID']))
            self.assertTrue(uuidutils.is_uuid_like(si['Snapshot ID']))

    def test_list_all_snapshot_instances_details(self):
        snapshot_instances = self.admin_client.list_snapshot_instances(
            detailed=True)

        self.assertGreater(len(snapshot_instances), 0)
        expected_keys = ('ID', 'Snapshot ID', 'Status', 'Created_at',
                         'Updated_at', 'Share_id', 'Share_instance_id',
                         'Progress', 'Provider_location')
        for si in snapshot_instances:
            for key in expected_keys:
                self.assertIn(key, si)
            for key in ('ID', 'Snapshot ID', 'Share_id', 'Share_instance_id'):
                self.assertTrue(
                    uuidutils.is_uuid_like(si[key]))

    def test_list_snapshot_instance_with_snapshot(self):
        snapshot_instances = self.admin_client.list_snapshot_instances(
            snapshot_id=self.snapshot['id'])

        self.assertEqual(1, len(snapshot_instances))
        expected_keys = ('ID', 'Snapshot ID', 'Status')
        for si in snapshot_instances:
            for key in expected_keys:
                self.assertIn(key, si)
            self.assertTrue(uuidutils.is_uuid_like(si['ID']))
            self.assertTrue(uuidutils.is_uuid_like(si['Snapshot ID']))

    def test_list_snapshot_instance_with_columns(self):
        snapshot_instances = self.admin_client.list_snapshot_instances(
            self.snapshot['id'], columns='id,status')

        self.assertGreater(len(snapshot_instances), 0)
        expected_keys = ('Id', 'Status')
        unexpected_keys = ('Snapshot ID', )
        for si in snapshot_instances:
            for key in expected_keys:
                self.assertIn(key, si)
            for key in unexpected_keys:
                self.assertNotIn(key, si)
            self.assertTrue(uuidutils.is_uuid_like(si['Id']))

    def test_get_snapshot_instance(self):
        snapshot_instances = self.admin_client.list_snapshot_instances(
            self.snapshot['id'])

        snapshot_instance = self.admin_client.get_snapshot_instance(
            snapshot_instances[0]['ID'])
        self.assertGreater(len(snapshot_instance), 0)
        expected_keys = ('id', 'snapshot_id', 'status', 'created_at',
                         'updated_at', 'share_id', 'share_instance_id',
                         'progress', 'provider_location')

        for key in expected_keys:
            self.assertIn(key, snapshot_instance)
        for key in ('id', 'snapshot_id', 'share_id', 'share_instance_id'):
            self.assertTrue(
                uuidutils.is_uuid_like(snapshot_instance[key]))

    def test_snapshot_instance_reset_state(self):
        snapshot_instances = self.admin_client.list_snapshot_instances(
            self.snapshot['id'])
        self.admin_client.reset_snapshot_instance(
            snapshot_instances[0]['ID'], 'error')
        snapshot_instance = self.admin_client.get_snapshot_instance(
            snapshot_instances[0]['ID'])

        self.assertEqual('error', snapshot_instance['status'])
        self.admin_client.reset_snapshot_instance(snapshot_instance['id'],
                                                  'available')
