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
from designateclient.functionaltests.datagen import random_zone_name
from designateclient.functionaltests.v2.fixtures import ZoneFixture


class TestZone(BaseDesignateTest):

    def setUp(self):
        super(TestZone, self).setUp()
        self.ensure_tld_exists('com')
        self.fixture = self.useFixture(ZoneFixture(
            name=random_zone_name(),
            email='test@example.com',
        ))
        self.zone = self.fixture.zone

    def test_zone_list(self):
        zones = self.clients.zone_list()
        self.assertGreater(len(zones), 0)

    def test_zone_create_and_show(self):
        zone = self.clients.zone_show(self.zone.id)
        self.assertTrue(hasattr(zone, 'action'))
        self.assertEqual(self.zone.created_at, zone.created_at)
        self.assertEqual(self.zone.description, zone.description)
        self.assertEqual(self.zone.email, zone.email)
        self.assertEqual(self.zone.id, zone.id)
        self.assertEqual(self.zone.masters, zone.masters)
        self.assertEqual(self.zone.name, zone.name)
        self.assertEqual(self.zone.pool_id, zone.pool_id)
        self.assertEqual(self.zone.project_id, zone.project_id)
        self.assertEqual(self.zone.serial, zone.serial)
        self.assertTrue(hasattr(zone, 'status'))
        self.assertEqual(self.zone.transferred_at, zone.transferred_at)
        self.assertEqual(self.zone.ttl, zone.ttl)
        self.assertEqual(self.zone.type, zone.type)
        self.assertEqual(self.zone.updated_at, zone.updated_at)
        self.assertEqual(self.zone.version, zone.version)

    def test_zone_delete(self):
        zone = self.clients.zone_delete(self.zone.id)
        self.assertEqual(zone.action, 'DELETE')
        self.assertEqual(zone.status, 'PENDING')

    def test_zone_set(self):
        ttl = int(self.zone.ttl) + 123
        email = 'updated{0}'.format(self.zone.email)
        description = 'new description'

        zone = self.clients.zone_set(self.zone.id, ttl=ttl, email=email,
                                     description=description)
        self.assertEqual(ttl, int(zone.ttl))
        self.assertEqual(email, zone.email)
        self.assertEqual(description, zone.description)

    def test_invalid_option_on_zone_create(self):
        cmd = 'zone create %s --invalid "not a valid option"'.format(
            random_zone_name())
        self.assertRaises(CommandFailed, self.clients.openstack, cmd)

    def test_invalid_zone_command(self):
        cmd = 'zone hopefullynotacommand'
        self.assertRaises(CommandFailed, self.clients.openstack, cmd)


class TestsPassingZoneFlags(BaseDesignateTest):

    def setUp(self):
        super(TestsPassingZoneFlags, self).setUp()
        self.ensure_tld_exists('com')

    def test_zone_create_primary_with_all_args(self):
        zone_name = random_zone_name()
        fixture = self.useFixture(ZoneFixture(
            name=zone_name,
            email='primary@example.com',
            description='A primary zone',
            ttl=2345,
            type='PRIMARY',
        ))
        zone = fixture.zone
        self.assertEqual(zone_name, zone.name)
        self.assertEqual('primary@example.com', zone.email)
        self.assertEqual('A primary zone', zone.description)
        self.assertEqual('2345', zone.ttl)
        self.assertEqual('PRIMARY', zone.type)

    def test_zone_create_secondary_with_all_args(self):
        zone_name = random_zone_name()
        fixture = self.useFixture(ZoneFixture(
            name=zone_name,
            description='A secondary zone',
            type='SECONDARY',
            masters='127.0.0.1',
        ))
        zone = fixture.zone
        self.assertEqual(zone_name, zone.name)
        self.assertEqual('A secondary zone', zone.description)
        self.assertEqual('SECONDARY', zone.type)
        self.assertEqual('127.0.0.1', zone.masters)

    def test_zone_set_secondary_masters(self):
        fixture = self.useFixture(ZoneFixture(
            name=random_zone_name(),
            description='A secondary zone',
            type='SECONDARY',
            masters='127.0.0.1',
        ))
        zone = fixture.zone
        self.assertEqual('127.0.0.1', zone.masters)

        zone = self.clients.zone_set(zone.id, masters='127.0.0.2')
        self.assertEqual('127.0.0.2', zone.masters)
