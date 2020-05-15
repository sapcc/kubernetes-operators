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
from designateclient.functionaltests.datagen import random_tld
from designateclient.functionaltests.v2.fixtures import TLDFixture


class TestTld(BaseDesignateTest):

    def setUp(self):
        super(TestTld, self).setUp()
        tld_name = random_tld()
        self.tld = self.useFixture(TLDFixture(
            name=tld_name,
            description='A random tld',
        )).tld

        self.assertEqual(self.tld.name, tld_name)
        self.assertEqual(self.tld.description, 'A random tld')

    def test_tld_list(self):
        tlds = self.clients.as_user('admin').tld_list()
        self.assertGreater(len(tlds), 0)

    def test_tld_create_and_show(self):
        tld = self.clients.as_user('admin').tld_show(self.tld.id)
        self.assertEqual(tld.name, self.tld.name)
        self.assertEqual(tld.created_at, self.tld.created_at)
        self.assertEqual(tld.id, self.tld.id)
        self.assertEqual(tld.name, self.tld.name)
        self.assertEqual(tld.updated_at, self.tld.updated_at)

    def test_tld_delete(self):
        client = self.clients.as_user('admin')
        client.tld_delete(self.tld.id)
        self.assertRaises(CommandFailed, client.tld_show, self.tld.id)

    def test_tld_set(self):
        client = self.clients.as_user('admin')
        updated_name = random_tld('updated')
        tld = client.tld_set(self.tld.id, name=updated_name,
                             description='An updated tld')
        self.assertEqual(tld.description, 'An updated tld')
        self.assertEqual(tld.name, updated_name)

    def test_tld_set_no_description(self):
        client = self.clients.as_user('admin')
        tld = client.tld_set(self.tld.id, no_description=True)
        self.assertEqual(tld.description, 'None')

    def test_no_set_tld_with_description_and_no_description(self):
        client = self.clients.as_user('admin')
        self.assertRaises(CommandFailed, client.tld_set, self.tld.id,
                          description='An updated tld',
                          no_description=True)


class TestTldNegative(BaseDesignateTest):

    def test_tld_invalid_commmand(self):
        client = self.clients.as_user('admin')
        self.assertRaises(CommandFailed, client.openstack, 'tld notacommand')

    def test_tld_create_invalid_flag(self):
        client = self.clients.as_user('admin')
        self.assertRaises(CommandFailed, client.openstack,
                          'tld create --notanoption "junk"')
