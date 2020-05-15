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
from designateclient.functionaltests.datagen import random_zone_file
from designateclient.functionaltests.v2.fixtures import ImportFixture


class TestZoneImport(BaseDesignateTest):

    def setUp(self):
        super(TestZoneImport, self).setUp()
        self.ensure_tld_exists('com')
        self.zone_file_contents = random_zone_file()

    def test_list_zone_imports(self):
        zone_import = self.useFixture(ImportFixture(
            zone_file_contents=self.zone_file_contents
        )).zone_import

        zone_imports = self.clients.zone_import_list()
        self.assertGreater(len(zone_imports), 0)
        self.assertTrue(self._is_entity_in_list(zone_import, zone_imports))

    def test_create_and_show_zone_import(self):
        zone_import = self.useFixture(ImportFixture(
            zone_file_contents=self.zone_file_contents
        )).zone_import

        fetched_import = self.clients.zone_import_show(zone_import.id)

        self.assertEqual(zone_import.created_at, fetched_import.created_at)
        self.assertEqual(zone_import.id, fetched_import.id)
        self.assertEqual(zone_import.project_id, fetched_import.project_id)

        # check both statuses to avoid a race condition, causing test failure.
        # we don't know when the import completes.
        self.assertIn(fetched_import.status, ['PENDING', 'COMPLETE'])

    def test_delete_zone_import(self):
        zone_import = self.useFixture(ImportFixture(
            zone_file_contents=self.zone_file_contents
        )).zone_import

        zone_imports = self.clients.zone_import_list()
        self.assertTrue(self._is_entity_in_list(zone_import, zone_imports))

        self.clients.zone_import_delete(zone_import.id)

        zone_imports = self.clients.zone_import_list()
        self.assertFalse(self._is_entity_in_list(zone_import, zone_imports))
