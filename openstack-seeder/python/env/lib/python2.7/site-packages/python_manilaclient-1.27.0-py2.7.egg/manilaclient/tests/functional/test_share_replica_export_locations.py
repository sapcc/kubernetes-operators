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
@testtools.skipUnless(CONF.run_replication_tests,
                      "Replication tests are disabled.")
@utils.skip_if_microversion_not_supported('2.47')
class ShareReplicaExportLocationsTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ShareReplicaExportLocationsTest, cls).setUpClass()

    def _create_share_and_replica(self):
        replication_type = CONF.replication_type
        share_type = self.create_share_type(
            driver_handles_share_servers=False,
            extra_specs={'replication_type': replication_type},
            cleanup_in_class=False)
        share = self.create_share(share_type=share_type['ID'],
                                  client=self.get_user_client())
        share_replica = self.create_share_replica(share['id'])
        return share, share_replica

    @ddt.data('admin', 'user')
    def test_list_share_export_locations(self, role):
        share, share_replica = self._create_share_and_replica()
        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_share_replica_export_locations(
            share_replica['id'])

        self.assertGreater(len(export_locations), 0)
        expected_keys = ['ID', 'Path', 'Preferred', 'Replica State',
                         'Availability Zone']

        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['ID']))
            self.assertIn(el['Preferred'], ('True', 'False'))

    @ddt.data('admin', 'user')
    def test_list_share_export_locations_with_columns(self, role):
        share, share_replica = self._create_share_and_replica()
        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_share_replica_export_locations(
            share_replica['id'], columns='id,path')

        self.assertGreater(len(export_locations), 0)
        expected_keys = ('Id', 'Path')
        unexpected_keys = ('Updated At', 'Created At')
        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            for key in unexpected_keys:
                self.assertNotIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['Id']))

    @ddt.data('admin', 'user')
    def test_get_share_replica_export_location(self, role):
        share, share_replica = self._create_share_and_replica()
        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_share_replica_export_locations(
            share_replica['id'])

        el = client.get_share_replica_export_location(
            share_replica['id'], export_locations[0]['ID'])

        expected_keys = ['path', 'updated_at', 'created_at', 'id',
                         'preferred', 'replica_state', 'availability_zone']
        if role == 'admin':
            expected_keys.extend(['is_admin_only', 'share_instance_id'])
        for key in expected_keys:
            self.assertIn(key, el)
        if role == 'admin':
            self.assertTrue(uuidutils.is_uuid_like(el['share_instance_id']))
            self.assertIn(el['is_admin_only'], ('True', 'False'))
        self.assertTrue(uuidutils.is_uuid_like(el['id']))
        self.assertIn(el['preferred'], ('True', 'False'))
        for list_k, get_k in (
                ('ID', 'id'), ('Path', 'path'), ('Preferred', 'preferred'),
                ('Replica State', 'replica_state'),
                ('Availability Zone', 'availability_zone')):
            self.assertEqual(
                export_locations[0][list_k], el[get_k])
