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
from designateclient.functionaltests.datagen import random_blacklist
from designateclient.functionaltests.v2.fixtures import BlacklistFixture


class TestBlacklist(BaseDesignateTest):

    def setUp(self):
        super(TestBlacklist, self).setUp()
        pattern = random_blacklist()
        self.blacklist = self.useFixture(BlacklistFixture(
            pattern=pattern,
            description='A random blacklist',
        )).blacklist

        self.assertEqual(self.blacklist.pattern, pattern)
        self.assertEqual(self.blacklist.description, 'A random blacklist')

    def test_zone_blacklist_list(self):
        blacklists = self.clients.as_user('admin').zone_blacklist_list()
        self.assertGreater(len(blacklists), 0)

    def test_zone_blacklist_create_and_show(self):
        client = self.clients.as_user('admin')
        blacklist = client.zone_blacklist_show(self.blacklist.id)

        self.assertEqual(self.blacklist.created_at, blacklist.created_at)
        self.assertEqual(self.blacklist.description, blacklist.description)
        self.assertEqual(self.blacklist.id, blacklist.id)
        self.assertEqual(self.blacklist.pattern, blacklist.pattern)
        self.assertEqual(self.blacklist.updated_at, blacklist.updated_at)

    def test_zone_blacklist_delete(self):
        client = self.clients.as_user('admin')
        client.zone_blacklist_delete(self.blacklist.id)
        self.assertRaises(CommandFailed, client.zone_blacklist_show,
                          self.blacklist.id)

    def test_zone_blacklist_set(self):
        client = self.clients.as_user('admin')
        updated_pattern = random_blacklist('updatedblacklist')
        blacklist = client.zone_blacklist_set(
            id=self.blacklist.id,
            pattern=updated_pattern,
            description='An updated blacklist',
        )

        self.assertEqual(blacklist.created_at, self.blacklist.created_at)
        self.assertEqual(blacklist.description, 'An updated blacklist')
        self.assertEqual(blacklist.id, self.blacklist.id)
        self.assertEqual(blacklist.pattern, updated_pattern)
        self.assertNotEqual(blacklist.updated_at, self.blacklist.updated_at)

    def test_zone_blacklist_set_no_description(self):
        client = self.clients.as_user('admin')
        blacklist = client.zone_blacklist_set(
            id=self.blacklist.id,
            no_description=True,
        )
        self.assertEqual(blacklist.description, 'None')

    def test_cannot_set_description_with_no_description_flag(self):
        client = self.clients.as_user('admin')
        self.assertRaises(CommandFailed, client.zone_blacklist_set,
                          self.blacklist.id,
                          pattern=random_blacklist(),
                          description='new description',
                          no_description=True)


class TestBlacklistNegative(BaseDesignateTest):

    def test_invalid_blacklist_command(self):
        client = self.clients.as_user('admin')
        cmd = 'zone blacklist notacommand'
        self.assertRaises(CommandFailed, client.openstack, cmd)

    def test_blacklist_create_invalid_flag(self):
        client = self.clients.as_user('admin')
        cmd = 'zone blacklist create --pattern helloworld --notaflag invalid'
        self.assertRaises(CommandFailed, client.openstack, cmd)
