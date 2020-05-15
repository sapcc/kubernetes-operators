"""
Copyright 2016 Rackspace

Author: Rahman Syed <rahman.syed@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from designateclient.functionaltests.base import BaseDesignateTest
from designateclient.functionaltests.datagen import random_zone_name
from designateclient.functionaltests.v2.fixtures import ExportFixture
from designateclient.functionaltests.v2.fixtures import ZoneFixture


class TestZoneExport(BaseDesignateTest):

    def setUp(self):
        super(TestZoneExport, self).setUp()
        self.ensure_tld_exists('com')
        fixture = self.useFixture(ZoneFixture(
            name=random_zone_name(),
            email='test@example.com',
        ))
        self.zone = fixture.zone

    def test_list_zone_exports(self):
        zone_export = self.useFixture(ExportFixture(
            zone=self.zone
        )).zone_export

        zone_exports = self.clients.zone_export_list()
        self.assertGreater(len(zone_exports), 0)
        self.assertTrue(self._is_entity_in_list(zone_export, zone_exports))

    def test_create_and_show_zone_export(self):
        zone_export = self.useFixture(ExportFixture(
            zone=self.zone
        )).zone_export

        fetched_export = self.clients.zone_export_show(zone_export.id)

        self.assertEqual(zone_export.created_at, fetched_export.created_at)
        self.assertEqual(zone_export.id, fetched_export.id)
        self.assertEqual(zone_export.message, fetched_export.message)
        self.assertEqual(zone_export.project_id, fetched_export.project_id)
        self.assertEqual(zone_export.zone_id, fetched_export.zone_id)

    def test_delete_zone_export(self):
        zone_export = self.useFixture(ExportFixture(
            zone=self.zone
        )).zone_export

        zone_exports = self.clients.zone_export_list()
        self.assertTrue(self._is_entity_in_list(zone_export, zone_exports))

        self.clients.zone_export_delete(zone_export.id)

        zone_exports = self.clients.zone_export_list()
        self.assertFalse(self._is_entity_in_list(zone_export, zone_exports))

    def test_show_export_file(self):
        zone_export = self.useFixture(ExportFixture(
            zone=self.zone
        )).zone_export

        fetched_export = self.clients.zone_export_showfile(zone_export.id)

        self.assertIn('$ORIGIN', fetched_export.data)
        self.assertIn('$TTL', fetched_export.data)
        self.assertIn('SOA', fetched_export.data)
        self.assertIn('NS', fetched_export.data)
        self.assertIn(self.zone.name, fetched_export.data)
