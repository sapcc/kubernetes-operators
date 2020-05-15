# Copyright 2015 Mirantis Inc.
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

from manilaclient.tests.functional import base


@ddt.ddt
class ExportLocationReadWriteTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ExportLocationReadWriteTest, cls).setUpClass()
        cls.share = cls.create_share(
            client=cls.get_user_client(),
            cleanup_in_class=True)

    @ddt.data('admin', 'user')
    def test_list_share_export_locations(self, role):
        self.skip_if_microversion_not_supported('2.14')

        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_share_export_locations(
            self.share['id'])

        self.assertGreater(len(export_locations), 0)
        expected_keys = ('ID', 'Path', 'Preferred')
        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['ID']))
            self.assertIn(el['Preferred'], ('True', 'False'))

    @ddt.data('admin', 'user')
    def test_list_share_export_locations_with_columns(self, role):
        self.skip_if_microversion_not_supported('2.9')

        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_share_export_locations(
            self.share['id'], columns='id,path')

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
    def test_get_share_export_location(self, role):
        self.skip_if_microversion_not_supported('2.14')

        client = self.admin_client if role == 'admin' else self.user_client
        export_locations = client.list_share_export_locations(
            self.share['id'])

        el = client.get_share_export_location(
            self.share['id'], export_locations[0]['ID'])

        expected_keys = ['path', 'updated_at', 'created_at', 'id', 'preferred']
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
                ('ID', 'id'), ('Path', 'path'), ('Preferred', 'preferred')):
            self.assertEqual(
                export_locations[0][list_k], el[get_k])

    def test_list_share_instance_export_locations(self):
        self.skip_if_microversion_not_supported('2.14')

        client = self.admin_client
        share_instances = client.list_share_instances(self.share['id'])
        self.assertGreater(len(share_instances), 0)
        self.assertIn('ID', share_instances[0])
        self.assertTrue(uuidutils.is_uuid_like(share_instances[0]['ID']))
        share_instance_id = share_instances[0]['ID']

        export_locations = client.list_share_instance_export_locations(
            share_instance_id)

        self.assertGreater(len(export_locations), 0)
        expected_keys = ('ID', 'Path', 'Is Admin only', 'Preferred')
        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['ID']))

    def test_list_share_instance_export_locations_with_columns(self):
        self.skip_if_microversion_not_supported('2.9')

        client = self.admin_client
        share_instances = client.list_share_instances(self.share['id'])
        self.assertGreater(len(share_instances), 0)
        self.assertIn('ID', share_instances[0])
        self.assertTrue(uuidutils.is_uuid_like(share_instances[0]['ID']))
        share_instance_id = share_instances[0]['ID']

        export_locations = client.list_share_instance_export_locations(
            share_instance_id, columns='id,path')

        self.assertGreater(len(export_locations), 0)
        expected_keys = ('Id', 'Path')
        unexpected_keys = ('Updated At', 'Created At', 'Is Admin only')
        for el in export_locations:
            for key in expected_keys:
                self.assertIn(key, el)
            for key in unexpected_keys:
                self.assertNotIn(key, el)
            self.assertTrue(uuidutils.is_uuid_like(el['Id']))

    def test_get_share_instance_export_location(self):
        self.skip_if_microversion_not_supported('2.14')

        client = self.admin_client
        share_instances = client.list_share_instances(self.share['id'])
        self.assertGreater(len(share_instances), 0)
        self.assertIn('ID', share_instances[0])
        self.assertTrue(uuidutils.is_uuid_like(share_instances[0]['ID']))
        share_instance_id = share_instances[0]['ID']

        export_locations = client.list_share_instance_export_locations(
            share_instance_id)

        el = client.get_share_instance_export_location(
            share_instance_id, export_locations[0]['ID'])

        expected_keys = (
            'path', 'updated_at', 'created_at', 'id', 'preferred',
            'is_admin_only', 'share_instance_id',
        )
        for key in expected_keys:
            self.assertIn(key, el)
        self.assertIn(el['is_admin_only'], ('True', 'False'))
        self.assertIn(el['preferred'], ('True', 'False'))
        self.assertTrue(uuidutils.is_uuid_like(el['id']))
        for list_k, get_k in (
                ('ID', 'id'), ('Path', 'path'), ('Preferred', 'preferred'),
                ('Is Admin only', 'is_admin_only')):
            self.assertEqual(
                export_locations[0][list_k], el[get_k])
