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
class SnapshotExportLocationReadWriteTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(SnapshotExportLocationReadWriteTest, cls).setUpClass()
        cls.share = cls.create_share(
            client=cls.get_user_client(),
            cleanup_in_class=True)
        cls.snapshot = cls.create_snapshot(share=cls.share['id'],
                                           client=cls.get_user_client(),
                                           cleanup_in_class=True)

    @ddt.data('admin', 'user')
    def test_get_snapshot_export_location(self, role):
        client = self.admin_client if role == 'admin' else self.user_client

        export_locations = client.list_snapshot_export_locations(
            self.snapshot['id'])

        el = client.get_snapshot_export_location(
            self.snapshot['id'], export_locations[0]['ID'])

        expected_keys = ['path', 'id', 'updated_at', 'created_at']
        if role == 'admin':
            expected_keys.extend(['is_admin_only',
                                  'share_snapshot_instance_id'])
            self.assertTrue(uuidutils.is_uuid_like(
                el['share_snapshot_instance_id']))
            self.assertIn(el['is_admin_only'], ('True', 'False'))
        self.assertTrue(uuidutils.is_uuid_like(el['id']))
        for key in expected_keys:
            self.assertIn(key, el)

    @ddt.data('admin', 'user')
    def test_list_snapshot_export_locations(self, role):
        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_snapshot_export_locations(
            self.snapshot['id'])

        self.assertGreater(len(export_locations), 0)
        expected_keys = ('ID', 'Path')

        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['ID']))

    @ddt.data('admin', 'user')
    def test_list_snapshot_export_locations_with_columns(self, role):
        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_snapshot_export_locations(
            self.snapshot['id'], columns='id,path')

        self.assertGreater(len(export_locations), 0)
        expected_keys = ('Id', 'Path')
        unexpected_keys = ('Updated At', 'Created At')
        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            for key in unexpected_keys:
                self.assertNotIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['Id']))
