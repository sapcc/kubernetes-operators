# Copyright (c) 2017 Hitachi Data Systems
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
@testtools.skipUnless(CONF.run_snapshot_tests and
                      CONF.run_mount_snapshot_tests,
                      "Snapshots or mountable snapshots tests are disabled.")
@utils.skip_if_microversion_not_supported('2.32')
class SnapshotInstanceExportLocationReadWriteTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(SnapshotInstanceExportLocationReadWriteTest, cls).setUpClass()
        cls.share = cls.create_share(
            client=cls.get_user_client(),
            cleanup_in_class=True)
        cls.snapshot = cls.create_snapshot(share=cls.share['id'],
                                           client=cls.get_user_client(),
                                           cleanup_in_class=True)

    def test_get_snapshot_instance_export_location(self):
        client = self.admin_client
        snapshot_instances = client.list_snapshot_instances(
            self.snapshot['id'])

        self.assertGreater(len(snapshot_instances), 0)
        self.assertIn('ID', snapshot_instances[0])
        self.assertTrue(uuidutils.is_uuid_like(
            snapshot_instances[0]['ID']))

        snapshot_instance_id = snapshot_instances[0]['ID']

        export_locations = client.list_snapshot_instance_export_locations(
            snapshot_instance_id)

        el = client.get_snapshot_instance_export_location(
            snapshot_instance_id, export_locations[0]['ID'])
        expected_keys = ['path', 'id', 'is_admin_only',
                         'share_snapshot_instance_id', 'updated_at',
                         'created_at']

        for key in expected_keys:
            self.assertIn(key, el)
        for key, key_el in (
                ('ID', 'id'), ('Path', 'path'),
                ('Is Admin only', 'is_admin_only')):
            self.assertEqual(export_locations[0][key], el[key_el])
        self.assertTrue(uuidutils.is_uuid_like(
            el['share_snapshot_instance_id']))
        self.assertTrue(uuidutils.is_uuid_like(el['id']))
        self.assertIn(el['is_admin_only'], ('True', 'False'))

    def test_list_snapshot_instance_export_locations(self):
        client = self.admin_client
        snapshot_instances = client.list_snapshot_instances(
            self.snapshot['id'])

        self.assertGreater(len(snapshot_instances), 0)
        self.assertIn('ID', snapshot_instances[0])
        self.assertTrue(uuidutils.is_uuid_like(snapshot_instances[0]['ID']))

        snapshot_instance_id = snapshot_instances[0]['ID']

        export_locations = client.list_snapshot_instance_export_locations(
            snapshot_instance_id)

        self.assertGreater(len(export_locations), 0)

        expected_keys = ('ID', 'Path', 'Is Admin only')
        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['ID']))

    def test_list_snapshot_instance_export_locations_with_columns(self):
        client = self.admin_client
        snapshot_instances = client.list_snapshot_instances(
            self.snapshot['id'])

        self.assertGreater(len(snapshot_instances), 0)
        self.assertIn('ID', snapshot_instances[0])
        self.assertTrue(uuidutils.is_uuid_like(snapshot_instances[0]['ID']))
        snapshot_instance_id = snapshot_instances[0]['ID']

        export_locations = client.list_snapshot_instance_export_locations(
            snapshot_instance_id, columns='id,path')

        self.assertGreater(len(export_locations), 0)
        expected_keys = ('Id', 'Path')
        unexpected_keys = ('Updated At', 'Created At', 'Is Admin only')

        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            for key in unexpected_keys:
                self.assertNotIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['Id']))
