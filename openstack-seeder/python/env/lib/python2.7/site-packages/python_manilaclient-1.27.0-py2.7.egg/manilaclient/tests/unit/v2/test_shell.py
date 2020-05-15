# -*- coding: utf-8 -*-
# Copyright 2013 OpenStack Foundation
# Copyright 2014 Mirantis, Inc.
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
import fixtures
import itertools
import mock
from oslo_utils import strutils
import six

from manilaclient import api_versions
from manilaclient import client
from manilaclient.common.apiclient import utils as apiclient_utils
from manilaclient.common import cliutils
from manilaclient.common import constants
from manilaclient import exceptions
from manilaclient import shell
from manilaclient.tests.unit import utils as test_utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient import utils
from manilaclient.v2 import messages
from manilaclient.v2 import security_services
from manilaclient.v2 import share_instances
from manilaclient.v2 import share_networks
from manilaclient.v2 import share_servers
from manilaclient.v2 import share_snapshots
from manilaclient.v2 import share_types
from manilaclient.v2 import shell as shell_v2


@ddt.ddt
class ShellTest(test_utils.TestCase):

    FAKE_ENV = {
        'MANILA_USERNAME': 'username',
        'MANILA_PASSWORD': 'password',
        'MANILA_PROJECT_ID': 'project_id',
        'MANILA_URL': 'http://no.where',
    }

    # Patch os.environ to avoid required auth info.
    def setUp(self):
        """Run before each test."""
        super(ShellTest, self).setUp()
        for var in self.FAKE_ENV:
            self.useFixture(fixtures.EnvironmentVariable(var,
                                                         self.FAKE_ENV[var]))

        self.shell = shell.OpenStackManilaShell()

        # HACK(bcwaldon): replace this when we start using stubs
        self.old_get_client_class = client.get_client_class
        client.get_client_class = lambda *_: fakes.FakeClient

        # Following shows available separators for optional params
        # and its values
        self.separators = [' ', '=']
        self.create_share_body = {
            "share": {
                "share_type": None,
                "name": None,
                "snapshot_id": None,
                "description": None,
                "metadata": {},
                "share_proto": "nfs",
                "share_network_id": None,
                "size": 1,
                "is_public": False,
                "availability_zone": None,
            }
        }

    def tearDown(self):
        # For some method like test_image_meta_bad_action we are
        # testing a SystemExit to be thrown and object self.shell has
        # no time to get instantatiated which is OK in this case, so
        # we make sure the method is there before launching it.
        if hasattr(self.shell, 'cs') and hasattr(self.shell.cs,
                                                 'clear_callstack'):
            self.shell.cs.clear_callstack()

        # HACK(bcwaldon): replace this when we start using stubs
        client.get_client_class = self.old_get_client_class
        super(ShellTest, self).tearDown()

    def run_command(self, cmd, version=None):
        if version:
            args = ['--os-share-api-version', version] + cmd.split()
        else:
            args = cmd.split()
        self.shell.main(args)

    def assert_called(self, method, url, body=None, **kwargs):
        return self.shell.cs.assert_called(method, url, body, **kwargs)

    def assert_called_anytime(self, method, url, body=None,
                              clear_callstack=True):
        return self.shell.cs.assert_called_anytime(
            method, url, body, clear_callstack=clear_callstack)

    def test_availability_zone_list(self):
        self.run_command('availability-zone-list')
        self.assert_called('GET', '/availability-zones')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_availability_zone_list_select_column(self):
        self.run_command('availability-zone-list --columns id,name')
        self.assert_called('GET', '/availability-zones')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=['Id', 'Name'])

    def test_service_list(self):
        self.run_command('service-list')
        self.assert_called('GET', '/services')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_service_list_select_column(self):
        self.run_command('service-list --columns id,host')
        self.assert_called('GET', '/services')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=['Id', 'Host'])

    def test_service_enable(self):
        self.run_command('service-enable foo_host@bar_backend manila-share')
        self.assert_called(
            'PUT',
            '/services/enable',
            {'host': 'foo_host@bar_backend', 'binary': 'manila-share'})

    def test_service_disable(self):
        self.run_command('service-disable foo_host@bar_backend manila-share')
        self.assert_called(
            'PUT',
            '/services/disable',
            {'host': 'foo_host@bar_backend', 'binary': 'manila-share'})

    def test_list(self):
        self.run_command('list')
        # NOTE(jdg): we default to detail currently
        self.assert_called('GET', '/shares/detail')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_list_select_column(self):
        self.run_command('list --column id,name')
        self.assert_called('GET', '/shares/detail')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['Id', 'Name'], sortby_index=None)

    def test_list_sort_by_name(self):
        self.run_command('list --sort_key name')
        self.assert_called('GET', '/shares/detail?sort_key=name')

    def test_list_filter_status(self):
        for separator in self.separators:
            self.run_command('list --status' + separator + 'available')
            self.assert_called('GET', '/shares/detail?status=available')

    def test_list_filter_name(self):
        for separator in self.separators:
            self.run_command('list --name' + separator + '1234')
            self.assert_called('GET', '/shares/detail?name=1234')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_list_all_tenants_only_key(self):
        self.run_command('list --all-tenants')
        self.assert_called('GET', '/shares/detail?all_tenants=1')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['ID', 'Name', 'Size', 'Share Proto', 'Status', 'Is Public',
             'Share Type Name', 'Host', 'Availability Zone', 'Project ID'],
            sortby_index=None)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_list_select_column_and_all_tenants(self):
        self.run_command('list --columns ID,Name --all-tenants')
        self.assert_called('GET', '/shares/detail?all_tenants=1')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['Id', 'Name'], sortby_index=None)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_list_select_column_and_public(self):
        self.run_command('list --columns ID,Name --public')
        self.assert_called('GET', '/shares/detail?is_public=True')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['Id', 'Name'], sortby_index=None)

    def test_list_all_tenants_key_and_value_1(self):
        for separator in self.separators:
            self.run_command('list --all-tenants' + separator + '1')
            self.assert_called('GET', '/shares/detail?all_tenants=1')

    def test_list_all_tenants_key_and_value_0(self):
        for separator in self.separators:
            self.run_command('list --all-tenants' + separator + '0')
            self.assert_called('GET', '/shares/detail')

    def test_list_filter_by_share_server_and_its_aliases(self):
        aliases = [
            '--share-server-id', '--share-server_id',
            '--share_server-id', '--share_server_id',
        ]
        for alias in aliases:
            for separator in self.separators:
                self.run_command('list ' + alias + separator + '1234')
                self.assert_called(
                    'GET', '/shares/detail?share_server_id=1234')

    def test_list_filter_by_metadata(self):
        self.run_command('list --metadata key=value')
        self.assert_called(
            'GET', '/shares/detail?metadata=%7B%27key%27%3A+%27value%27%7D')

    def test_list_filter_by_extra_specs_and_its_aliases(self):
        aliases = ['--extra-specs', '--extra_specs', ]
        for alias in aliases:
            self.run_command('list ' + alias + ' key=value')
            self.assert_called(
                'GET',
                '/shares/detail?extra_specs=%7B%27key%27%3A+%27value%27%7D',
            )

    def test_list_filter_by_share_type_and_its_aliases(self):
        fake_st = type('Empty', (object,), {'id': 'fake_st'})
        aliases = [
            '--share-type', '--share_type', '--share-type-id',
            '--share-type_id', '--share_type-id', '--share_type_id',
        ]
        for alias in aliases:
            for separator in self.separators:
                with mock.patch.object(
                        apiclient_utils,
                        'find_resource',
                        mock.Mock(return_value=fake_st)):
                    self.run_command('list ' + alias + separator + fake_st.id)
                    self.assert_called(
                        'GET', '/shares/detail?share_type_id=' + fake_st.id)

    def test_list_filter_by_inexact_name(self):
        for separator in self.separators:
            self.run_command('list --name~' + separator +
                             'fake_name')
            self.assert_called(
                'GET',
                '/shares/detail?name~=fake_name')

    def test_list_filter_by_inexact_description(self):
        for separator in self.separators:
            self.run_command('list --description~' + separator +
                             'fake_description')
            self.assert_called(
                'GET',
                '/shares/detail?description~=fake_description')

    def test_list_filter_by_inexact_unicode_name(self):
        for separator in self.separators:
            self.run_command('list --name~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/shares/detail?name~=%D1%84%D1%84%D1%84')

    def test_list_filter_by_inexact_unicode_description(self):
        for separator in self.separators:
            self.run_command('list --description~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/shares/detail?description~=%D1%84%D1%84%D1%84')

    def test_list_filter_by_share_type_not_found(self):
        for separator in self.separators:
            self.assertRaises(
                exceptions.CommandError,
                self.run_command,
                'list --share-type' + separator + 'not_found_expected',
            )
            self.assert_called('GET', '/types?all_tenants=1&is_public=all')

    def test_list_with_limit(self):
        for separator in self.separators:
            self.run_command('list --limit' + separator + '50')
            self.assert_called('GET', '/shares/detail?limit=50')

    def test_list_with_offset(self):
        for separator in self.separators:
            self.run_command('list --offset' + separator + '50')
            self.assert_called('GET', '/shares/detail?offset=50')

    def test_list_with_sort_dir_verify_keys(self):
        # Verify allowed aliases and keys
        aliases = ['--sort_dir', '--sort-dir']
        for alias in aliases:
            for key in constants.SORT_DIR_VALUES:
                for separator in self.separators:
                    self.run_command('list ' + alias + separator + key)
                    self.assert_called('GET', '/shares/detail?sort_dir=' + key)

    def test_list_with_fake_sort_dir(self):
        self.assertRaises(
            ValueError,
            self.run_command,
            'list --sort-dir fake_sort_dir',
        )

    def test_list_with_sort_key_verify_keys(self):
        # Verify allowed aliases and keys
        aliases = ['--sort_key', '--sort-key']
        for alias in aliases:
            for key in constants.SHARE_SORT_KEY_VALUES:
                for separator in self.separators:
                    self.run_command('list ' + alias + separator + key)
                    key = 'share_network_id' if key == 'share_network' else key
                    key = 'snapshot_id' if key == 'snapshot' else key
                    key = 'share_type_id' if key == 'share_type' else key
                    self.assert_called('GET', '/shares/detail?sort_key=' + key)

    def test_list_with_fake_sort_key(self):
        self.assertRaises(
            ValueError,
            self.run_command,
            'list --sort-key fake_sort_key',
        )

    def test_list_filter_by_snapshot(self):
        fake_s = type('Empty', (object,), {'id': 'fake_snapshot_id'})
        for separator in self.separators:
            with mock.patch.object(
                    apiclient_utils,
                    'find_resource',
                    mock.Mock(return_value=fake_s)):
                self.run_command('list --snapshot' + separator + fake_s.id)
                self.assert_called(
                    'GET', '/shares/detail?snapshot_id=' + fake_s.id)

    def test_list_filter_by_snapshot_not_found(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'list --snapshot not_found_expected',
        )
        self.assert_called('GET', '/snapshots/detail?all_tenants=1')

    def test_list_filter_by_host(self):
        for separator in self.separators:
            self.run_command('list --host' + separator + 'fake_host')
            self.assert_called('GET', '/shares/detail?host=fake_host')

    @ddt.data(('id', 'b4991315-eb7d-43ec-979e-5715d4399827'),
              ('path', 'fake_path'))
    @ddt.unpack
    def test_share_list_filter_by_export_location(self, filter_type, value):
        for separator in self.separators:
            self.run_command('list --export_location' + separator + value)
            self.assert_called(
                'GET',
                '/shares/detail?export_location_' + filter_type + '=' + value)

    @ddt.data('list', 'share-instance-list')
    def test_share_or_instance_list_filter_by_export_location_version_invalid(
            self, cmd):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            cmd + ' --export_location=fake',
            '2.34'
        )

    def test_list_filter_by_share_network(self):
        aliases = ['--share-network', '--share_network', ]
        fake_sn = type('Empty', (object,), {'id': 'fake_share_network_id'})
        for alias in aliases:
            for separator in self.separators:
                with mock.patch.object(
                        apiclient_utils,
                        'find_resource',
                        mock.Mock(return_value=fake_sn)):
                    self.run_command('list ' + alias + separator + fake_sn.id)
                    self.assert_called(
                        'GET', '/shares/detail?share_network_id=' + fake_sn.id)

    def test_list_filter_by_share_network_not_found(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'list --share-network not_found_expected',
        )
        self.assert_called('GET', '/share-networks/detail?all_tenants=1')

    @ddt.data('True', 'False')
    def test_list_filter_with_count(self, value):
        except_url = '/shares/detail?with_count=' + value
        if value == 'False':
            except_url = '/shares/detail'

        for separator in self.separators:
            self.run_command('list --count' + separator + value)
            self.assert_called('GET', except_url)

    @ddt.data('True', 'False')
    def test_list_filter_with_count_invalid_version(self, value):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'list --count ' + value,
            version='2.41'
        )

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_instance_list(self):
        self.run_command('share-instance-list')

        self.assert_called('GET', '/share_instances')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['ID', 'Share ID', 'Host', 'Status', 'Availability Zone',
             'Share Network ID', 'Share Server ID', 'Share Type ID'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_instance_list_select_column(self):
        self.run_command('share-instance-list --column id,host,status')

        self.assert_called('GET', '/share_instances')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['Id', 'Host', 'Status'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    @ddt.data(('id', 'b4991315-eb7d-43ec-979e-5715d4399827'),
              ('path', 'fake_path'))
    @ddt.unpack
    def test_share_instance_list_filter_by_export_location(self, filter_type,
                                                           value):
        for separator in self.separators:
            self.run_command('share-instance-list --export_location' +
                             separator + value)
            self.assert_called(
                'GET',
                ('/share_instances?export_location_' +
                 filter_type + '=' + value))

    @mock.patch.object(apiclient_utils, 'find_resource',
                       mock.Mock(return_value='fake'))
    def test_share_instance_list_with_share(self):
        self.run_command('share-instance-list --share-id=fake')
        self.assert_called('GET', '/shares/fake/instances')

    def test_share_instance_list_invalid_share(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'share-instance-list --share-id=not-found-id',
        )

    def test_share_instance_show(self):
        self.run_command('share-instance-show 1234')
        self.assert_called_anytime('GET', '/share_instances/1234')

    def test_share_instance_export_location_list(self):
        self.run_command('share-instance-export-location-list 1234')

        self.assert_called_anytime(
            'GET', '/share_instances/1234/export_locations')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_instance_export_location_list_with_columns(self):
        self.run_command(
            'share-instance-export-location-list 1234 --columns uuid,path')

        self.assert_called_anytime(
            'GET', '/share_instances/1234/export_locations')
        cliutils.print_list.assert_called_once_with(mock.ANY, ['Uuid', 'Path'])

    def test_share_instance_export_location_show(self):
        self.run_command(
            'share-instance-export-location-show 1234 fake_el_uuid')
        self.assert_called_anytime(
            'GET', '/share_instances/1234/export_locations/fake_el_uuid')

    def test_share_instance_reset_state(self):
        self.run_command('share-instance-reset-state 1234')
        expected = {'reset_status': {'status': 'available'}}
        self.assert_called('POST', '/share_instances/1234/action',
                           body=expected)

    def test_share_instance_force_delete(self):
        manager_mock = mock.Mock()
        share_instance = share_instances.ShareInstance(
            manager_mock, {'id': 'fake'}, True)

        with mock.patch.object(shell_v2, '_find_share_instance',
                               mock.Mock(return_value=share_instance)):
            self.run_command('share-instance-force-delete 1234')
            manager_mock.force_delete.assert_called_once_with(share_instance)

    def test_type_show_details(self):
        self.run_command('type-show 1234')
        self.assert_called_anytime('GET', '/types/1234')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    @ddt.data(*itertools.product(
        ('type-list --columns id,is_default', 'type-list --columns id,name',
         'type-list --columns is_default', 'type-list'),
        {'2.45', '2.46', api_versions.MAX_VERSION}))
    @ddt.unpack
    def test_type_list(self, command, version):
        self.run_command(command, version=version)

        columns_requested = ['ID', 'Name', 'visibility',
                             'is_default', 'required_extra_specs',
                             'optional_extra_specs', 'Description']
        if 'columns' in command:
            columns_requested = command.split('--columns ')[1].split(',')

        is_default_in_api = (api_versions.APIVersion(version) >=
                             api_versions.APIVersion('2.46'))

        if not is_default_in_api and 'is_default' in columns_requested:
            self.assert_called('GET', '/types/default')
            self.assert_called_anytime('GET', '/types')
        else:
            self.assert_called('GET', '/types')

        cliutils.print_list.assert_called_with(
            mock.ANY, columns_requested, mock.ANY)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_type_list_select_column(self):
        self.run_command('type-list --columns id,name')

        self.assert_called('GET', '/types')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['id', 'name'],
            mock.ANY)

    def test_type_list_all(self):
        self.run_command('type-list --all')
        self.assert_called_anytime('GET', '/types?is_public=all')

    @ddt.data(True, False)
    def test_type_create_with_access(self, public):
        expected = {
            'share_type': {
                'name': 'test-type-3',
                'extra_specs': {
                    'driver_handles_share_servers': False,
                },
                'share_type_access:is_public': public
            }
        }
        self.run_command(
            'type-create test-type-3 false --is-public %s' %
            six.text_type(public))
        self.assert_called('POST', '/types', body=expected)

    def test_type_access_list(self):
        self.run_command('type-access-list 3')
        self.assert_called('GET', '/types/3/share_type_access')

    def test_type_access_add_project(self):
        expected = {'addProjectAccess': {'project': '101'}}
        self.run_command('type-access-add 3 101')
        self.assert_called('POST', '/types/3/action', body=expected)

    def test_type_access_remove_project(self):
        expected = {'removeProjectAccess': {'project': '101'}}
        self.run_command('type-access-remove 3 101')
        self.assert_called('POST', '/types/3/action', body=expected)

    def test_list_filter_by_project_id(self):
        aliases = ['--project-id', '--project_id']
        for alias in aliases:
            for separator in self.separators:
                self.run_command('list ' + alias + separator + 'fake_id')
                self.assert_called('GET', '/shares/detail?project_id=fake_id')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_list_with_public_shares(self):
        listed_fields = [
            'ID',
            'Name',
            'Size',
            'Share Proto',
            'Status',
            'Is Public',
            'Share Type Name',
            'Host',
            'Availability Zone',
            'Project ID'
        ]
        self.run_command('list --public')
        self.assert_called('GET', '/shares/detail?is_public=True')
        cliutils.print_list.assert_called_with(mock.ANY, listed_fields,
                                               sortby_index=None)

    def test_show(self):
        self.run_command('show 1234')
        self.assert_called_anytime('GET', '/shares/1234')

    def test_share_export_location_list(self):
        self.run_command('share-export-location-list 1234')
        self.assert_called_anytime(
            'GET', '/shares/1234/export_locations')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_export_location_list_with_columns(self):
        self.run_command('share-export-location-list 1234 --columns uuid,path')

        self.assert_called_anytime(
            'GET', '/shares/1234/export_locations')
        cliutils.print_list.assert_called_once_with(mock.ANY, ['Uuid', 'Path'])

    def test_share_export_location_show(self):
        self.run_command('share-export-location-show 1234 fake_el_uuid')
        self.assert_called_anytime(
            'GET', '/shares/1234/export_locations/fake_el_uuid')

    @ddt.data({'cmd_args': '--driver_options opt1=opt1 opt2=opt2'
                           ' --share_type fake_share_type',
               'valid_params': {
                   'driver_options': {'opt1': 'opt1', 'opt2': 'opt2'},
                   'share_type': 'fake_share_type',
                   'share_server_id': None,
               }},
              {'cmd_args': '--share_type fake_share_type',
               'valid_params': {
                   'driver_options': {},
                   'share_type': 'fake_share_type',
                   'share_server_id': None,
               }},
              {'cmd_args': '',
               'valid_params': {
                   'driver_options': {},
                   'share_type': None,
                   'share_server_id': None,
               }},
              {'cmd_args': '--public',
               'valid_params': {
                   'driver_options': {},
                   'share_type': None,
                   'share_server_id': None,
               },
               'is_public': True,
               'version': '--os-share-api-version 2.8',
               },
              {'cmd_args': '',
               'valid_params': {
                   'driver_options': {},
                   'share_type': None,
                   'share_server_id': None,
               },
               'is_public': False,
               'version': '--os-share-api-version 2.8',
               },
              {'cmd_args': '--driver_options opt1=opt1 opt2=opt2'
                           ' --share_type fake_share_type',
               'valid_params': {
                   'driver_options': {'opt1': 'opt1', 'opt2': 'opt2'},
                   'share_type': 'fake_share_type',
                   'share_server_id': None,
               },
               'version': '--os-share-api-version 2.49',
               },
              {'cmd_args': '--driver_options opt1=opt1 opt2=opt2'
                           ' --share_type fake_share_type'
                           ' --share_server_id fake_server',
               'valid_params': {
                   'driver_options': {'opt1': 'opt1', 'opt2': 'opt2'},
                   'share_type': 'fake_share_type',
                   'share_server_id': 'fake_server',
               },
               'version': '--os-share-api-version 2.49',
               },
              {'cmd_args': '--driver_options opt1=opt1 opt2=opt2'
                           ' --share_type fake_share_type'
                           ' --share_server_id fake_server',
               'valid_params': {
                   'driver_options': {'opt1': 'opt1', 'opt2': 'opt2'},
                   'share_type': 'fake_share_type',
                   'share_server_id': 'fake_server',
               }},
              )
    @ddt.unpack
    def test_manage(self, cmd_args, valid_params, is_public=False,
                    version=None):
        if version is not None:
            self.run_command(version
                             + ' manage fake_service fake_protocol '
                             + ' fake_export_path '
                             + cmd_args)
        else:
            self.run_command(' manage fake_service fake_protocol '
                             + ' fake_export_path '
                             + cmd_args)
        expected = {
            'share': {
                'service_host': 'fake_service',
                'protocol': 'fake_protocol',
                'export_path': 'fake_export_path',
                'name': None,
                'description': None,
                'is_public': is_public,
                'share_server_id': valid_params['share_server_id'],
            }
        }
        expected['share'].update(valid_params)
        self.assert_called('POST', '/shares/manage', body=expected)

    def test_manage_invalid_param_share_server_id(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            '--os-share-api-version 2.48'
            + ' manage fake_service fake_protocol '
            + ' fake_export_path '
            + ' --driver_options opt1=opt1 opt2=opt2'
            + ' --share_type fake_share_type'
            + ' --share_server_id fake_server')

    @ddt.data({'driver_args': '--driver_options opt1=opt1 opt2=opt2',
               'valid_params': {
                   'driver_options': {'opt1': 'opt1', 'opt2': 'opt2'},
               },
               'version': '--os-share-api-version 2.49',
               },
              {'driver_args': '--driver_options opt1=opt1 opt2=opt2',
               'valid_params': {
                   'driver_options': {'opt1': 'opt1', 'opt2': 'opt2'},
               },
               },
              {'driver_args': "",
               'valid_params': {
                   'driver_options': {}
               },
               'version': '--os-share-api-version 2.49',
               })
    @ddt.unpack
    def test_share_server_manage(self, driver_args, valid_params,
                                 version=None):
        fake_share_network = type(
            'FakeShareNetwork', (object,), {'id': '3456'})
        self.mock_object(
            shell_v2, '_find_share_network',
            mock.Mock(return_value=fake_share_network))
        command = "" if version is None else version
        command += (' share-server-manage fake_host fake_share_net_id '
                    + ' 88-as-23-f3-45 ' + driver_args)

        self.run_command(command)

        expected = {
            'share_server': {
                'host': 'fake_host',
                'share_network_id': fake_share_network.id,
                'identifier': '88-as-23-f3-45',
                'driver_options': driver_args
            }
        }
        expected['share_server'].update(valid_params)

        self.assert_called('POST', '/share-servers/manage', body=expected)

    @ddt.data(constants.STATUS_ERROR, constants.STATUS_ACTIVE,
              constants.STATUS_MANAGE_ERROR, constants.STATUS_UNMANAGE_ERROR,
              constants.STATUS_DELETING, constants.STATUS_CREATING)
    def test_share_server_reset_state(self, status):
        self.run_command('share-server-reset-state 1234 --state %s ' % status)
        expected = {'reset_status': {'status': status}}
        self.assert_called('POST', '/share-servers/1234/action', body=expected)

    def test_unmanage(self):
        self.run_command('unmanage 1234')
        self.assert_called('POST', '/shares/1234/action')

    def test_share_server_unmanage(self):
        self.run_command('share-server-unmanage 1234')
        self.assert_called('POST', '/share-servers/1234/action',
                           body={'unmanage': {'force': False}})

    def test_share_server_unmanage_force(self):
        self.run_command('share-server-unmanage 1234 --force')
        self.assert_called('POST', '/share-servers/1234/action',
                           body={'unmanage': {'force': True}})

    @ddt.data({'cmd_args': '--driver_options opt1=opt1 opt2=opt2',
               'valid_params': {
                   'driver_options': {'opt1': 'opt1', 'opt2': 'opt2'},
               }},
              {'cmd_args': '',
               'valid_params': {
                   'driver_options': {},
               }},
              )
    @ddt.unpack
    @mock.patch.object(shell_v2, '_find_share', mock.Mock())
    def test_snapshot_manage(self, cmd_args, valid_params):
        shell_v2._find_share.return_value = 'fake_share'
        self.run_command('snapshot-manage fake_share fake_provider_location '
                         + cmd_args)
        expected = {
            'snapshot': {
                'share_id': 'fake_share',
                'provider_location': 'fake_provider_location',
                'name': None,
                'description': None,
            }
        }
        expected['snapshot'].update(valid_params)
        self.assert_called('POST', '/snapshots/manage', body=expected)

    def test_snapshot_unmanage(self):
        self.run_command('snapshot-unmanage 1234')
        self.assert_called('POST', '/snapshots/1234/action',
                           body={'unmanage': None})

    def test_revert_to_snapshot(self):

        fake_share_snapshot = type(
            'FakeShareSnapshot', (object,), {'id': '5678', 'share_id': '1234'})
        self.mock_object(
            shell_v2, '_find_share_snapshot',
            mock.Mock(return_value=fake_share_snapshot))

        self.run_command('revert-to-snapshot 5678')

        self.assert_called('POST', '/shares/1234/action',
                           body={'revert': {'snapshot_id': '5678'}})

    def test_delete(self):
        self.run_command('delete 1234')
        self.assert_called('DELETE', '/shares/1234')

    @ddt.data(
        '--group sg1313', '--share-group sg1313', '--share_group sg1313')
    @mock.patch.object(shell_v2, '_find_share_group', mock.Mock())
    def test_delete_with_share_group(self, sg_cmd):
        fake_sg = type('FakeShareGroup', (object,), {'id': sg_cmd.split()[-1]})
        shell_v2._find_share_group.return_value = fake_sg

        self.run_command('delete 1234 %s' % sg_cmd)

        self.assert_called('DELETE', '/shares/1234?share_group_id=sg1313')
        self.assertTrue(shell_v2._find_share_group.called)

    def test_delete_not_found(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'delete fake-not-found'
        )

    def test_list_snapshots(self):
        self.run_command('snapshot-list')
        self.assert_called('GET', '/snapshots/detail')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_snapshot_list_select_column(self):
        self.run_command('snapshot-list --columns id,name')
        self.assert_called('GET', '/snapshots/detail')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['Id', 'Name'], sortby_index=None)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_list_snapshots_all_tenants_only_key(self):
        self.run_command('snapshot-list --all-tenants')
        self.assert_called('GET', '/snapshots/detail?all_tenants=1')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            ['ID', 'Share ID', 'Status', 'Name', 'Share Size', 'Project ID'],
            sortby_index=None)

    def test_list_snapshots_all_tenants_key_and_value_1(self):
        for separator in self.separators:
            self.run_command('snapshot-list --all-tenants' + separator + '1')
            self.assert_called(
                'GET', '/snapshots/detail?all_tenants=1')

    def test_list_snapshots_all_tenants_key_and_value_0(self):
        for separator in self.separators:
            self.run_command('snapshot-list --all-tenants' + separator + '0')
            self.assert_called('GET', '/snapshots/detail')

    def test_list_snapshots_filter_by_name(self):
        for separator in self.separators:
            self.run_command('snapshot-list --name' + separator + '1234')
            self.assert_called(
                'GET', '/snapshots/detail?name=1234')

    def test_list_snapshots_filter_by_status(self):
        for separator in self.separators:
            self.run_command('snapshot-list --status' + separator + '1234')
            self.assert_called(
                'GET', '/snapshots/detail?status=1234')

    def test_list_snapshots_filter_by_share_id(self):
        aliases = ['--share_id', '--share-id']
        for alias in aliases:
            for separator in self.separators:
                self.run_command('snapshot-list ' + alias + separator + '1234')
                self.assert_called(
                    'GET', '/snapshots/detail?share_id=1234')

    def test_list_snapshots_only_used(self):
        for separator in self.separators:
            self.run_command('snapshot-list --usage' + separator + 'used')
            self.assert_called('GET', '/snapshots/detail?usage=used')

    def test_list_snapshots_only_unused(self):
        for separator in self.separators:
            self.run_command('snapshot-list --usage' + separator + 'unused')
            self.assert_called('GET', '/snapshots/detail?usage=unused')

    def test_list_snapshots_any(self):
        for separator in self.separators:
            self.run_command('snapshot-list --usage' + separator + 'any')
            self.assert_called('GET', '/snapshots/detail?usage=any')

    def test_list_snapshots_with_limit(self):
        for separator in self.separators:
            self.run_command('snapshot-list --limit' + separator + '50')
            self.assert_called(
                'GET', '/snapshots/detail?limit=50')

    def test_list_snapshots_with_offset(self):
        for separator in self.separators:
            self.run_command('snapshot-list --offset' + separator + '50')
            self.assert_called(
                'GET', '/snapshots/detail?offset=50')

    def test_list_snapshots_filter_by_inexact_name(self):
        for separator in self.separators:
            self.run_command('snapshot-list --name~' + separator +
                             'fake_name')
            self.assert_called(
                'GET',
                '/snapshots/detail?name~=fake_name')

    def test_list_snapshots_filter_by_inexact_description(self):
        for separator in self.separators:
            self.run_command('snapshot-list --description~' + separator +
                             'fake_description')
            self.assert_called(
                'GET',
                '/snapshots/detail?description~=fake_description')

    def test_list_snapshots_filter_by_inexact_unicode_name(self):
        for separator in self.separators:
            self.run_command('snapshot-list --name~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/snapshots/detail?name~=%D1%84%D1%84%D1%84')

    def test_list_snapshots_filter_by_inexact_unicode_description(self):
        for separator in self.separators:
            self.run_command('snapshot-list --description~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/snapshots/detail?description~=%D1%84%D1%84%D1%84')

    def test_list_snapshots_with_sort_dir_verify_keys(self):
        aliases = ['--sort_dir', '--sort-dir']
        for alias in aliases:
            for key in constants.SORT_DIR_VALUES:
                for separator in self.separators:
                    self.run_command(
                        'snapshot-list ' + alias + separator + key)
                    self.assert_called(
                        'GET',
                        '/snapshots/detail?sort_dir=' + key)

    def test_list_snapshots_with_fake_sort_dir(self):
        self.assertRaises(
            ValueError,
            self.run_command,
            'snapshot-list --sort-dir fake_sort_dir',
        )

    def test_list_snapshots_with_sort_key_verify_keys(self):
        aliases = ['--sort_key', '--sort-key']
        for alias in aliases:
            for key in constants.SNAPSHOT_SORT_KEY_VALUES:
                for separator in self.separators:
                    self.run_command(
                        'snapshot-list ' + alias + separator + key)
                    self.assert_called(
                        'GET',
                        '/snapshots/detail?sort_key=' + key)

    def test_list_snapshots_with_fake_sort_key(self):
        self.assertRaises(
            ValueError,
            self.run_command,
            'snapshot-list --sort-key fake_sort_key',
        )

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_extra_specs_list(self):
        self.run_command('extra-specs-list')

        self.assert_called('GET', '/types?is_public=all')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, ['ID', 'Name', 'all_extra_specs'], mock.ANY)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_extra_specs_list_select_column(self):
        self.run_command('extra-specs-list --columns id,name')

        self.assert_called('GET', '/types?is_public=all')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, ['id', 'name'], mock.ANY)

    @ddt.data('fake', 'FFFalse', 'trueee')
    def test_type_create_invalid_dhss_value(self, value):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test ' + value,
        )

    @ddt.data('True', 'False')
    def test_type_create_duplicate_dhss(self, value):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test ' + value +
            ' --extra-specs driver_handles_share_servers=' + value,
        )

    @ddt.data(*itertools.product(
        ['snapshot_support', 'create_share_from_snapshot_support'],
        ['True', 'False'])
    )
    @ddt.unpack
    def test_type_create_duplicate_switch_and_extra_spec(self, key, value):

        cmd = ('type-create test True --%(key)s %(value)s --extra-specs '
               '%(key)s=%(value)s' % {'key': key, 'value': value})

        self.assertRaises(exceptions.CommandError, self.run_command, cmd)

    def test_type_create_duplicate_extra_spec_key(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test True --extra-specs'
            ' a=foo1 a=foo2',
        )

    @ddt.unpack
    @ddt.data({'expected_bool': True, 'text': 'true'},
              {'expected_bool': True, 'text': '1'},
              {'expected_bool': False, 'text': 'false'},
              {'expected_bool': False, 'text': '0'})
    def test_type_create(self, expected_bool, text):
        expected = {
            "share_type": {
                "name": "test",
                "share_type_access:is_public": True,
                "extra_specs": {
                    "driver_handles_share_servers": expected_bool,
                }
            }
        }

        self.run_command('type-create test ' + text)

        self.assert_called('POST', '/types', body=expected)

    def test_type_create_with_description(self):
        expected = {
            "share_type": {
                "name": "test",
                "description": "test_description",
                "share_type_access:is_public": True,
                "extra_specs": {
                    "driver_handles_share_servers": False,
                }
            }
        }
        self.run_command('type-create test false '
                         '--description test_description', version='2.41')

        self.assert_called('POST', '/types', body=expected)

    @ddt.data('2.26', '2.40')
    def test_type_create_invalid_description_version(self, version):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test false --description test_description',
            version=version
        )

    @ddt.unpack
    @ddt.data(
        *([{'expected_bool': True, 'text': v}
           for v in ('true', 'True', '1', 'TRUE', 'tRuE')] +
          [{'expected_bool': False, 'text': v}
           for v in ('false', 'False', '0', 'FALSE', 'fAlSe')])
    )
    def test_type_create_with_snapshot_support(self, expected_bool, text):
        expected = {
            "share_type": {
                "name": "test",
                "share_type_access:is_public": True,
                "extra_specs": {
                    "snapshot_support": expected_bool,
                    "driver_handles_share_servers": False,
                }
            }
        }
        self.run_command('type-create test false --snapshot-support ' + text)

        self.assert_called('POST', '/types', body=expected)

    @ddt.unpack
    @ddt.data({'expected_bool': True,
               'snapshot_text': 'true',
               'replication_type': 'readable'},
              {'expected_bool': False,
               'snapshot_text': 'false',
               'replication_type': 'writable'})
    def test_create_with_extra_specs(self, expected_bool, snapshot_text,
                                     replication_type):
        expected = {
            "share_type": {
                "name": "test",
                "share_type_access:is_public": True,
                "extra_specs": {
                    "driver_handles_share_servers": False,
                    "snapshot_support": expected_bool,
                    "replication_type": replication_type,
                }
            }
        }

        self.run_command('type-create test false --extra-specs'
                         ' snapshot_support=' + snapshot_text +
                         ' replication_type=' + replication_type)

        self.assert_called('POST', '/types', body=expected)

    @ddt.unpack
    @ddt.data(
        *([{'expected_bool': True, 'text': v}
           for v in ('true', 'True', '1', 'TRUE', 'tRuE')] +
          [{'expected_bool': False, 'text': v}
           for v in ('false', 'False', '0', 'FALSE', 'fAlSe')])
    )
    def test_type_create_with_create_share_from_snapshot_support(
            self, expected_bool, text):
        expected = {
            "share_type": {
                "name": "test",
                "share_type_access:is_public": True,
                "extra_specs": {
                    "driver_handles_share_servers": False,
                    "snapshot_support": True,
                    "create_share_from_snapshot_support": expected_bool,
                }
            }
        }

        self.run_command('type-create test false --snapshot-support true '
                         '--create-share-from-snapshot-support ' + text)

        self.assert_called('POST', '/types', body=expected)

    @ddt.data('snapshot_support', 'create_share_from_snapshot_support')
    def test_type_create_invalid_switch_value(self, value):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test false --%s fake' % value,
        )

    @ddt.data('snapshot_support', 'create_share_from_snapshot_support')
    def test_type_create_invalid_extra_spec_value(self, value):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test false --extra-specs %s=fake' % value,
        )

    @ddt.unpack
    @ddt.data(
        *([{'expected_bool': True, 'text': v}
           for v in ('true', 'True', '1', 'TRUE', 'tRuE')] +
          [{'expected_bool': False, 'text': v}
           for v in ('false', 'False', '0', 'FALSE', 'fAlSe')])
    )
    def test_type_create_with_revert_to_snapshot_support(
            self, expected_bool, text):
        expected = {
            "share_type": {
                "name": "test",
                "share_type_access:is_public": True,
                "extra_specs": {
                    "driver_handles_share_servers": False,
                    "snapshot_support": True,
                    "revert_to_snapshot_support": expected_bool,
                }
            }
        }

        self.run_command('type-create test false --snapshot-support true '
                         '--revert-to-snapshot-support ' + text)

        self.assert_called('POST', '/types', body=expected)

    @ddt.data('fake', 'FFFalse', 'trueee')
    def test_type_create_invalid_revert_to_snapshot_support_value(self, value):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test false --revert-to-snapshot-support ' + value,
        )

    @ddt.unpack
    @ddt.data(
        *([{'expected_bool': True, 'text': v}
           for v in ('true', 'True', '1', 'TRUE', 'tRuE')] +
          [{'expected_bool': False, 'text': v}
           for v in ('false', 'False', '0', 'FALSE', 'fAlSe')])
    )
    def test_type_create_with_mount_snapshot_support(
            self, expected_bool, text):
        expected = {
            "share_type": {
                "name": "test",
                "share_type_access:is_public": True,
                "extra_specs": {
                    "driver_handles_share_servers": False,
                    "snapshot_support": True,
                    "revert_to_snapshot_support": False,
                    "mount_snapshot_support": expected_bool,
                }
            }
        }

        self.run_command('type-create test false --snapshot-support true '
                         '--revert-to-snapshot-support false '
                         '--mount-snapshot-support ' + text)

        self.assert_called('POST', '/types', body=expected)

    @ddt.data('fake', 'FFFalse', 'trueee')
    def test_type_create_invalid_mount_snapshot_support_value(self, value):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'type-create test false --mount-snapshot-support ' + value,
        )

    @ddt.data('--is-public', '--is_public')
    def test_update(self, alias):
        # basic rename with positional arguments
        self.run_command('update 1234 --name new-name')
        expected = {'share': {'display_name': 'new-name'}}
        self.assert_called('PUT', '/shares/1234', body=expected)
        # change description only
        self.run_command('update 1234 --description=new-description')
        expected = {'share': {'display_description': 'new-description'}}
        self.assert_called('PUT', '/shares/1234', body=expected)
        # update is_public attr
        valid_is_public_values = strutils.TRUE_STRINGS + strutils.FALSE_STRINGS
        for is_public in valid_is_public_values:
            self.run_command('update 1234 %(alias)s %(value)s' % {
                'alias': alias,
                'value': is_public})
            expected = {
                'share': {
                    'is_public': strutils.bool_from_string(is_public,
                                                           strict=True),
                },
            }
            self.assert_called('PUT', '/shares/1234', body=expected)
        for invalid_val in ['truebar', 'bartrue']:
            self.assertRaises(ValueError, self.run_command,
                              'update 1234 %(alias)s %(value)s' % {
                                  'alias': alias,
                                  'value': invalid_val})
        # update all attributes
        self.run_command('update 1234 --name new-name '
                         '--description=new-description '
                         '%s True' % alias)
        expected = {'share': {
            'display_name': 'new-name',
            'display_description': 'new-description',
            'is_public': True,
        }}
        self.assert_called('PUT', '/shares/1234', body=expected)
        self.assertRaises(exceptions.CommandError,
                          self.run_command, 'update 1234')

    def test_rename_snapshot(self):
        # basic rename with positional arguments
        self.run_command('snapshot-rename 1234 new-name')
        expected = {'snapshot': {'display_name': 'new-name'}}
        self.assert_called('PUT', '/snapshots/1234', body=expected)
        # change description only
        self.run_command('snapshot-rename 1234 '
                         '--description=new-description')
        expected = {'snapshot': {'display_description': 'new-description'}}

        self.assert_called('PUT', '/snapshots/1234', body=expected)
        # snapshot-rename and change description
        self.run_command('snapshot-rename 1234 new-name '
                         '--description=new-description')
        expected = {'snapshot': {
            'display_name': 'new-name',
            'display_description': 'new-description',
        }}
        self.assert_called('PUT', '/snapshots/1234', body=expected)
        # noop, the only all will be the lookup
        self.assertRaises(exceptions.CommandError,
                          self.run_command, 'snapshot-rename 1234')

    def test_set_metadata_set(self):
        self.run_command('metadata 1234 set key1=val1 key2=val2')
        self.assert_called('POST', '/shares/1234/metadata',
                           {'metadata': {'key1': 'val1', 'key2': 'val2'}})

    def test_set_metadata_delete_dict(self):
        self.run_command('metadata 1234 unset key1=val1 key2=val2')
        self.assert_called('DELETE', '/shares/1234/metadata/key1')
        self.assert_called('DELETE', '/shares/1234/metadata/key2', pos=-2)

    def test_set_metadata_delete_keys(self):
        self.run_command('metadata 1234 unset key1 key2')
        self.assert_called('DELETE', '/shares/1234/metadata/key1')
        self.assert_called('DELETE', '/shares/1234/metadata/key2', pos=-2)

    def test_share_metadata_update_all(self):
        self.run_command('metadata-update-all 1234 key1=val1 key2=val2')
        self.assert_called('PUT', '/shares/1234/metadata',
                           {'metadata': {'key1': 'val1', 'key2': 'val2'}})

    def test_extract_metadata(self):
        # mimic the result of argparse's parse_args() method
        class Arguments(object):
            def __init__(self, metadata=None):
                if metadata is None:
                    metadata = []
                self.metadata = metadata

        inputs = [
            ([], {}),
            (["key=value"], {"key": "value"}),
            (["key"], {"key": None}),
            (["k1=v1", "k2=v2"], {"k1": "v1", "k2": "v2"}),
            (["k1=v1", "k2"], {"k1": "v1", "k2": None}),
            (["k1", "k2=v2"], {"k1": None, "k2": "v2"})
        ]

        for input in inputs:
            args = Arguments(metadata=input[0])
            self.assertEqual(shell_v2._extract_metadata(args), input[1])

    def test_extend(self):
        self.run_command('extend 1234 77')
        expected = {'extend': {'new_size': 77}}
        self.assert_called('POST', '/shares/1234/action', body=expected)

    def test_reset_state(self):
        self.run_command('reset-state 1234')
        expected = {'reset_status': {'status': 'available'}}
        self.assert_called('POST', '/shares/1234/action', body=expected)

    def test_shrink(self):
        self.run_command('shrink 1234 77')
        expected = {'shrink': {'new_size': 77}}
        self.assert_called('POST', '/shares/1234/action', body=expected)

    def test_reset_state_with_flag(self):
        self.run_command('reset-state --state error 1234')
        expected = {'reset_status': {'status': 'error'}}
        self.assert_called('POST', '/shares/1234/action', body=expected)

    def test_snapshot_reset_state(self):
        self.run_command('snapshot-reset-state 1234')
        expected = {'reset_status': {'status': 'available'}}
        self.assert_called('POST', '/snapshots/1234/action', body=expected)

    def test_snapshot_reset_state_with_flag(self):
        self.run_command('snapshot-reset-state --state error 1234')
        expected = {'reset_status': {'status': 'error'}}
        self.assert_called('POST', '/snapshots/1234/action', body=expected)

    @ddt.data(
        {},
        {'--name': 'fake_name'},
        {'--description': 'fake_description'},
        {'--neutron_net_id': 'fake_neutron_net_id'},
        {'--neutron_subnet_id': 'fake_neutron_subnet_id'},
        {'--description': 'fake_description',
         '--name': 'fake_name',
         '--neutron_net_id': 'fake_neutron_net_id',
         '--neutron_subnet_id': 'fake_neutron_subnet_id'})
    def test_share_network_create(self, data):
        cmd = 'share-network-create'
        for k, v in data.items():
            cmd += ' ' + k + ' ' + v
        self.run_command(cmd)

        self.assert_called('POST', '/share-networks')

    @ddt.data(
        {'--name': 'fake_name'},
        {'--description': 'fake_description'},
        {'--neutron_net_id': 'fake_neutron_net_id'},
        {'--neutron_subnet_id': 'fake_neutron_subnet_id'},
        {'--description': 'fake_description',
         '--name': 'fake_name',
         '--neutron_net_id': 'fake_neutron_net_id',
         '--neutron_subnet_id': 'fake_neutron_subnet_id'},
        {'--name': '""'},
        {'--description': '""'},
        {'--neutron_net_id': '""'},
        {'--neutron_subnet_id': '""'},
        {'--description': '""',
         '--name': '""',
         '--neutron_net_id': '""',
         '--neutron_subnet_id': '""',
         },)
    def test_share_network_update(self, data):
        cmd = 'share-network-update 1111'
        expected = dict()
        for k, v in data.items():
            cmd += ' ' + k + ' ' + v
            expected[k[2:]] = v
        expected = dict(share_network=expected)

        self.run_command(cmd)

        self.assert_called('PUT', '/share-networks/1111', body=expected)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list(self):
        self.run_command('share-network-list')
        self.assert_called(
            'GET',
            '/share-networks/detail',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_select_column(self):
        self.run_command('share-network-list --columns id')
        self.assert_called(
            'GET',
            '/share-networks/detail',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['Id'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_all_tenants(self):
        self.run_command('share-network-list --all-tenants')
        self.assert_called(
            'GET',
            '/share-networks/detail?all_tenants=1',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    @mock.patch.object(shell_v2, '_find_security_service', mock.Mock())
    def test_share_network_list_filter_by_security_service(self):
        ss = type('FakeSecurityService', (object,), {'id': 'fake-ss-id'})
        shell_v2._find_security_service.return_value = ss
        for command in ['--security_service', '--security-service']:
            self.run_command('share-network-list %(command)s %(ss_id)s' %
                             {'command': command,
                              'ss_id': ss.id})
            self.assert_called(
                'GET',
                '/share-networks/detail?security_service_id=%s' % ss.id,
            )
            shell_v2._find_security_service.assert_called_with(mock.ANY, ss.id)
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_project_id_aliases(self):
        for command in ['--project-id', '--project_id']:
            self.run_command('share-network-list %s 1234' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?project_id=1234',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_created_before_aliases(self):
        for command in ['--created-before', '--created_before']:
            self.run_command('share-network-list %s 2001-01-01' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?created_before=2001-01-01',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_created_since_aliases(self):
        for command in ['--created-since', '--created_since']:
            self.run_command('share-network-list %s 2001-01-01' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?created_since=2001-01-01',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_neutron_net_id_aliases(self):
        for command in ['--neutron-net-id', '--neutron-net_id',
                        '--neutron_net-id', '--neutron_net_id']:
            self.run_command('share-network-list %s fake-id' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?neutron_net_id=fake-id',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_neutron_subnet_id_aliases(self):
        for command in ['--neutron-subnet-id', '--neutron-subnet_id',
                        '--neutron_subnet-id', '--neutron_subnet_id']:
            self.run_command('share-network-list %s fake-id' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?neutron_subnet_id=fake-id',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_network_type_aliases(self):
        for command in ['--network_type', '--network-type']:
            self.run_command('share-network-list %s local' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?network_type=local',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_segmentation_id_aliases(self):
        for command in ['--segmentation-id', '--segmentation_id']:
            self.run_command('share-network-list %s 1234' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?segmentation_id=1234',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_ip_version_aliases(self):
        for command in ['--ip-version', '--ip_version']:
            self.run_command('share-network-list %s 4' % command)
            self.assert_called(
                'GET',
                '/share-networks/detail?ip_version=4',
            )
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_list_all_filters(self):
        filters = {
            'name': 'fake-name',
            'project-id': '1234',
            'created-since': '2001-01-01',
            'created-before': '2002-02-02',
            'neutron-net-id': 'fake-net',
            'neutron-subnet-id': 'fake-subnet',
            'network-type': 'local',
            'segmentation-id': '5678',
            'cidr': 'fake-cidr',
            'ip-version': '4',
            'offset': 10,
            'limit': 20,
        }
        command_str = 'share-network-list'
        for key, value in filters.items():
            command_str += ' --%(key)s=%(value)s' % {'key': key,
                                                     'value': value}
        self.run_command(command_str)
        query = utils.safe_urlencode(sorted([(k.replace('-', '_'), v) for
                                             (k, v) in filters.items()]))
        self.assert_called(
            'GET',
            '/share-networks/detail?%s' % query,
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name'])

    def test_share_network_list_filter_by_inexact_name(self):
        for separator in self.separators:
            self.run_command('share-network-list --name~' + separator +
                             'fake_name')
            self.assert_called(
                'GET',
                '/share-networks/detail?name~=fake_name')

    def test_share_network_list_filter_by_inexact_description(self):
        for separator in self.separators:
            self.run_command('share-network-list --description~' + separator +
                             'fake_description')
            self.assert_called(
                'GET',
                '/share-networks/detail?description~=fake_description')

    def test_share_network_list_filter_by_inexact_unicode_name(self):
        for separator in self.separators:
            self.run_command('share-network-list --name~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/share-networks/detail?name~=%D1%84%D1%84%D1%84')

    def test_share_network_list_filter_by_inexact_unicode_description(self):
        for separator in self.separators:
            self.run_command('share-network-list --description~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/share-networks/detail?description~=%D1%84%D1%84%D1%84')

    def test_share_network_security_service_add(self):
        self.run_command('share-network-security-service-add fake_share_nw '
                         'fake_security_service')
        self.assert_called(
            'POST',
            '/share-networks/1234/action',
        )

    def test_share_network_security_service_remove(self):
        self.run_command('share-network-security-service-remove fake_share_nw '
                         'fake_security_service')
        self.assert_called(
            'POST',
            '/share-networks/1234/action',
        )

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_network_security_service_list_select_column(self):
        self.run_command('share-network-security-service-list '
                         'fake_share_nw --column id,name')
        self.assert_called(
            'GET',
            '/security-services/detail?share_network_id=1234',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['Id', 'Name'])

    def test_share_network_security_service_list_by_name(self):
        self.run_command('share-network-security-service-list fake_share_nw')
        self.assert_called(
            'GET',
            '/security-services/detail?share_network_id=1234',
        )

    def test_share_network_security_service_list_by_name_not_found(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'share-network-security-service-list inexistent_share_nw',
        )

    def test_share_network_security_service_list_by_name_multiple(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            'share-network-security-service-list duplicated_name',
        )

    def test_share_network_security_service_list_by_id(self):
        self.run_command('share-network-security-service-list 1111')
        self.assert_called(
            'GET',
            '/security-services/detail?share_network_id=1111',
        )

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_server_list_select_column(self):
        self.run_command('share-server-list --columns id,host,status')
        self.assert_called('GET', '/share-servers')
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['Id', 'Host', 'Status'])

    def test_create_share(self):
        # Use only required fields
        self.run_command("create nfs 1")
        self.assert_called("POST", "/shares", body=self.create_share_body)

    def test_create_public_share(self):
        expected = self.create_share_body.copy()
        expected['share']['is_public'] = True
        self.run_command("create --public nfs 1")
        self.assert_called("POST", "/shares", body=expected)

    def test_create_with_share_network(self):
        # Except required fields added share network
        sn = "fake-share-network"
        with mock.patch.object(shell_v2, "_find_share_network",
                               mock.Mock(return_value=sn)):
            self.run_command("create nfs 1 --share-network %s" % sn)
            expected = self.create_share_body.copy()
            expected['share']['share_network_id'] = sn
            self.assert_called("POST", "/shares", body=expected)
            shell_v2._find_share_network.assert_called_once_with(mock.ANY, sn)

    def test_create_with_metadata(self):
        # Except required fields added metadata
        self.run_command("create nfs 1 --metadata key1=value1 key2=value2")
        expected = self.create_share_body.copy()
        expected['share']['metadata'] = {"key1": "value1", "key2": "value2"}
        self.assert_called("POST", "/shares", body=expected)

    def test_allow_access_cert(self):
        self.run_command("access-allow 1234 cert client.example.com")

        expected = {
            "allow_access": {
                "access_type": "cert",
                "access_to": "client.example.com",
            }
        }
        self.assert_called("POST", "/shares/1234/action", body=expected)

    def test_allow_access_cert_error_gt64(self):
        common_name = 'x' * 65
        self.assertRaises(exceptions.CommandError, self.run_command,
                          ("access-allow 1234 cert %s" % common_name))

    def test_allow_access_cert_error_zero(self):
        cmd = mock.Mock()
        cmd.split = mock.Mock(side_effect=lambda: ['access-allow', '1234',
                                                   'cert', ''])

        self.assertRaises(exceptions.CommandError, self.run_command, cmd)

        cmd.split.assert_called_once_with()

    def test_allow_access_cert_error_whitespace(self):
        cmd = mock.Mock()
        cmd.split = mock.Mock(side_effect=lambda: ['access-allow', '1234',
                                                   'cert', ' '])

        self.assertRaises(exceptions.CommandError, self.run_command, cmd)

        cmd.split.assert_called_once_with()

    def test_allow_access_with_access_level(self):
        aliases = ['--access_level', '--access-level']
        expected = {
            "allow_access": {
                "access_type": "ip",
                "access_to": "10.0.0.6",
                "access_level": "ro",
            }
        }

        for alias in aliases:
            for s in self.separators:
                self.run_command(
                    "access-allow " + alias + s + "ro 1111 ip 10.0.0.6")
                self.assert_called("POST", "/shares/1111/action",
                                   body=expected)

    def test_allow_access_with_valid_access_levels(self):
        expected = {
            "allow_access": {
                "access_type": "ip",
                "access_to": "10.0.0.6",
            }
        }

        for level in ['rw', 'ro']:
            expected["allow_access"]['access_level'] = level
            self.run_command(
                "access-allow --access-level " + level + " 1111 ip 10.0.0.6")
            self.assert_called("POST", "/shares/1111/action",
                               body=expected)

    def test_allow_access_with_invalid_access_level(self):
        self.assertRaises(SystemExit, self.run_command,
                          "access-allow --access-level fake 1111 ip 10.0.0.6")

    def test_allow_access_with_metadata(self):
        expected = {
            "allow_access": {
                "access_type": "ip",
                "access_to": "10.0.0.6",
                "metadata": {"key1": "v1", "key2": "v2"},
            }
        }

        self.run_command(
            "access-allow 2222 ip 10.0.0.6 --metadata key1=v1 key2=v2",
            version="2.45")
        self.assert_called("POST", "/shares/2222/action", body=expected)

    def test_set_access_metadata(self):
        expected = {
            "metadata": {
                "key1": "v1",
                "key2": "v2",
            }
        }
        self.run_command(
            "access-metadata 9999 set key1=v1 key2=v2",
            version="2.45")
        self.assert_called("PUT", "/share-access-rules/9999/metadata",
                           body=expected)

    def test_unset_access_metadata(self):
        self.run_command(
            "access-metadata 9999 unset key1",
            version="2.45")
        self.assert_called("DELETE", "/share-access-rules/9999/metadata/key1")

    @ddt.data("1.0", "2.0", "2.44")
    def test_allow_access_with_metadata_not_support_version(self, version):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command,
            "access-allow 2222 ip 10.0.0.6 --metadata key1=v1",
            version=version,
        )

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    @ddt.data(*set(["2.44", "2.45", api_versions.MAX_VERSION]))
    def test_access_list(self, version):
        self.run_command("access-list 1111", version=version)
        version = api_versions.APIVersion(version)
        cliutils.print_list.assert_called_with(
            mock.ANY,
            ['id', 'access_type', 'access_to', 'access_level', 'state',
             'access_key', 'created_at', 'updated_at'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    @ddt.data(*set(["2.44", "2.45", api_versions.MAX_VERSION]))
    def test_access_list_select_column(self, version):
        self.run_command("access-list 1111 --columns id,access_type",
                         version=version)
        cliutils.print_list.assert_called_with(
            mock.ANY,
            ['Id', 'Access_Type'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_snapshot_access_list(self):
        self.run_command("snapshot-access-list 1234")

        self.assert_called('GET', '/snapshots/1234/access-list')
        cliutils.print_list.assert_called_with(
            mock.ANY, ['id', 'access_type', 'access_to', 'state'])

    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_snapshot_access_allow(self):
        self.run_command("snapshot-access-allow 1234 ip 1.1.1.1")

        self.assert_called('POST', '/snapshots/1234/action')
        cliutils.print_dict.assert_called_with(
            {'access_type': 'ip', 'access_to': '1.1.1.1'})

    def test_snapshot_access_deny(self):
        self.run_command("snapshot-access-deny 1234 fake_id")

        self.assert_called('POST', '/snapshots/1234/action')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_snapshot_export_location_list(self):
        self.run_command('snapshot-export-location-list 1234')

        self.assert_called(
            'GET', '/snapshots/1234/export-locations')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_snapshot_instance_export_location_list(self):
        self.run_command('snapshot-instance-export-location-list 1234')

        self.assert_called(
            'GET', '/snapshot-instances/1234/export-locations')

    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_snapshot_instance_export_location_show(self):
        self.run_command('snapshot-instance-export-location-show 1234 '
                         'fake_el_id')

        self.assert_called(
            'GET', '/snapshot-instances/1234/export-locations/fake_el_id')
        cliutils.print_dict.assert_called_once_with(
            {'path': '/fake_path', 'id': 'fake_id'})

    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_snapshot_export_location_show(self):
        self.run_command('snapshot-export-location-show 1234 fake_el_id')

        self.assert_called('GET',
                           '/snapshots/1234/export-locations/fake_el_id')
        cliutils.print_dict.assert_called_once_with(
            {'path': '/fake_path', 'id': 'fake_id'})

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_security_service_list(self):
        self.run_command('security-service-list')
        self.assert_called(
            'GET',
            '/security-services',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name', 'status', 'type'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_security_service_list_select_column(self):
        self.run_command('security-service-list --columns name,type')
        self.assert_called(
            'GET',
            '/security-services',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['Name', 'Type'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    @mock.patch.object(shell_v2, '_find_share_network', mock.Mock())
    def test_security_service_list_filter_share_network(self):
        class FakeShareNetwork(object):
            id = 'fake-sn-id'
        sn = FakeShareNetwork()
        shell_v2._find_share_network.return_value = sn
        for command in ['--share-network', '--share_network']:
            self.run_command('security-service-list %(command)s %(sn_id)s' %
                             {'command': command,
                              'sn_id': sn.id})
            self.assert_called(
                'GET',
                '/security-services?share_network_id=%s' % sn.id,
            )
            shell_v2._find_share_network.assert_called_with(mock.ANY, sn.id)
            cliutils.print_list.assert_called_with(
                mock.ANY,
                fields=['id', 'name', 'status', 'type'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_security_service_list_detailed(self):
        self.run_command('security-service-list --detailed')
        self.assert_called(
            'GET',
            '/security-services/detail',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name', 'status', 'type', 'share_networks'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_security_service_list_all_tenants(self):
        self.run_command('security-service-list --all-tenants')
        self.assert_called(
            'GET',
            '/security-services?all_tenants=1',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name', 'status', 'type'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_security_service_list_all_filters(self):
        filters = {
            'status': 'new',
            'name': 'fake-name',
            'type': 'ldap',
            'user': 'fake-user',
            'dns-ip': '1.1.1.1',
            'ou': 'fake-ou',
            'server': 'fake-server',
            'domain': 'fake-domain',
            'offset': 10,
            'limit': 20,
        }
        command_str = 'security-service-list'
        for key, value in filters.items():
            command_str += ' --%(key)s=%(value)s' % {'key': key,
                                                     'value': value}
        self.run_command(command_str)
        self.assert_called(
            'GET',
            '/security-services?dns_ip=1.1.1.1&domain=fake-domain&limit=20'
            '&name=fake-name&offset=10&ou=fake-ou&server=fake-server'
            '&status=new&type=ldap&user=fake-user',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name', 'status', 'type'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_security_service_list_filter_by_dns_ip_alias(self):
        self.run_command('security-service-list --dns_ip 1.1.1.1')
        self.assert_called(
            'GET',
            '/security-services?dns_ip=1.1.1.1',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name', 'status', 'type'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_security_service_list_filter_by_ou_alias(self):
        self.run_command('security-service-list --ou fake-ou')
        self.assert_called(
            'GET',
            '/security-services?ou=fake-ou',
        )
        cliutils.print_list.assert_called_once_with(
            mock.ANY,
            fields=['id', 'name', 'status', 'type'])

    @ddt.data(
        {'--name': 'fake_name'},
        {'--description': 'fake_description'},
        {'--dns-ip': 'fake_dns_ip'},
        {'--ou': 'fake_ou'},
        {'--domain': 'fake_domain'},
        {'--server': 'fake_server'},
        {'--user': 'fake_user'},
        {'--password': 'fake_password'},
        {'--name': 'fake_name',
         '--description': 'fake_description',
         '--dns-ip': 'fake_dns_ip',
         '--ou': 'fake_ou',
         '--domain': 'fake_domain',
         '--server': 'fake_server',
         '--user': 'fake_user',
         '--password': 'fake_password'},
        {'--name': '""'},
        {'--description': '""'},
        {'--dns-ip': '""'},
        {'--ou': '""'},
        {'--domain': '""'},
        {'--server': '""'},
        {'--user': '""'},
        {'--password': '""'},
        {'--name': '""',
         '--description': '""',
         '--dns-ip': '""',
         '--ou': '""',
         '--domain': '""',
         '--server': '""',
         '--user': '""',
         '--password': '""'},)
    def test_security_service_update(self, data):
        cmd = 'security-service-update 1111'
        expected = dict()
        for k, v in data.items():
            cmd += ' ' + k + ' ' + v
            expected[k[2:].replace('-', '_')] = v
        expected = dict(security_service=expected)

        self.run_command(cmd)

        self.assert_called('PUT', '/security-services/1111', body=expected)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_pool_list(self):
        self.run_command('pool-list')
        self.assert_called(
            'GET',
            '/scheduler-stats/pools?backend=.%2A&host=.%2A&pool=.%2A',
        )
        cliutils.print_list.assert_called_with(
            mock.ANY,
            fields=["Name", "Host", "Backend", "Pool"])

    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_quota_show(self):
        self.run_command('quota-show --tenant 1234')
        self.assert_called(
            'GET',
            '/quota-sets/1234',
        )
        cliutils.print_dict.assert_called_once_with(mock.ANY)

    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_quota_show_with_detail(self):
        self.run_command('quota-show --tenant 1234 --detail')
        self.assert_called(
            'GET',
            '/quota-sets/1234/detail',
        )
        cliutils.print_dict.assert_called_once_with(mock.ANY)

    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_quota_show_with_user_id(self):
        self.run_command('quota-show --tenant 1234 --user 1111')
        self.assert_called(
            'GET',
            '/quota-sets/1234?user_id=1111',
        )
        cliutils.print_dict.assert_called_once_with(mock.ANY)

    @ddt.data('1111', '0')
    @mock.patch('manilaclient.common.cliutils.print_dict')
    def test_quota_show_with_share_type(self, share_type_id, mock_print_dict):
        self.run_command(
            'quota-show --tenant 1234 --share_type %s' % share_type_id)

        self.assert_called(
            'GET',
            '/quota-sets/1234?share_type=%s' % share_type_id,
        )
        mock_print_dict.assert_called_once_with(mock.ANY)

    @ddt.data(
        ('--shares 13', {'shares': 13}),
        ('--gigabytes 14', {'gigabytes': 14}),
        ('--snapshots 15', {'snapshots': 15}),
        ('--snapshot-gigabytes 13', {'snapshot_gigabytes': 13}),
        ('--share-networks 13', {'share_networks': 13}),
        ('--share-groups 13', {'share_groups': 13}),
        ('--share-groups 0', {'share_groups': 0}),
        ('--share-group-snapshots 13', {'share_group_snapshots': 13}),
        ('--share-group-snapshots 0', {'share_group_snapshots': 0}),
    )
    @ddt.unpack
    def test_quota_update(self, cmd, expected_body):
        self.run_command('quota-update 1234 %s' % cmd)

        expected = {'quota_set': dict(expected_body, tenant_id='1234')}
        self.assert_called('PUT', '/quota-sets/1234', body=expected)

    @ddt.data(
        "quota-update 1234 --share-groups 13 --share-type foo",
        "quota-update 1234 --share-group-snapshots 14 --share-type bar",
        ("quota-update 1234 --share-groups 13 --share-type foo "
         "--share-group-snapshots 14"),
        "--os-share-api-version 2.39 quota-update 1234 --share-groups 13",
        ("--os-share-api-version 2.39 quota-update 1234 "
         "--share-group-snapshots 13"),
        ("--os-share-api-version 2.38 quota-update 1234 --shares 5 "
         "--share-type foo"),
    )
    def test_quota_update_with_wrong_combinations(self, cmd):
        self.assertRaises(exceptions.CommandError, self.run_command, cmd)

    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_pool_list_with_detail(self):
        self.run_command('pool-list --detail')
        self.assert_called(
            'GET',
            '/scheduler-stats/pools/detail?backend=.%2A&host=.%2A&pool=.%2A',
        )
        cliutils.print_dict.assert_called_with(
            {'name': 'host1@backend1#pool2', 'qos': False})

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_pool_list_select_column(self):
        self.run_command('pool-list --columns name,host')
        self.assert_called(
            'GET',
            '/scheduler-stats/pools/detail?backend=.%2A&host=.%2A&pool=.%2A',
        )
        cliutils.print_list.assert_called_with(
            mock.ANY,
            fields=["Name", "Host"])

    @ddt.data(({"key1": "value1",
               "key2": "value2"},
               {"key1": "value1",
               "key2": "value2"}),
              ({"key1": {"key11": "value11", "key12": "value12"},
                "key2": {"key21": "value21"}},
               {"key1": "key11 = value11\nkey12 = value12",
                "key2": "key21 = value21"}),
              ({}, {}))
    @ddt.unpack
    @mock.patch.object(cliutils, 'print_dict', mock.Mock())
    def test_quota_set_pretty_show(self, value, expected):
        fake_quota_set = fakes.FakeQuotaSet(value)

        shell_v2._quota_set_pretty_show(fake_quota_set)
        cliutils.print_dict.assert_called_with(expected)

    @ddt.data('--share-type test_type', '--share_type test_type',
              '--share-type-id 0123456789', '--share_type_id 0123456789')
    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_pool_list_with_filters(self, param):
        cmd = ('pool-list --host host1 --backend backend1 --pool pool1' + ' ' +
               param)
        self.run_command(cmd)
        self.assert_called(
            'GET',
            '/scheduler-stats/pools?backend=backend1&host=host1&'
            'pool=pool1&share_type=%s' % param.split()[-1],
        )
        cliutils.print_list.assert_called_with(
            mock.ANY,
            fields=["Name", "Host", "Backend", "Pool"])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_api_version(self):
        self.run_command('api-version')
        self.assert_called('GET', '')
        cliutils.print_list.assert_called_with(
            mock.ANY,
            ['ID', 'Status', 'Version', 'Min_version'],
            field_labels=['ID', 'Status', 'Version', 'Minimum Version'])

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_group_list(self):
        self.run_command('share-group-list')

        self.assert_called('GET', '/share-groups/detail')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=('ID', 'Name', 'Status', 'Description'),
            sortby_index=None)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_group_list_select_column(self):
        self.run_command('share-group-list --columns id,name,description')

        self.assert_called('GET', '/share-groups/detail')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=['Id', 'Name', 'Description'], sortby_index=None)

    def test_share_group_list_filter_by_inexact_name(self):
        for separator in self.separators:
            self.run_command('share-group-list --name~' + separator +
                             'fake_name')
            self.assert_called(
                'GET',
                '/share-groups/detail?name~=fake_name')

    def test_share_group_list_filter_by_inexact_description(self):
        for separator in self.separators:
            self.run_command('share-group-list --description~' + separator +
                             'fake_description')
            self.assert_called(
                'GET',
                '/share-groups/detail?description~=fake_description')

    def test_share_group_list_filter_by_inexact_unicode_name(self):
        for separator in self.separators:
            self.run_command('share-group-list --name~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/share-groups/detail?name~=%D1%84%D1%84%D1%84')

    def test_share_group_list_filter_by_inexact_unicode_description(self):
        for separator in self.separators:
            self.run_command('share-group-list --description~' + separator +
                             u'ффф')
            self.assert_called(
                'GET',
                '/share-groups/detail?description~=%D1%84%D1%84%D1%84')

    def test_share_group_show(self):
        self.run_command('share-group-show 1234')

        self.assert_called('GET', '/share-groups/1234')

    def test_share_group_create(self):
        fake_share_type_1 = type('FakeShareType1', (object,), {'id': '1234'})
        fake_share_type_2 = type('FakeShareType2', (object,), {'id': '5678'})
        self.mock_object(
            shell_v2, '_find_share_type',
            mock.Mock(side_effect=[fake_share_type_1, fake_share_type_2]))
        fake_share_group_type = type(
            'FakeShareGroupType', (object,), {'id': '2345'})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))
        fake_share_network = type(
            'FakeShareNetwork', (object,), {'id': '3456'})
        self.mock_object(
            shell_v2, '_find_share_network',
            mock.Mock(return_value=fake_share_network))

        self.run_command(
            'share-group-create --name fake_sg '
            '--description my_group --share-types 1234,5678 '
            '--share-group-type fake_sg_type '
            '--share-network fake_share_network '
            '--availability-zone fake_az')

        expected = {
            'share_group': {
                'name': 'fake_sg',
                'description': 'my_group',
                'availability_zone': 'fake_az',
                'share_group_type_id': '2345',
                'share_network_id': '3456',
                'share_types': ['1234', '5678'],
            },
        }
        self.assert_called('POST', '/share-groups', body=expected)

    @ddt.data(
        '--name fake_name --availability-zone fake_az',
        '--description my_fake_description --name fake_name',
        '--availability-zone fake_az',
    )
    def test_share_group_create_no_share_types(self, data):
        cmd = 'share-group-create' + ' ' + data

        self.run_command(cmd)

        self.assert_called('POST', '/share-groups')

    def test_share_group_create_invalid_args(self):
        fake_share_type_1 = type('FakeShareType1', (object,), {'id': '1234'})
        fake_share_type_2 = type('FakeShareType2', (object,), {'id': '5678'})
        self.mock_object(
            shell_v2, '_find_share_type',
            mock.Mock(side_effect=[fake_share_type_1, fake_share_type_2]))
        fake_share_group_type = type(
            'FakeShareGroupType', (object,), {'id': '2345'})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))
        fake_share_group_snapshot = type(
            'FakeShareGroupSnapshot', (object,), {'id': '3456'})
        self.mock_object(
            shell_v2, '_find_share_group_snapshot',
            mock.Mock(return_value=fake_share_group_snapshot))

        self.assertRaises(
            ValueError,
            self.run_command,
            'share-group-create --name fake_sg '
            '--description my_group --share-types 1234,5678 '
            '--share-group-type fake_sg_type '
            '--source-share-group-snapshot fake_share_group_snapshot '
            '--availability-zone fake_az')

    @ddt.data(
        ('--name new-name', {'name': 'new-name'}),
        ('--description new-description', {'description': 'new-description'}),
        ('--name new-name --description new-description',
         {'name': 'new-name', 'description': 'new-description'}),
    )
    @ddt.unpack
    def test_share_group_update(self, cmd, expected_body):
        self.run_command('share-group-update 1234 %s' % cmd)

        expected = {'share_group': expected_body}
        self.assert_called('PUT', '/share-groups/1234', body=expected)

    def test_try_update_share_group_without_data(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command, 'share-group-update 1234')

    @mock.patch.object(shell_v2, '_find_share_group', mock.Mock())
    def test_share_group_delete(self):
        fake_group = type('FakeShareGroup', (object,), {'id': '1234'})
        shell_v2._find_share_group.return_value = fake_group

        self.run_command('share-group-delete fake-sg')

        self.assert_called('DELETE', '/share-groups/1234')

    @mock.patch.object(shell_v2, '_find_share_group', mock.Mock())
    def test_share_group_delete_force(self):
        fake_group = type('FakeShareGroup', (object,), {'id': '1234'})
        shell_v2._find_share_group.return_value = fake_group

        self.run_command('share-group-delete --force fake-group')

        self.assert_called(
            'POST', '/share-groups/1234/action', {'force_delete': None})

    @mock.patch.object(shell_v2, '_find_share_group', mock.Mock())
    def test_share_group_delete_all_fail(self):
        shell_v2._find_share_group.side_effect = Exception

        self.assertRaises(
            exceptions.CommandError,
            self.run_command, 'share-group-delete fake-group')

    @mock.patch.object(shell_v2, '_find_share_group', mock.Mock())
    def test_share_group_reset_state_with_flag(self):
        fake_group = type('FakeShareGroup', (object,), {'id': '1234'})
        shell_v2._find_share_group.return_value = fake_group

        self.run_command('share-group-reset-state --state error 1234')

        self.assert_called(
            'POST', '/share-groups/1234/action',
            {'reset_status': {'status': 'error'}})

    @ddt.data(
        'fake-sg-id',
        '--name fake_name fake-sg-id',
        '--description my_fake_description --name fake_name  fake-sg-id',
    )
    @mock.patch.object(shell_v2, '_find_share_group', mock.Mock())
    def test_share_group_snapshot_create(self, data):
        fake_sg = type('FakeShareGroup', (object,), {'id': '1234'})
        shell_v2._find_share_group.return_value = fake_sg

        self.run_command('share-group-snapshot-create ' + data)

        shell_v2._find_share_group.assert_called_with(mock.ANY, 'fake-sg-id')
        self.assert_called('POST', '/share-group-snapshots')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_group_snapshot_list(self):
        self.run_command('share-group-snapshot-list')

        self.assert_called('GET', '/share-group-snapshots/detail')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=('id', 'name', 'status', 'description'),
            sortby_index=None)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_group_snapshot_list_select_column(self):
        self.run_command('share-group-snapshot-list --columns id,name')

        self.assert_called('GET', '/share-group-snapshots/detail')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=['Id', 'Name'], sortby_index=None)

    def test_share_group_snapshot_list_all_tenants_only_key(self):
        self.run_command('share-group-snapshot-list --all-tenants')

        self.assert_called(
            'GET', '/share-group-snapshots/detail?all_tenants=1')

    def test_share_group_snapshot_list_all_tenants_key_and_value_1(self):
        for separator in self.separators:
            self.run_command(
                'share-group-snapshot-list --all-tenants' + separator + '1')

            self.assert_called(
                'GET', '/share-group-snapshots/detail?all_tenants=1')

    def test_share_group_snapshot_list_with_filters(self):
        self.run_command('share-group-snapshot-list --limit 10 --offset 0')

        self.assert_called(
            'GET', '/share-group-snapshots/detail?limit=10&offset=0')

    def test_share_group_snapshot_show(self):
        self.run_command('share-group-snapshot-show 1234')

        self.assert_called('GET', '/share-group-snapshots/1234')

    def test_share_group_snapshot_list_members(self):
        self.run_command('share-group-snapshot-list-members 1234')

        self.assert_called('GET', '/share-group-snapshots/1234')

    def test_share_group_snapshot_list_members_select_column(self):
        self.mock_object(cliutils, 'print_list')

        self.run_command(
            'share-group-snapshot-list-members 1234 --columns id,size')

        self.assert_called('GET', '/share-group-snapshots/1234')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=['Id', 'Size'])

    @mock.patch.object(shell_v2, '_find_share_group_snapshot', mock.Mock())
    def test_share_group_snapshot_reset_state(self):
        fake_sg_snapshot = type(
            'FakeShareGroupSnapshot', (object,), {'id': '1234'})
        shell_v2._find_share_group_snapshot.return_value = fake_sg_snapshot

        self.run_command('share-group-snapshot-reset-state 1234')

        self.assert_called(
            'POST', '/share-group-snapshots/1234/action',
            {'reset_status': {'status': 'available'}})

    @mock.patch.object(shell_v2, '_find_share_group_snapshot', mock.Mock())
    def test_share_group_snapshot_reset_state_with_flag(self):
        fake_sg_snapshot = type('FakeSGSnapshot', (object,), {'id': '1234'})
        shell_v2._find_share_group_snapshot.return_value = fake_sg_snapshot

        self.run_command(
            'share-group-snapshot-reset-state --state creating 1234')

        self.assert_called(
            'POST', '/share-group-snapshots/1234/action',
            {'reset_status': {'status': 'creating'}})

    @ddt.data(
        ('--name new-name', {'name': 'new-name'}),
        ('--description new-description', {'description': 'new-description'}),
        ('--name new-name --description new-description',
         {'name': 'new-name', 'description': 'new-description'}),
    )
    @ddt.unpack
    def test_share_group_snapshot_update(self, cmd, expected_body):
        self.run_command('share-group-snapshot-update 1234 %s' % cmd)

        expected = {'share_group_snapshot': expected_body}
        self.assert_called('PUT', '/share-group-snapshots/1234', body=expected)

    def test_try_update_share_group_snapshot_without_data(self):
        self.assertRaises(
            exceptions.CommandError,
            self.run_command, 'share-group-snapshot-update 1234')

    @mock.patch.object(shell_v2, '_find_share_group_snapshot', mock.Mock())
    def test_share_group_snapshot_delete(self):
        fake_sg_snapshot = type('FakeSGSnapshot', (object,), {'id': '1234'})
        shell_v2._find_share_group_snapshot.return_value = fake_sg_snapshot

        self.run_command('share-group-snapshot-delete fake-group-snapshot')

        self.assert_called('DELETE', '/share-group-snapshots/1234')

    @mock.patch.object(shell_v2, '_find_share_group_snapshot', mock.Mock())
    def test_share_group_snapshot_delete_force(self):
        fake_sg_snapshot = type('FakeSGSnapshot', (object,), {'id': '1234'})
        shell_v2._find_share_group_snapshot.return_value = fake_sg_snapshot

        self.run_command(
            'share-group-snapshot-delete --force fake-sg-snapshot')

        self.assert_called(
            'POST', '/share-group-snapshots/1234/action',
            {'force_delete': None})

    def test_share_group_snapshot_delete_all_fail(self):
        self.mock_object(
            shell_v2, '_find_share_group_snapshot',
            mock.Mock(side_effect=Exception))

        self.assertRaises(
            exceptions.CommandError,
            self.run_command, 'share-group-snapshot-delete fake-sg-snapshot')

    @ddt.data(*itertools.product(
        ('--columns id,is_default', '--columns id,name',
         '--columns is_default', ''),
        {'2.45', '2.46', api_versions.MAX_VERSION}))
    @ddt.unpack
    def test_share_group_type_list(self, command_args, version):
        self.mock_object(shell_v2, '_print_share_group_type_list')
        command = 'share-group-type-list ' + command_args
        columns_requested = command_args.split('--columns ')[-1] or None
        is_default_in_api = (api_versions.APIVersion(version) >=
                             api_versions.APIVersion('2.46'))

        self.run_command(command, version=version)

        if (not is_default_in_api and
                (not columns_requested or 'is_default' in columns_requested)):
            self.assert_called('GET', '/share-group-types/default')
            self.assert_called_anytime('GET', '/share-group-types')
        else:
            self.assert_called('GET', '/share-group-types')

        shell_v2._print_share_group_type_list.assert_called_once_with(
            mock.ANY, default_share_group_type=mock.ANY,
            columns=columns_requested)

    def test_share_group_type_list_select_column(self):
        self.mock_object(shell_v2, '_print_share_group_type_list')

        self.run_command('share-group-type-list --columns id,name')

        self.assert_called('GET', '/share-group-types')
        shell_v2._print_share_group_type_list.assert_called_once_with(
            mock.ANY, default_share_group_type=mock.ANY, columns='id,name')

    def test_share_group_type_list_all(self):
        self.run_command('share-group-type-list --all')

        self.assert_called_anytime('GET', '/share-group-types?is_public=all')

    @ddt.data(('', mock.ANY), (' --columns id,name', 'id,name'))
    @ddt.unpack
    def test_share_group_specs_list(self, args_cmd, expected_columns):
        self.mock_object(shell_v2, '_print_type_and_extra_specs_list')

        self.run_command('share-group-type-specs-list')

        self.assert_called('GET', '/share-group-types?is_public=all')
        shell_v2._print_type_and_extra_specs_list.assert_called_once_with(
            mock.ANY, columns=mock.ANY)

    @ddt.data(True, False)
    def test_share_group_type_create_with_access_and_group_specs(self, public):
        fake_share_type_1 = type('FakeShareType', (object,), {'id': '1234'})
        fake_share_type_2 = type('FakeShareType', (object,), {'id': '5678'})
        self.mock_object(
            shell_v2, '_find_share_type',
            mock.Mock(side_effect=[fake_share_type_1, fake_share_type_2]))
        expected = {
            'share_group_type': {
                'name': 'test-group-type-1',
                'share_types': ['1234', '5678'],
                'group_specs': {'spec1': 'value1'},
                'is_public': public,
            }
        }

        self.run_command(
            'share-group-type-create test-group-type-1 '
            'type1,type2 --is-public %s --group-specs '
            'spec1=value1' % six.text_type(public))

        self.assert_called_anytime('POST', '/share-group-types', body=expected)

    def test_share_group_type_delete(self):
        fake_share_group_type = type(
            'FakeShareGroupType', (object,), {'id': '1234'})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))

        self.run_command('share-group-type-delete test-group-type-1')

        self.assert_called('DELETE', '/share-group-types/1234')

    def test_share_group_type_key_set(self):
        fake_share_group_type = type(
            'FakeShareGroupType', (object,),
            {'id': '1234', 'is_public': False, 'set_keys': mock.Mock(),
             'unset_keys': mock.Mock()})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))

        self.run_command('share-group-type-key fake_sg_type set key1=value1')

        fake_share_group_type.set_keys.assert_called_with({'key1': 'value1'})

    def test_share_group_type_key_unset(self):
        fake_share_group_type = type(
            'FakeShareGroupType', (object,),
            {'id': '1234', 'is_public': False, 'set_keys': mock.Mock(),
             'unset_keys': mock.Mock()})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))

        self.run_command('share-group-type-key fake_group_type unset key1')

        fake_share_group_type.unset_keys.assert_called_with(['key1'])

    def test_share_group_type_access_list(self):
        fake_share_group_type = type(
            'FakeShareGroupType', (object,),
            {'id': '1234', 'is_public': False})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))

        self.run_command('share-group-type-access-list 1234')

        self.assert_called('GET', '/share-group-types/1234/access')

    def test_share_group_type_access_list_public(self):
        fake_share_group_type = type(
            'FakeShareGroupType', (object,),
            {'id': '1234', 'is_public': True})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))

        self.assertRaises(
            exceptions.CommandError,
            self.run_command, 'share-group-type-access-list 1234')

    def test_share_group_type_access_add_project(self):
        fake_share_group_type = type(
            'FakeShareGroupType', (object,),
            {'id': '1234', 'is_public': False})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))
        expected = {'addProjectAccess': {'project': '101'}}

        self.run_command('share-group-type-access-add 1234 101')

        self.assert_called(
            'POST', '/share-group-types/1234/action', body=expected)

    def test_share_group_type_access_remove_project(self):
        fake_share_group_type = type(
            'FakeShareGroupType', (object,),
            {'id': '1234', 'is_public': False})
        self.mock_object(
            shell_v2, '_find_share_group_type',
            mock.Mock(return_value=fake_share_group_type))
        expected = {'removeProjectAccess': {'project': '101'}}

        self.run_command('share-group-type-access-remove 1234 101')

        self.assert_called(
            'POST', '/share-group-types/1234/action', body=expected)

    @ddt.data(
        {'--shares': 5},
        {'--snapshots': 5},
        {'--gigabytes': 5},
        {'--snapshot-gigabytes': 5},
        {'--snapshot_gigabytes': 5},
        {'--share-networks': 5},
        {'--share_networks': 5},
        {'--shares': 5,
         '--snapshots': 5,
         '--gigabytes': 5,
         '--snapshot-gigabytes': 5,
         '--share-networks': 5})
    def test_quota_class_update(self, data):
        cmd = 'quota-class-update test'
        expected = dict()
        for k, v in data.items():
            cmd += ' %(arg)s %(val)s' % {'arg': k, 'val': v}
            expected[k[2:].replace('-', '_')] = v
        expected['class_name'] = 'test'
        expected = dict(quota_class_set=expected)

        self.run_command(cmd)
        self.assert_called('PUT', '/quota-class-sets/test', body=expected)

    @ddt.data(True, False)
    @mock.patch.object(shell_v2, '_find_share_replica', mock.Mock())
    def test_share_replica_delete_force(self, force):

        fake_replica = type('FakeShareReplica', (object,), {'id': '1234'})
        shell_v2._find_share_replica.return_value = fake_replica

        force = '--force' if force else ''
        self.run_command('share-replica-delete fake-replica ' + force)

        if force:
            self.assert_called('POST', '/share-replicas/1234/action',
                               body={'force_delete': None})
        else:
            self.assert_called('DELETE', '/share-replicas/1234')

    @ddt.data([1, 0], [1, 1], [2, 0], [2, 1], [2, 2])
    @ddt.unpack
    @mock.patch.object(shell_v2, '_find_share_replica', mock.Mock())
    def test_share_replica_delete_errors(self, replica_count, replica_errors):

        class StubbedReplicaFindError(Exception):
            """Error in find share replica stub"""
            pass

        class StubbedFindWithErrors(object):
            def __init__(self, existing_replicas):
                self.existing_replicas = existing_replicas

            def __call__(self, cs, replica):
                if replica not in self.existing_replicas:
                    raise StubbedReplicaFindError
                return type('FakeShareReplica', (object,), {'id': replica})

        all_replicas = []
        existing_replicas = []
        for counter in range(replica_count):
            replica = 'fake-replica-%d' % counter
            if counter >= replica_errors:
                existing_replicas.append(replica)
            all_replicas.append(replica)

        shell_v2._find_share_replica.side_effect = StubbedFindWithErrors(
            existing_replicas)
        cmd = 'share-replica-delete %s' % ' '.join(all_replicas)

        if replica_count == replica_errors:
            self.assertRaises(exceptions.CommandError, self.run_command, cmd)
        else:
            self.run_command(cmd)
            for replica in existing_replicas:
                self.assert_called_anytime('DELETE',
                                           '/share-replicas/' + replica,
                                           clear_callstack=False)

    def test_share_replica_list_all(self):

        self.run_command('share-replica-list')

        self.assert_called('GET', '/share-replicas/detail')

    @mock.patch.object(shell_v2, '_find_share', mock.Mock())
    def test_share_replica_list_for_share(self):

        fshare = type('FakeShare', (object,), {'id': 'fake-share-id'})
        shell_v2._find_share.return_value = fshare
        cmd = 'share-replica-list --share-id %s'
        self.run_command(cmd % fshare.id)

        self.assert_called(
            'GET', '/share-replicas/detail?share_id=fake-share-id')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_share_replica_list_select_column(self):
        self.run_command('share-replica-list --columns id,status')

        self.assert_called('GET', '/share-replicas/detail')

        cliutils.print_list.assert_called_once_with(
            mock.ANY, ['Id', 'Status'])

    @ddt.data(
        'fake-share-id --az fake-az',
        'fake-share-id --availability-zone fake-az --share-network '
        'fake-network',
    )
    @mock.patch.object(shell_v2, '_find_share_network', mock.Mock())
    @mock.patch.object(shell_v2, '_find_share', mock.Mock())
    def test_share_replica_create(self, data):

        fshare = type('FakeShare', (object,), {'id': 'fake-share-id'})
        shell_v2._find_share.return_value = fshare

        fnetwork = type('FakeShareNetwork', (object,), {'id': 'fake-network'})
        shell_v2._find_share_network.return_value = fnetwork

        cmd = 'share-replica-create' + ' ' + data

        self.run_command(cmd)

        shell_v2._find_share.assert_called_with(mock.ANY, fshare.id)
        self.assert_called('POST', '/share-replicas')

    def test_share_replica_show(self):

        self.run_command('share-replica-show 5678')

        self.assert_called_anytime('GET', '/share-replicas/5678')

    @ddt.data('promote', 'resync')
    @mock.patch.object(shell_v2, '_find_share_replica', mock.Mock())
    def test_share_replica_actions(self, action):
        fake_replica = type('FakeShareReplica', (object,), {'id': '1234'})
        shell_v2._find_share_replica.return_value = fake_replica
        cmd = 'share-replica-' + action + ' ' + fake_replica.id

        self.run_command(cmd)

        self.assert_called(
            'POST', '/share-replicas/1234/action',
            body={action.replace('-', '_'): None})

    @mock.patch.object(shell_v2, '_find_share_replica', mock.Mock())
    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    @ddt.data(None, "replica_state,path")
    def test_share_replica_export_location_list(self, columns):
        fake_replica = type('FakeShareReplica', (object,), {'id': '1234'})
        shell_v2._find_share_replica.return_value = fake_replica
        cmd = 'share-replica-export-location-list ' + fake_replica.id
        if columns is not None:
            cmd = cmd + ' --columns=%s' % columns
            expected_columns = list(map(lambda x: x.strip().title(),
                                        columns.split(",")))
        else:
            expected_columns = [
                'ID', 'Availability Zone', 'Replica State',
                'Preferred', 'Path'
            ]

        self.run_command(cmd)

        self.assert_called(
            'GET', '/share-replicas/1234/export-locations')
        cliutils.print_list.assert_called_with(mock.ANY, expected_columns)

    @mock.patch.object(shell_v2, '_find_share_replica', mock.Mock())
    def test_share_replica_export_location_show(self):
        fake_replica = type('FakeShareReplica', (object,), {'id': '1234'})
        shell_v2._find_share_replica.return_value = fake_replica
        self.run_command(
            'share-replica-export-location-show 1234 fake-el-uuid')
        self.assert_called(
            'GET', '/share-replicas/1234/export-locations/fake-el-uuid')

    @ddt.data('reset-state', 'reset-replica-state')
    @mock.patch.object(shell_v2, '_find_share_replica', mock.Mock())
    def test_share_replica_reset_state_cmds(self, action):
        if action == 'reset-state':
            attr = 'status'
            action_name = 'reset_status'
        else:
            attr = 'replica_state'
            action_name = action.replace('-', '_')
        fake_replica = type('FakeShareReplica', (object,), {'id': '1234'})
        shell_v2._find_share_replica.return_value = fake_replica
        cmd = 'share-replica-%(action)s %(resource)s --state %(state)s'

        self.run_command(cmd % {
            'action': action, 'resource': 1234, 'state': 'xyzzyspoon!'})

        self.assert_called(
            'POST', '/share-replicas/1234/action',
            body={action_name: {attr: 'xyzzyspoon!'}})

    def test_snapshot_instance_list_all(self):
        self.run_command('snapshot-instance-list')
        self.assert_called('GET', '/snapshot-instances')

    def test_snapshot_instance_list_all_detail(self):
        self.run_command('snapshot-instance-list --detail True')
        self.assert_called('GET', '/snapshot-instances/detail')

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_snapshot_instance_list_select_column(self):
        self.run_command('snapshot-instance-list --columns id,status')
        self.assert_called('GET', '/snapshot-instances')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, ['Id', 'Status'])

    @mock.patch.object(shell_v2, '_find_share_snapshot', mock.Mock())
    def test_snapshot_instance_list_for_snapshot(self):
        fsnapshot = type('FakeSnapshot', (object,),
                         {'id': 'fake-snapshot-id'})
        shell_v2._find_share_snapshot.return_value = fsnapshot
        cmd = 'snapshot-instance-list --snapshot %s'
        self.run_command(cmd % fsnapshot.id)

        self.assert_called(
            'GET', '/snapshot-instances?snapshot_id=fake-snapshot-id')

    def test_snapshot_instance_show(self):
        self.run_command('snapshot-instance-show 1234')
        self.assert_called_anytime('GET', '/snapshot-instances/1234',
                                   clear_callstack=False)
        self.assert_called_anytime('GET',
                                   '/snapshot-instances/1234/export-locations')

    def test_snapshot_instance_reset_state(self):
        self.run_command('snapshot-instance-reset-state 1234')
        expected = {'reset_status': {'status': 'available'}}
        self.assert_called('POST', '/snapshot-instances/1234/action',
                           body=expected)

    def test_migration_start(self):
        command = ("migration-start --force-host-assisted-migration True "
                   "--new-share-network 1111 --new-share-type 1 1234 "
                   "host@backend#pool --writable False --nondisruptive True "
                   "--preserve-metadata False --preserve-snapshots True")
        self.run_command(command)
        expected = {'migration_start': {
            'host': 'host@backend#pool',
            'force_host_assisted_migration': 'True',
            'preserve_metadata': 'False',
            'writable': 'False',
            'nondisruptive': 'True',
            'preserve_snapshots': 'True',
            'new_share_network_id': 1111,
            'new_share_type_id': 1,
        }}
        self.assert_called('POST', '/shares/1234/action', body=expected)

    @ddt.data('migration-complete', 'migration-get-progress',
              'migration-cancel')
    def test_migration_others(self, method):
        command = ' '.join((method, '1234'))
        self.run_command(command)
        expected = {method.replace('-', '_'): None}
        self.assert_called('POST', '/shares/1234/action', body=expected)

    @ddt.data('migration_error', 'migration_success', None)
    def test_reset_task_state(self, param):
        command = ' '.join(('reset-task-state --state', six.text_type(param),
                            '1234'))
        self.run_command(command)
        expected = {'reset_task_state': {'task_state': param}}
        self.assert_called('POST', '/shares/1234/action', body=expected)

    @ddt.data(('fake_security_service1', ),
              ('fake_security_service1', 'fake_security_service2'))
    def test_security_service_delete(self, ss_ids):
        fake_security_services = [
            security_services.SecurityService('fake', {'id': ss_id}, True)
            for ss_id in ss_ids
        ]
        self.mock_object(
            shell_v2, '_find_security_service',
            mock.Mock(side_effect=fake_security_services))

        self.run_command('security-service-delete %s' % ' '.join(ss_ids))

        shell_v2._find_security_service.assert_has_calls([
            mock.call(self.shell.cs, ss_id) for ss_id in ss_ids
        ])
        for ss in fake_security_services:
            self.assert_called_anytime(
                'DELETE', '/security-services/%s' % ss.id,
                clear_callstack=False)

    @ddt.data(('fake_share_network1', ),
              ('fake_share_network1', 'fake_share_network1'))
    def test_share_network_delete(self, sn_ids):
        fake_share_networks = [
            share_networks.ShareNetwork('fake', {'id': sn_id}, True)
            for sn_id in sn_ids
        ]
        self.mock_object(
            shell_v2, '_find_share_network',
            mock.Mock(side_effect=fake_share_networks))

        self.run_command('share-network-delete %s' % ' '.join(sn_ids))

        shell_v2._find_share_network.assert_has_calls([
            mock.call(self.shell.cs, sn_id) for sn_id in sn_ids
        ])
        for sn in fake_share_networks:
            self.assert_called_anytime(
                'DELETE', '/share-networks/%s' % sn.id,
                clear_callstack=False)

    @ddt.data(('fake_snapshot1', ), ('fake_snapshot1', 'fake_snapshot2'))
    def test_snapshot_delete(self, snapshot_ids):
        fake_snapshots = [
            share_snapshots.ShareSnapshot('fake', {'id': snapshot_id}, True)
            for snapshot_id in snapshot_ids
        ]
        self.mock_object(
            shell_v2, '_find_share_snapshot',
            mock.Mock(side_effect=fake_snapshots))

        self.run_command('snapshot-delete %s' % ' '.join(snapshot_ids))

        shell_v2._find_share_snapshot.assert_has_calls([
            mock.call(self.shell.cs, s_id) for s_id in snapshot_ids
        ])
        for snapshot in fake_snapshots:
            self.assert_called_anytime(
                'DELETE', '/snapshots/%s' % snapshot.id,
                clear_callstack=False)

    @ddt.data(('1234', ), ('1234', '5678'))
    def test_snapshot_force_delete(self, snapshot_ids):
        fake_snapshots = [
            share_snapshots.ShareSnapshot('fake', {'id': snapshot_id}, True)
            for snapshot_id in snapshot_ids
        ]
        self.mock_object(
            shell_v2, '_find_share_snapshot',
            mock.Mock(side_effect=fake_snapshots))

        self.run_command('snapshot-force-delete %s' % ' '.join(snapshot_ids))

        shell_v2._find_share_snapshot.assert_has_calls([
            mock.call(self.shell.cs, s_id) for s_id in snapshot_ids
        ])
        for snapshot in fake_snapshots:
            self.assert_called_anytime(
                'POST', '/snapshots/%s/action' % snapshot.id,
                {'force_delete': None},
                clear_callstack=False)

    @ddt.data(('fake_type1', ), ('fake_type1', 'fake_type2'))
    def test_share_type_delete(self, type_ids):
        fake_share_types = [
            share_types.ShareType('fake', {'id': type_id}, True)
            for type_id in type_ids
        ]
        self.mock_object(
            shell_v2, '_find_share_type',
            mock.Mock(side_effect=fake_share_types))

        self.run_command('type-delete %s' % ' '.join(type_ids))

        shell_v2._find_share_type.assert_has_calls([
            mock.call(self.shell.cs, t_id) for t_id in type_ids
        ])
        for fake_share_type in fake_share_types:
            self.assert_called_anytime(
                'DELETE', '/types/%s' % fake_share_type.id,
                clear_callstack=False)

    @ddt.data(('1234', ), ('1234', '5678'))
    def test_share_server_delete(self, server_ids):
        fake_share_servers = [
            share_servers.ShareServer('fake', {'id': server_id}, True)
            for server_id in server_ids
        ]
        self.mock_object(
            shell_v2, '_find_share_server',
            mock.Mock(side_effect=fake_share_servers))

        self.run_command('share-server-delete %s' % ' '.join(server_ids))

        shell_v2._find_share_server.assert_has_calls([
            mock.call(self.shell.cs, s_id) for s_id in server_ids
        ])
        for server in fake_share_servers:
            self.assert_called_anytime(
                'DELETE', '/share-servers/%s' % server.id,
                clear_callstack=False)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_message_list(self):
        self.run_command('message-list')

        self.assert_called('GET', '/messages')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=['ID', 'Resource Type', 'Resource ID',
                              'Action ID', 'User Message', 'Detail ID',
                              'Created At'], sortby_index=None)

    @mock.patch.object(cliutils, 'print_list', mock.Mock())
    def test_message_list_select_column(self):
        self.run_command('message-list --columns id,resource_type')

        self.assert_called('GET', '/messages')
        cliutils.print_list.assert_called_once_with(
            mock.ANY, fields=['Id', 'Resource_Type'], sortby_index=None)

    def test_message_list_with_filters(self):
        self.run_command('message-list --limit 10 --offset 0')

        self.assert_called(
            'GET', '/messages?limit=10&offset=0')

    def test_message_show(self):
        self.run_command('message-show 1234')

        self.assert_called('GET', '/messages/1234')

    @ddt.data(('1234', ),
              ('1234_error', ),
              ('1234_error', '5678'),
              ('1234', '5678_error'),
              ('1234', '5678'))
    def test_message_delete(self, ids):
        fake_messages = dict()
        for mid in ids:
            if mid.endswith('_error'):
                continue
            fake_messages[mid] = messages.Message('fake', {'id': mid}, True)

        def _find_message_with_errors(cs, mid):
            if mid.endswith('_error'):
                raise Exception
            return fake_messages[mid]

        self.mock_object(
            shell_v2, '_find_message',
            mock.Mock(side_effect=_find_message_with_errors))

        cmd = 'message-delete %s' % ' '.join(ids)

        if len(fake_messages) == 0:
            self.assertRaises(exceptions.CommandError, self.run_command, cmd)
        else:
            self.run_command(cmd)

        shell_v2._find_message.assert_has_calls([
            mock.call(self.shell.cs, mid) for mid in ids
        ])
        for fake_message in fake_messages.values():
            self.assert_called_anytime(
                'DELETE', '/messages/%s' % fake_message.id,
                clear_callstack=False)

    @ddt.data(('share-network-list', ' --description~',
               '/share-networks/', '2.35'),
              ('share-network-list', ' --name~',
               '/share-networks/', '2.35'),
              ('share-group-list', ' --description~',
               '/share-groups/', '2.35'),
              ('share-group-list', ' --name~', '/share-groups/', '2.35'),
              ('list', ' --description~', '/shares/', '2.35'),
              ('list', ' --name~', '/shares/', '2.35'),
              ('snapshot-list', ' --description~', '/snapshots/', '2.35'),
              ('snapshot-list', ' --name~', '/snapshots/', '2.35'))
    @ddt.unpack
    def test_list_filter_by_inexact_version_not_support(
            self, cmd, option, url, version):
        for separator in self.separators:
            self.assertRaises(
                exceptions.CommandError,
                self.run_command,
                cmd + option + separator + 'fake',
                version=version
            )

    def test_share_server_unmanage_all_fail(self):
        # All of 2345, 5678, 9999 throw exception
        cmd = '--os-share-api-version 2.49'
        cmd += ' share-server-unmanage'
        cmd += ' 2345 5678 9999'
        self.assertRaises(exceptions.CommandError,
                          self.run_command, cmd)

    def test_share_server_unmanage_some_fail(self):
        # 5678 and 9999 throw exception
        self.run_command('share-server-unmanage 1234 5678 9999')
        expected = {'unmanage': {'force': False}}
        self.assert_called('POST', '/share-servers/1234/action',
                           body=expected)
