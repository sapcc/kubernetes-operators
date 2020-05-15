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
import unittest

from tempest.lib.exceptions import CommandFailed

from designateclient.functionaltests.base import BaseDesignateTest
from designateclient.functionaltests.client import DesignateCLI
from designateclient.functionaltests.datagen import random_zone_name
from designateclient.functionaltests.v2.fixtures import TransferRequestFixture
from designateclient.functionaltests.v2.fixtures import ZoneFixture


class TestZoneTransferRequest(BaseDesignateTest):

    def setUp(self):
        super(TestZoneTransferRequest, self).setUp()
        self.ensure_tld_exists('com')
        fixture = self.useFixture(ZoneFixture(
            name=random_zone_name(),
            email='test@example.com',
        ))
        self.zone = fixture.zone

    def test_list_zone_transfer_request(self):
        self.useFixture(TransferRequestFixture(self.zone))
        xfrs = self.clients.zone_transfer_request_list()
        self.assertGreater(len(xfrs), 0)

    def test_create_and_show_zone_transfer_request(self):
        transfer_request = self.useFixture(TransferRequestFixture(
            zone=self.zone,
            user='default',
            target_user='alt',
        )).transfer_request

        fetched_xfr = self.clients.zone_transfer_request_show(
            transfer_request.id)

        self.assertEqual(fetched_xfr.created_at, transfer_request.created_at)
        self.assertEqual(fetched_xfr.description, transfer_request.description)
        self.assertEqual(fetched_xfr.id, transfer_request.id)
        self.assertEqual(fetched_xfr.key, transfer_request.key)
        self.assertEqual(fetched_xfr.links, transfer_request.links)
        self.assertEqual(fetched_xfr.target_project_id,
                         transfer_request.target_project_id)
        self.assertEqual(fetched_xfr.updated_at, transfer_request.updated_at)
        self.assertEqual(fetched_xfr.status, transfer_request.status)
        self.assertEqual(fetched_xfr.zone_id, self.zone.id)
        self.assertEqual(fetched_xfr.zone_name, self.zone.name)

    def test_delete_zone_transfer_request(self):
        transfer_request = self.useFixture(TransferRequestFixture(
            zone=self.zone,
            user='default',
            target_user='alt',
        )).transfer_request

        self.clients.zone_transfer_request_delete(transfer_request.id)
        self.assertRaises(CommandFailed,
                          self.clients.zone_transfer_request_show,
                          transfer_request.id)

    @unittest.skip("Fails because `zone transfer request set` returns nothing")
    def test_set_zone_transfer_request(self):
        transfer_request = self.useFixture(TransferRequestFixture(
            zone=self.zone,
            description="old description",
        )).transfer_request

        self.assertEqual(transfer_request.description, "old description")

        updated_xfr = self.clients.zone_transfer_request_set(
            transfer_request.id,
            description="updated description")
        self.assertEqual(updated_xfr.description, "updated description")


class TestZoneTransferAccept(BaseDesignateTest):

    def setUp(self):
        super(TestZoneTransferAccept, self).setUp()
        self.ensure_tld_exists('com')
        fixture = self.useFixture(ZoneFixture(
            name=random_zone_name(),
            email='test@example.com',
        ))
        self.zone = fixture.zone

        self.target_client = DesignateCLI.as_user('alt')
        fixture = self.useFixture(TransferRequestFixture(
            zone=self.zone,
            user='default',
            target_user='alt',
            target_project_id=self.target_client.project_id,
        ))
        self.transfer_request = fixture.transfer_request

    def test_zone_transfer_accept_request(self):
        self.target_client.zone_transfer_accept_request(
            id=self.transfer_request.id,
            key=self.transfer_request.key,
        )
        self.target_client.zone_show(self.zone.id)
        self.assertRaises(CommandFailed, self.clients.zone_show, self.zone.id)
