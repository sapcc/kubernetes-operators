"""
Copyright 2017 SAP SE

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
from designateclient.functionaltests.datagen import random_tsigkey_name
from designateclient.functionaltests.datagen import random_tsigkey_secret
from designateclient.functionaltests.datagen import random_zone_name
from designateclient.functionaltests.v2.fixtures import TSIGKeyFixture
from designateclient.functionaltests.v2.fixtures import ZoneFixture


class TestTSIGKey(BaseDesignateTest):
    def setUp(self):
        super(TestTSIGKey, self).setUp()
        self.ensure_tsigkey_exists('com')
        self.zone = self.useFixture(ZoneFixture(
            name=random_zone_name(),
            email='test@example.com',
        )).zone
        tsig_name = random_tsigkey_name()
        tsig_algorithm = "hmac-sha256"
        tsig_secret = random_tsigkey_secret()
        tsig_scope = 'ZONE'
        self.tsig = self.useFixture(TSIGKeyFixture(
            name=tsig_name,
            algorithm=tsig_algorithm,
            secret=tsig_secret,
            scope=tsig_scope,
            resource_id=self.zone.id
        )).tsig

        self.assertEqual(self.tsig.name, tsig_name)
        self.assertEqual(self.tsig.algorithm, tsig_algorithm)
        self.assertEqual(self.tsig.secret, tsig_secret)
        self.assertEqual(self.tsig.scope, tsig_scope)
        self.assertEqual(self.tsig.resource_id, self.zone.id)

    def test_tsigkey_list(self):
        tsigkeys = self.clients.as_user('admin').tsigkey_list()
        self.assertGreater(len(tsigkeys), 0)

    def test_tsigkey_create_and_show(self):
        tsigkey = self.clients.as_user('admin').tsigkey_show(self.tsigkey.id)
        self.assertEqual(tsigkey.name, self.tsigkey.name)
        self.assertEqual(tsigkey.created_at, self.tsigkey.created_at)
        self.assertEqual(tsigkey.id, self.tsigkey.id)
        self.assertEqual(self.tsig.algorithm, self.tsig_algorithm)
        self.assertEqual(self.tsig.secret, self.tsig_secret)
        self.assertEqual(self.tsig.scope, self.tsig_scope)
        self.assertEqual(self.tsig.resource_id, self.zone.id)
        self.assertEqual(tsigkey.updated_at, self.tsigkey.updated_at)

    def test_tsigkey_delete(self):
        client = self.clients.as_user('admin')
        client.tsigkey_delete(self.tsigkey.id)
        self.assertRaises(CommandFailed, client.tsigkey_show, self.tsigkey.id)

    def test_tsigkey_set(self):
        client = self.clients.as_user('admin')
        updated_name = random_tsigkey_name('updated')
        tsigkey = client.tsigkey_set(self.tsigkey.id, name=updated_name,
                                     secret='An updated tsigsecret')
        self.assertEqual(tsigkey.secret, 'An updated tsigsecret')
        self.assertEqual(tsigkey.name, updated_name)


class TestTSIGKeyNegative(BaseDesignateTest):
    def test_tsigkey_invalid_commmand(self):
        client = self.clients.as_user('admin')
        self.assertRaises(CommandFailed, client.openstack,
                          'tsigkey notacommand')

    def test_tsigkey_create_invalid_flag(self):
        client = self.clients.as_user('admin')
        self.assertRaises(CommandFailed, client.openstack,
                          'tsigkey create --notanoption "junk"')
