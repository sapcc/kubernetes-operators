"""
Copyright 2015 Rackspace

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
from tempest.lib.exceptions import CommandFailed

from designateclient.functionaltests.base import BaseDesignateTest
from designateclient.functionaltests.datagen import random_a_recordset_name
from designateclient.functionaltests.datagen import random_zone_name
from designateclient.functionaltests.v2.fixtures import RecordsetFixture
from designateclient.functionaltests.v2.fixtures import ZoneFixture


class TestRecordset(BaseDesignateTest):

    def setUp(self):
        super(TestRecordset, self).setUp()
        self.ensure_tld_exists('com')
        self.zone = self.useFixture(ZoneFixture(
            name=random_zone_name(),
            email='test@example.com',
        )).zone

        name = random_a_recordset_name(self.zone.name)
        self.recordset = self.useFixture(RecordsetFixture(
            zone_id=self.zone.id,
            name=name,
            records='1.2.3.4',
            description='An a recordset',
            type='A',
            ttl=1234,
        )).recordset

        self.assertEqual(self.recordset.name, name)
        self.assertEqual(self.recordset.records, '1.2.3.4')
        self.assertEqual(self.recordset.description, 'An a recordset')
        self.assertEqual(self.recordset.type, 'A')
        self.assertEqual(self.recordset.ttl, '1234')

    def test_recordset_list(self):
        rsets = self.clients.recordset_list(self.zone.id)
        self.assertGreater(len(rsets), 0)

    def test_recordset_create_and_show(self):
        rset = self.clients.recordset_show(self.zone.id, self.recordset.id)
        self.assertTrue(hasattr(self.recordset, 'action'))
        self.assertTrue(hasattr(rset, 'action'))
        self.assertEqual(self.recordset.created_at, rset.created_at)
        self.assertEqual(self.recordset.description, rset.description)
        self.assertEqual(self.recordset.id, rset.id)
        self.assertEqual(self.recordset.name, rset.name)
        self.assertEqual(self.recordset.records, rset.records)
        self.assertEqual(self.recordset.status, rset.status)
        self.assertEqual(self.recordset.ttl, rset.ttl)
        self.assertEqual(self.recordset.type, rset.type)
        self.assertEqual(self.recordset.updated_at, rset.updated_at)
        self.assertEqual(self.recordset.version, rset.version)
        self.assertEqual(self.recordset.zone_id, self.zone.id)

    def test_recordset_delete(self):
        rset = self.clients.recordset_delete(self.zone.id, self.recordset.id)
        self.assertEqual(rset.action, 'DELETE')
        self.assertEqual(rset.status, 'PENDING')

    def test_recordset_set(self):
        rset = self.clients.recordset_set(
            self.zone.id,
            self.recordset.id,
            records='2.3.4.5',
            ttl=2345,
            description='Updated description',
        )

        self.assertEqual(rset.records, '2.3.4.5')
        self.assertEqual(rset.ttl, '2345')
        self.assertEqual(rset.description, 'Updated description')

    def test_recordset_set_clear_ttl_and_description(self):
        rset = self.clients.recordset_set(
            self.zone.id,
            self.recordset.id,
            no_description=True,
            no_ttl=True,
        )

        self.assertEqual(rset.description, 'None')
        self.assertEqual(rset.ttl, 'None')


class TestRecordsetNegative(BaseDesignateTest):

    def test_invalid_option_on_recordset_create(self):
        cmd = 'recordset create de47d30b-41c5-4e38-b2c5-e0b908e19ec7 ' \
            'aaa.desig.com. --type A --records 1.2.3.4 ' \
            '--invalid "not valid"'
        self.assertRaises(CommandFailed, self.clients.openstack, cmd)

    def test_invalid_recordset_command(self):
        cmd = 'recordset hopefullynotvalid'
        self.assertRaises(CommandFailed, self.clients.openstack, cmd)
