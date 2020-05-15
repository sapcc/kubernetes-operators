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
import testtools

from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions

from manilaclient.common import constants
from manilaclient import config
from manilaclient.tests.functional import base
from manilaclient.tests.functional import utils

CONF = config.CONF


@ddt.ddt
class ShareServersReadOnlyTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(ShareServersReadOnlyTest, cls).setUpClass()
        cls.client = cls.get_admin_client()

    def test_share_server_list(self):
        self.client.list_share_servers()

    def test_share_server_list_with_host_param(self):
        self.client.list_share_servers(filters={'host': 'fake_host'})

    def test_share_server_list_with_status_param(self):
        self.client.list_share_servers(filters={'status': 'fake_status'})

    def test_share_server_list_with_share_network_param(self):
        self.client.list_share_servers(filters={'share_network': 'fake_sn'})

    def test_share_server_list_with_project_id_param(self):
        self.client.list_share_servers(
            filters={'project_id': 'fake_project_id'})

    @ddt.data(
        'host', 'status', 'project_id', 'share_network',
        'host,status,project_id,share_network',
    )
    def test_share_server_list_with_specified_columns(self, columns):
        self.client.list_share_servers(columns=columns)

    def test_share_server_list_by_user(self):
        self.assertRaises(
            exceptions.CommandFailed, self.user_client.list_share_servers)


@ddt.ddt
class ShareServersReadWriteBase(base.BaseTestCase):

    protocol = None

    @classmethod
    def setUpClass(cls):
        super(ShareServersReadWriteBase, cls).setUpClass()
        if not CONF.run_share_servers_tests:
            message = "share-servers tests are disabled."
            raise cls.skipException(message)
        if cls.protocol not in CONF.enable_protocols:
            message = "%s tests are disabled." % cls.protocol
            raise cls.skipException(message)

        cls.client = cls.get_admin_client()
        if not cls.client.share_network:
            message = "Can run only with DHSS=True mode"
            raise cls.skipException(message)

    def _create_share_and_share_network(self):
        name = data_utils.rand_name('autotest_share_name')
        description = data_utils.rand_name('autotest_share_description')

        common_share_network = self.client.get_share_network(
            self.client.share_network)
        neutron_net_id = (
            common_share_network['neutron_net_id']
            if 'none' not in common_share_network['neutron_net_id'].lower()
            else None)
        neutron_subnet_id = (
            common_share_network['neutron_subnet_id']
            if 'none' not in common_share_network['neutron_subnet_id'].lower()
            else None)
        share_network = self.client.create_share_network(
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id,
        )

        self.share = self.create_share(
            share_protocol=self.protocol,
            size=1,
            name=name,
            description=description,
            share_network=share_network['id'],
            client=self.client,
            wait_for_creation=True
        )
        self.share = self.client.get_share(self.share['id'])
        return self.share, share_network

    def _delete_share_and_share_server(self, share_id, share_server_id):
        # Delete share
        self.client.delete_share(share_id)
        self.client.wait_for_share_deletion(share_id)

        # Delete share server
        self.client.delete_share_server(share_server_id)
        self.client.wait_for_share_server_deletion(share_server_id)

    def test_get_and_delete_share_server(self):
        self.share, share_network = self._create_share_and_share_network()
        share_server_id = self.client.get_share(
            self.share['id'])['share_server_id']

        # Get share server
        server = self.client.get_share_server(share_server_id)
        expected_keys = (
            'id', 'host', 'status', 'created_at', 'updated_at',
            'share_network_id', 'share_network_name', 'project_id',
        )

        if utils.is_microversion_supported('2.49'):
            expected_keys += ('identifier', 'is_auto_deletable')

        for key in expected_keys:
            self.assertIn(key, server)

        self._delete_share_and_share_server(self.share['id'], share_server_id)

    @testtools.skipUnless(
        CONF.run_manage_tests, 'Share Manage/Unmanage tests are disabled.')
    @utils.skip_if_microversion_not_supported('2.49')
    def test_manage_and_unmanage_share_server(self):
        share, share_network = self._create_share_and_share_network()
        share_server_id = self.client.get_share(
            self.share['id'])['share_server_id']
        server = self.client.get_share_server(share_server_id)
        server_host = server['host']
        export_location = self.client.list_share_export_locations(
            self.share['id'])[0]['Path']
        share_host = share['host']
        identifier = server['identifier']

        self.assertEqual('True', server['is_auto_deletable'])

        # Unmanages share
        self.client.unmanage_share(share['id'])
        self.client.wait_for_share_deletion(share['id'])

        server = self.client.get_share_server(share_server_id)
        self.assertEqual('False', server['is_auto_deletable'])

        # Unmanages share server
        self.client.unmanage_server(share_server_id)
        self.client.wait_for_share_server_deletion(share_server_id)

        # Manage share server
        managed_share_server_id = self.client.share_server_manage(
            server_host, share_network['id'], identifier)
        self.client.wait_for_resource_status(
            managed_share_server_id, constants.STATUS_ACTIVE,
            resource_type='share_server')

        managed_server = self.client.get_share_server(managed_share_server_id)
        self.assertEqual('False', managed_server['is_auto_deletable'])

        # Manage share
        managed_share_id = self.client.manage_share(
            share_host, self.protocol, export_location,
            managed_share_server_id)
        self.client.wait_for_resource_status(managed_share_id,
                                             constants.STATUS_AVAILABLE)

        self._delete_share_and_share_server(managed_share_id,
                                            managed_share_server_id)


class ShareServersReadWriteNFSTest(ShareServersReadWriteBase):
    protocol = 'nfs'


class ShareServersReadWriteCIFSTest(ShareServersReadWriteBase):
    protocol = 'cifs'


def load_tests(loader, tests, _):
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is ShareServersReadWriteBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
