# Copyright (c) 2013 OpenStack Foundation
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
import mock
from requests_mock.contrib import fixture as requests_mock_fixture
from six.moves.urllib import parse

from cinderclient import client
from cinderclient import exceptions
from cinderclient import shell
from cinderclient.v2 import shell as test_shell
from cinderclient.v2 import volume_backups
from cinderclient.v2 import volumes

from cinderclient.tests.unit.fixture_data import keystone_client
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes


@ddt.ddt
@mock.patch.object(client, 'Client', fakes.FakeClient)
class ShellTest(utils.TestCase):

    FAKE_ENV = {
        'CINDER_USERNAME': 'username',
        'CINDER_PASSWORD': 'password',
        'CINDER_PROJECT_ID': 'project_id',
        'OS_VOLUME_API_VERSION': '2',
        'CINDER_URL': keystone_client.BASE_URL,
    }

    # Patch os.environ to avoid required auth info.
    def setUp(self):
        """Run before each test."""
        super(ShellTest, self).setUp()
        for var in self.FAKE_ENV:
            self.useFixture(fixtures.EnvironmentVariable(var,
                                                         self.FAKE_ENV[var]))

        self.mock_completion()

        self.shell = shell.OpenStackCinderShell()

        self.requests = self.useFixture(requests_mock_fixture.Fixture())
        self.requests.register_uri(
            'GET', keystone_client.BASE_URL,
            text=keystone_client.keystone_request_callback)

        self.cs = mock.Mock()

    def _make_args(self, args):
        class Args(object):
            def __init__(self, entries):
                self.__dict__.update(entries)

        return Args(args)

    def run_command(self, cmd):
        self.shell.main(cmd.split())

    def assert_called(self, method, url, body=None,
                      partial_body=None, **kwargs):
        return self.shell.cs.assert_called(method, url, body,
                                           partial_body, **kwargs)

    def test_list(self):
        self.run_command('list')
        # NOTE(jdg): we default to detail currently
        self.assert_called('GET', '/volumes/detail')

    def test_list_filter_tenant_with_all_tenants(self):
        self.run_command('list --all-tenants=1 --tenant 123')
        self.assert_called('GET',
                           '/volumes/detail?all_tenants=1&project_id=123')

    def test_list_filter_tenant_without_all_tenants(self):
        self.run_command('list --tenant 123')
        self.assert_called('GET',
                           '/volumes/detail?all_tenants=1&project_id=123')

    def test_metadata_args_with_limiter(self):
        self.run_command('create --metadata key1="--test1" 1')
        self.assert_called('GET', '/volumes/1234')
        expected = {'volume': {'imageRef': None,
                               'size': 1,
                               'availability_zone': None,
                               'source_volid': None,
                               'consistencygroup_id': None,
                               'name': None,
                               'snapshot_id': None,
                               'metadata': {'key1': '"--test1"'},
                               'volume_type': None,
                               'description': None,
                               }}
        self.assert_called_anytime('POST', '/volumes', expected)

    def test_metadata_args_limiter_display_name(self):
        self.run_command('create --metadata key1="--t1" --name="t" 1')
        self.assert_called('GET', '/volumes/1234')
        expected = {'volume': {'imageRef': None,
                               'size': 1,
                               'availability_zone': None,
                               'source_volid': None,
                               'consistencygroup_id': None,
                               'name': '"t"',
                               'snapshot_id': None,
                               'metadata': {'key1': '"--t1"'},
                               'volume_type': None,
                               'description': None,
                               }}
        self.assert_called_anytime('POST', '/volumes', expected)

    def test_delimit_metadata_args(self):
        self.run_command('create --metadata key1="test1" key2="test2" 1')
        expected = {'volume': {'imageRef': None,
                               'size': 1,
                               'availability_zone': None,
                               'source_volid': None,
                               'consistencygroup_id': None,
                               'name': None,
                               'snapshot_id': None,
                               'metadata': {'key1': '"test1"',
                                            'key2': '"test2"'},
                               'volume_type': None,
                               'description': None,
                               }}
        self.assert_called_anytime('POST', '/volumes', expected)

    def test_delimit_metadata_args_display_name(self):
        self.run_command('create --metadata key1="t1" --name="t" 1')
        self.assert_called('GET', '/volumes/1234')
        expected = {'volume': {'imageRef': None,
                               'size': 1,
                               'availability_zone': None,
                               'source_volid': None,
                               'consistencygroup_id': None,
                               'name': '"t"',
                               'snapshot_id': None,
                               'metadata': {'key1': '"t1"'},
                               'volume_type': None,
                               'description': None,
                               }}
        self.assert_called_anytime('POST', '/volumes', expected)

    def test_list_filter_status(self):
        self.run_command('list --status=available')
        self.assert_called('GET', '/volumes/detail?status=available')

    def test_list_filter_bootable_true(self):
        self.run_command('list --bootable=true')
        self.assert_called('GET', '/volumes/detail?bootable=true')

    def test_list_filter_bootable_false(self):
        self.run_command('list --bootable=false')
        self.assert_called('GET', '/volumes/detail?bootable=false')

    def test_list_filter_name(self):
        self.run_command('list --name=1234')
        self.assert_called('GET', '/volumes/detail?name=1234')

    def test_list_all_tenants(self):
        self.run_command('list --all-tenants=1')
        self.assert_called('GET', '/volumes/detail?all_tenants=1')

    def test_list_marker(self):
        self.run_command('list --marker=1234')
        self.assert_called('GET', '/volumes/detail?marker=1234')

    def test_list_limit(self):
        self.run_command('list --limit=10')
        self.assert_called('GET', '/volumes/detail?limit=10')

    @mock.patch("cinderclient.utils.print_list")
    def test_list_field(self, mock_print):
        self.run_command('list --field Status,Name,Size,Bootable')
        self.assert_called('GET', '/volumes/detail')
        key_list = ['ID', 'Status', 'Name', 'Size', 'Bootable']
        mock_print.assert_called_once_with(mock.ANY, key_list,
            exclude_unavailable=True, sortby_index=0)

    @mock.patch("cinderclient.utils.print_list")
    def test_list_field_with_all_tenants(self, mock_print):
        self.run_command('list --field Status,Name,Size,Bootable '
                         '--all-tenants 1')
        self.assert_called('GET', '/volumes/detail?all_tenants=1')
        key_list = ['ID', 'Status', 'Name', 'Size', 'Bootable']
        mock_print.assert_called_once_with(mock.ANY, key_list,
            exclude_unavailable=True, sortby_index=0)

    @mock.patch("cinderclient.utils.print_list")
    def test_list_duplicate_fields(self, mock_print):
        self.run_command('list --field Status,id,Size,status')
        self.assert_called('GET', '/volumes/detail')
        key_list = ['ID', 'Status', 'Size']
        mock_print.assert_called_once_with(mock.ANY, key_list,
            exclude_unavailable=True, sortby_index=0)

    @mock.patch("cinderclient.utils.print_list")
    def test_list_field_with_tenant(self, mock_print):
        self.run_command('list --field Status,Name,Size,Bootable '
                         '--tenant 123')
        self.assert_called('GET',
            '/volumes/detail?all_tenants=1&project_id=123')
        key_list = ['ID', 'Status', 'Name', 'Size', 'Bootable']
        mock_print.assert_called_once_with(mock.ANY, key_list,
            exclude_unavailable=True, sortby_index=0)

    def test_list_sort_name(self):
        # Client 'name' key is mapped to 'display_name'
        self.run_command('list --sort=name')
        self.assert_called('GET', '/volumes/detail?sort=display_name')

    def test_list_sort_single_key_only(self):
        self.run_command('list --sort=id')
        self.assert_called('GET', '/volumes/detail?sort=id')

    def test_list_sort_single_key_trailing_colon(self):
        self.run_command('list --sort=id:')
        self.assert_called('GET', '/volumes/detail?sort=id')

    def test_list_sort_single_key_and_dir(self):
        self.run_command('list --sort=id:asc')
        url = '/volumes/detail?%s' % parse.urlencode([('sort', 'id:asc')])
        self.assert_called('GET', url)

    def test_list_sort_multiple_keys_only(self):
        self.run_command('list --sort=id,status,size')
        url = ('/volumes/detail?%s' %
               parse.urlencode([('sort', 'id,status,size')]))
        self.assert_called('GET', url)

    def test_list_sort_multiple_keys_and_dirs(self):
        self.run_command('list --sort=id:asc,status,size:desc')
        url = ('/volumes/detail?%s' %
               parse.urlencode([('sort', 'id:asc,status,size:desc')]))
        self.assert_called('GET', url)

    def test_list_reorder_with_sort(self):
        # sortby_index is None if there is sort information
        for cmd in ['list --sort=name',
                    'list --sort=name:asc']:
            with mock.patch('cinderclient.utils.print_list') as mock_print:
                self.run_command(cmd)
                mock_print.assert_called_once_with(
                    mock.ANY, mock.ANY, exclude_unavailable=True,
                    sortby_index=None)

    def test_list_reorder_without_sort(self):
        # sortby_index is 0 without sort information
        for cmd in ['list', 'list --all-tenants']:
            with mock.patch('cinderclient.utils.print_list') as mock_print:
                self.run_command(cmd)
                mock_print.assert_called_once_with(
                    mock.ANY, mock.ANY, exclude_unavailable=True,
                    sortby_index=0)

    def test_list_availability_zone(self):
        self.run_command('availability-zone-list')
        self.assert_called('GET', '/os-availability-zone')

    def test_create_volume_from_snapshot(self):
        expected = {'volume': {'size': None}}

        expected['volume']['snapshot_id'] = '1234'
        self.run_command('create --snapshot-id=1234')
        self.assert_called_anytime('POST', '/volumes', partial_body=expected)
        self.assert_called('GET', '/volumes/1234')

        expected['volume']['size'] = 2
        self.run_command('create --snapshot-id=1234 2')
        self.assert_called_anytime('POST', '/volumes', partial_body=expected)
        self.assert_called('GET', '/volumes/1234')

    def test_create_volume_from_volume(self):
        expected = {'volume': {'size': None}}

        expected['volume']['source_volid'] = '1234'
        self.run_command('create --source-volid=1234')
        self.assert_called_anytime('POST', '/volumes', partial_body=expected)
        self.assert_called('GET', '/volumes/1234')

        expected['volume']['size'] = 2
        self.run_command('create --source-volid=1234 2')
        self.assert_called_anytime('POST', '/volumes', partial_body=expected)
        self.assert_called('GET', '/volumes/1234')

    def test_create_volume_from_image(self):
        expected = {'volume': {'size': 1,
                               'imageRef': '1234'}}
        self.run_command('create --image=1234 1')
        self.assert_called_anytime('POST', '/volumes', partial_body=expected)
        self.assert_called('GET', '/volumes/1234')

    def test_upload_to_image(self):
        expected = {'os-volume_upload_image': {'force': False,
                                               'container_format': 'bare',
                                               'disk_format': 'raw',
                                               'image_name': 'test-image'}}
        self.run_command('upload-to-image 1234 test-image')
        self.assert_called_anytime('GET', '/volumes/1234')
        self.assert_called_anytime('POST', '/volumes/1234/action',
                                   body=expected)

    def test_upload_to_image_force(self):
        expected = {'os-volume_upload_image': {'force': 'True',
                                               'container_format': 'bare',
                                               'disk_format': 'raw',
                                               'image_name': 'test-image'}}
        self.run_command('upload-to-image --force=True 1234 test-image')
        self.assert_called_anytime('GET', '/volumes/1234')
        self.assert_called_anytime('POST', '/volumes/1234/action',
                                   body=expected)

    def test_create_size_required_if_not_snapshot_or_clone(self):
        self.assertRaises(SystemExit, self.run_command, 'create')

    def test_create_size_zero_if_not_snapshot_or_clone(self):
        expected = {'volume': {'size': 0}}
        self.run_command('create 0')
        self.assert_called_anytime('POST', '/volumes', partial_body=expected)
        self.assert_called('GET', '/volumes/1234')

    def test_show(self):
        self.run_command('show 1234')
        self.assert_called('GET', '/volumes/1234')

    def test_delete(self):
        self.run_command('delete 1234')
        self.assert_called('DELETE', '/volumes/1234')

    def test_delete_by_name(self):
        self.run_command('delete sample-volume')
        self.assert_called_anytime('GET', '/volumes/detail?all_tenants=1&'
                                          'name=sample-volume')
        self.assert_called('DELETE', '/volumes/1234')

    def test_delete_multiple(self):
        self.run_command('delete 1234 5678')
        self.assert_called_anytime('DELETE', '/volumes/1234')
        self.assert_called('DELETE', '/volumes/5678')

    def test_delete_with_cascade_true(self):
        self.run_command('delete 1234 --cascade')
        self.assert_called('DELETE', '/volumes/1234?cascade=True')
        self.run_command('delete --cascade 1234')
        self.assert_called('DELETE', '/volumes/1234?cascade=True')

    def test_delete_with_cascade_with_invalid_value(self):
        self.assertRaises(SystemExit, self.run_command,
                          'delete 1234 --cascade 1234')

    def test_backup(self):
        self.run_command('backup-create 1234')
        self.assert_called('POST', '/backups')

    def test_backup_incremental(self):
        self.run_command('backup-create 1234 --incremental')
        self.assert_called('POST', '/backups')

    def test_backup_force(self):
        self.run_command('backup-create 1234 --force')
        self.assert_called('POST', '/backups')

    def test_backup_snapshot(self):
        self.run_command('backup-create 1234 --snapshot-id 4321')
        self.assert_called('POST', '/backups')

    def test_multiple_backup_delete(self):
        self.run_command('backup-delete 1234 5678')
        self.assert_called_anytime('DELETE', '/backups/1234')
        self.assert_called('DELETE', '/backups/5678')

    def test_restore(self):
        self.run_command('backup-restore 1234')
        self.assert_called('POST', '/backups/1234/restore')

    def test_restore_with_name(self):
        self.run_command('backup-restore 1234 --name restore_vol')
        expected = {'restore': {'volume_id': None, 'name': 'restore_vol'}}
        self.assert_called('POST', '/backups/1234/restore',
                           body=expected)

    def test_restore_with_name_error(self):
        self.assertRaises(exceptions.CommandError, self.run_command,
                          'backup-restore 1234 --volume fake_vol --name '
                          'restore_vol')

    @ddt.data('backup_name', '1234')
    @mock.patch('cinderclient.shell_utils.find_backup')
    @mock.patch('cinderclient.utils.print_dict')
    @mock.patch('cinderclient.utils.find_volume')
    def test_do_backup_restore_with_name(self,
                                         value,
                                         mock_find_volume,
                                         mock_print_dict,
                                         mock_find_backup):
        backup_id = '1234'
        volume_id = '5678'
        name = None
        input = {
            'backup': value,
            'volume': volume_id,
            'name': None
        }

        args = self._make_args(input)
        with mock.patch.object(self.cs.restores,
                               'restore') as mocked_restore:
            mock_find_volume.return_value = volumes.Volume(self,
                                                           {'id': volume_id},
                                                           loaded=True)
            mock_find_backup.return_value = volume_backups.VolumeBackup(
                self,
                {'id': backup_id},
                loaded=True)
            test_shell.do_backup_restore(self.cs, args)
            mock_find_backup.assert_called_once_with(
                self.cs,
                value)
            mocked_restore.assert_called_once_with(
                backup_id,
                volume_id,
                name)
            self.assertTrue(mock_print_dict.called)

    def test_record_export(self):
        self.run_command('backup-export 1234')
        self.assert_called('GET', '/backups/1234/export_record')

    def test_record_import(self):
        self.run_command('backup-import fake.driver URL_STRING')
        expected = {'backup-record': {'backup_service': 'fake.driver',
                                      'backup_url': 'URL_STRING'}}
        self.assert_called('POST', '/backups/import_record', expected)

    def test_snapshot_list_filter_volume_id(self):
        self.run_command('snapshot-list --volume-id=1234')
        self.assert_called('GET', '/snapshots/detail?volume_id=1234')

    def test_snapshot_list_filter_status_and_volume_id(self):
        self.run_command('snapshot-list --status=available --volume-id=1234')
        self.assert_called('GET', '/snapshots/detail?'
                           'status=available&volume_id=1234')

    def test_snapshot_list_filter_name(self):
        self.run_command('snapshot-list --name abc')
        self.assert_called('GET', '/snapshots/detail?name=abc')

    @mock.patch("cinderclient.utils.print_list")
    def test_snapshot_list_sort(self, mock_print_list):
        self.run_command('snapshot-list --sort id')
        self.assert_called('GET', '/snapshots/detail?sort=id')
        columns = ['ID', 'Volume ID', 'Status', 'Name', 'Size']
        mock_print_list.assert_called_once_with(mock.ANY, columns,
            sortby_index=None)

    def test_snapshot_list_filter_tenant_with_all_tenants(self):
        self.run_command('snapshot-list --all-tenants=1 --tenant 123')
        self.assert_called('GET',
                           '/snapshots/detail?all_tenants=1&project_id=123')

    def test_snapshot_list_filter_tenant_without_all_tenants(self):
        self.run_command('snapshot-list --tenant 123')
        self.assert_called('GET',
                           '/snapshots/detail?all_tenants=1&project_id=123')

    def test_rename(self):
        # basic rename with positional arguments
        self.run_command('rename 1234 new-name')
        expected = {'volume': {'name': 'new-name'}}
        self.assert_called('PUT', '/volumes/1234', body=expected)
        # change description only
        self.run_command('rename 1234 --description=new-description')
        expected = {'volume': {'description': 'new-description'}}
        self.assert_called('PUT', '/volumes/1234', body=expected)
        # rename and change description
        self.run_command('rename 1234 new-name '
                         '--description=new-description')
        expected = {'volume': {
            'name': 'new-name',
            'description': 'new-description',
        }}
        self.assert_called('PUT', '/volumes/1234', body=expected)

        # Call rename with no arguments
        self.assertRaises(SystemExit, self.run_command, 'rename')

    def test_rename_invalid_args(self):
        """Ensure that error generated does not reference an HTTP code."""

        self.assertRaisesRegex(exceptions.ClientException,
                               '(?!HTTP)',
                               self.run_command,
                               'rename volume-1234-abcd')

    def test_rename_snapshot(self):
        # basic rename with positional arguments
        self.run_command('snapshot-rename 1234 new-name')
        expected = {'snapshot': {'name': 'new-name'}}
        self.assert_called('PUT', '/snapshots/1234', body=expected)
        # change description only
        self.run_command('snapshot-rename 1234 '
                         '--description=new-description')
        expected = {'snapshot': {'description': 'new-description'}}
        self.assert_called('PUT', '/snapshots/1234', body=expected)
        # snapshot-rename and change description
        self.run_command('snapshot-rename 1234 new-name '
                         '--description=new-description')
        expected = {'snapshot': {
            'name': 'new-name',
            'description': 'new-description',
        }}
        self.assert_called('PUT', '/snapshots/1234', body=expected)

        # Call snapshot-rename with no arguments
        self.assertRaises(SystemExit, self.run_command, 'snapshot-rename')

    def test_rename_snapshot_invalid_args(self):
        self.assertRaises(exceptions.ClientException,
                          self.run_command,
                          'snapshot-rename snapshot-1234')

    def test_set_metadata_set(self):
        self.run_command('metadata 1234 set key1=val1 key2=val2')
        self.assert_called('POST', '/volumes/1234/metadata',
                           {'metadata': {'key1': 'val1', 'key2': 'val2'}})

    def test_set_metadata_delete_dict(self):
        self.run_command('metadata 1234 unset key1=val1 key2=val2')
        self.assert_called('DELETE', '/volumes/1234/metadata/key1')
        self.assert_called('DELETE', '/volumes/1234/metadata/key2', pos=-2)

    def test_set_metadata_delete_keys(self):
        self.run_command('metadata 1234 unset key1 key2')
        self.assert_called('DELETE', '/volumes/1234/metadata/key1')
        self.assert_called('DELETE', '/volumes/1234/metadata/key2', pos=-2)

    def test_reset_state(self):
        self.run_command('reset-state 1234')
        expected = {'os-reset_status': {'status': 'available'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_reset_state_attach(self):
        self.run_command('reset-state --state in-use 1234')
        expected = {'os-reset_status': {'status': 'in-use'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_reset_state_with_flag(self):
        self.run_command('reset-state --state error 1234')
        expected = {'os-reset_status': {'status': 'error'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_reset_state_with_attach_status(self):
        self.run_command('reset-state --attach-status detached 1234')
        expected = {'os-reset_status': {'attach_status': 'detached'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_reset_state_with_attach_status_with_flag(self):
        self.run_command('reset-state --state in-use '
                         '--attach-status attached 1234')
        expected = {'os-reset_status': {'status': 'in-use',
                                        'attach_status': 'attached'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_reset_state_with_reset_migration_status(self):
        self.run_command('reset-state --reset-migration-status 1234')
        expected = {'os-reset_status': {'migration_status': 'none'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_reset_state_multiple(self):
        self.run_command('reset-state 1234 5678 --state error')
        expected = {'os-reset_status': {'status': 'error'}}
        self.assert_called_anytime('POST', '/volumes/1234/action',
                                   body=expected)
        self.assert_called_anytime('POST', '/volumes/5678/action',
                                   body=expected)

    def test_reset_state_two_with_one_nonexistent(self):
        cmd = 'reset-state 1234 123456789'
        self.assertRaises(exceptions.CommandError, self.run_command, cmd)
        expected = {'os-reset_status': {'status': 'available'}}
        self.assert_called_anytime('POST', '/volumes/1234/action',
                                   body=expected)

    def test_reset_state_one_with_one_nonexistent(self):
        cmd = 'reset-state 123456789'
        self.assertRaises(exceptions.CommandError, self.run_command, cmd)

    def test_snapshot_reset_state(self):
        self.run_command('snapshot-reset-state 1234')
        expected = {'os-reset_status': {'status': 'available'}}
        self.assert_called('POST', '/snapshots/1234/action', body=expected)

    def test_snapshot_reset_state_with_flag(self):
        self.run_command('snapshot-reset-state --state error 1234')
        expected = {'os-reset_status': {'status': 'error'}}
        self.assert_called('POST', '/snapshots/1234/action', body=expected)

    def test_snapshot_reset_state_multiple(self):
        self.run_command('snapshot-reset-state 1234 5678')
        expected = {'os-reset_status': {'status': 'available'}}
        self.assert_called_anytime('POST', '/snapshots/1234/action',
                                   body=expected)
        self.assert_called_anytime('POST', '/snapshots/5678/action',
                                   body=expected)

    def test_backup_reset_state(self):
        self.run_command('backup-reset-state 1234')
        expected = {'os-reset_status': {'status': 'available'}}
        self.assert_called('POST', '/backups/1234/action', body=expected)

    def test_backup_reset_state_with_flag(self):
        self.run_command('backup-reset-state --state error 1234')
        expected = {'os-reset_status': {'status': 'error'}}
        self.assert_called('POST', '/backups/1234/action', body=expected)

    def test_backup_reset_state_multiple(self):
        self.run_command('backup-reset-state 1234 5678')
        expected = {'os-reset_status': {'status': 'available'}}
        self.assert_called_anytime('POST', '/backups/1234/action',
                                   body=expected)
        self.assert_called_anytime('POST', '/backups/5678/action',
                                   body=expected)

    def test_type_list(self):
        self.run_command('type-list')
        self.assert_called_anytime('GET', '/types?is_public=None')

    def test_type_show(self):
        self.run_command('type-show 1')
        self.assert_called('GET', '/types/1')

    def test_type_create(self):
        self.run_command('type-create test-type-1')
        self.assert_called('POST', '/types')

    def test_type_create_public(self):
        expected = {'volume_type': {'name': 'test-type-1',
                                    'description': 'test_type-1-desc',
                                    'os-volume-type-access:is_public': True}}
        self.run_command('type-create test-type-1 '
                         '--description=test_type-1-desc '
                         '--is-public=True')
        self.assert_called('POST', '/types', body=expected)

    def test_type_create_private(self):
        expected = {'volume_type': {'name': 'test-type-3',
                                    'description': 'test_type-3-desc',
                                    'os-volume-type-access:is_public': False}}
        self.run_command('type-create test-type-3 '
                         '--description=test_type-3-desc '
                         '--is-public=False')
        self.assert_called('POST', '/types', body=expected)

    def test_type_create_with_invalid_bool(self):
        self.assertRaises(ValueError,
                          self.run_command,
                          ('type-create test-type-3 '
                          '--description=test_type-3-desc '
                          '--is-public=invalid_bool'))

    def test_type_update(self):
        expected = {'volume_type': {'name': 'test-type-1',
                                    'description': 'test_type-1-desc',
                                    'is_public': False}}
        self.run_command('type-update --name test-type-1 '
                         '--description=test_type-1-desc '
                         '--is-public=False 1')
        self.assert_called('PUT', '/types/1', body=expected)

    def test_type_update_with_invalid_bool(self):
        self.assertRaises(ValueError,
                          self.run_command,
                          'type-update --name test-type-1 '
                          '--description=test_type-1-desc '
                          '--is-public=invalid_bool 1')

    def test_type_update_without_args(self):
        self.assertRaises(exceptions.CommandError, self.run_command,
                          'type-update 1')

    def test_type_access_list(self):
        self.run_command('type-access-list --volume-type 3')
        self.assert_called('GET', '/types/3/os-volume-type-access')

    def test_type_access_add_project(self):
        expected = {'addProjectAccess': {'project': '101'}}
        self.run_command('type-access-add --volume-type 3 --project-id 101')
        self.assert_called_anytime('GET', '/types/3')
        self.assert_called('POST', '/types/3/action',
                           body=expected)

    def test_type_access_add_project_by_name(self):
        expected = {'addProjectAccess': {'project': '101'}}
        with mock.patch('cinderclient.utils.find_resource') as mock_find:
            mock_find.return_value = '3'
            self.run_command('type-access-add --volume-type type_name \
                              --project-id 101')
            mock_find.assert_called_once_with(mock.ANY, 'type_name')
        self.assert_called('POST', '/types/3/action',
                           body=expected)

    def test_type_access_remove_project(self):
        expected = {'removeProjectAccess': {'project': '101'}}
        self.run_command('type-access-remove '
                         '--volume-type 3 --project-id 101')
        self.assert_called_anytime('GET', '/types/3')
        self.assert_called('POST', '/types/3/action',
                           body=expected)

    def test_type_delete(self):
        self.run_command('type-delete 1')
        self.assert_called('DELETE', '/types/1')

    def test_type_delete_multiple(self):
        self.run_command('type-delete 1 3')
        self.assert_called_anytime('DELETE', '/types/1')
        self.assert_called('DELETE', '/types/3')

    def test_type_delete_by_name(self):
        self.run_command('type-delete test-type-1')
        self.assert_called_anytime('GET', '/types?is_public=None')
        self.assert_called('DELETE', '/types/1')

    def test_encryption_type_list(self):
        """
        Test encryption-type-list shell command.

        Verify a series of GET requests are made:
        - one to get the volume type list information
        - one per volume type to retrieve the encryption type information
        """
        self.run_command('encryption-type-list')
        self.assert_called_anytime('GET', '/types?is_public=None')
        self.assert_called_anytime('GET', '/types/1/encryption')
        self.assert_called_anytime('GET', '/types/2/encryption')

    def test_encryption_type_show(self):
        """
        Test encryption-type-show shell command.

        Verify two GET requests are made per command invocation:
        - one to get the volume type information
        - one to get the encryption type information
        """
        self.run_command('encryption-type-show 1')
        self.assert_called('GET', '/types/1/encryption')
        self.assert_called_anytime('GET', '/types/1')

    def test_encryption_type_create(self):
        """
        Test encryption-type-create shell command.

        Verify GET and POST requests are made per command invocation:
        - one GET request to retrieve the relevant volume type information
        - one POST request to create the new encryption type
        """

        expected = {'encryption': {'cipher': None, 'key_size': None,
                                   'provider': 'TestProvider',
                                   'control_location': 'front-end'}}
        self.run_command('encryption-type-create 2 TestProvider')
        self.assert_called('POST', '/types/2/encryption', body=expected)
        self.assert_called_anytime('GET', '/types/2')

    @ddt.data('--key-size 512 --control-location front-end',
              '--key_size 512 --control_location front-end')  # old style
    def test_encryption_type_create_with_args(self, arg):
        expected = {'encryption': {'cipher': None,
                                   'key_size': 512,
                                   'provider': 'TestProvider',
                                   'control_location': 'front-end'}}
        self.run_command('encryption-type-create 2 TestProvider ' + arg)
        self.assert_called('POST', '/types/2/encryption', body=expected)
        self.assert_called_anytime('GET', '/types/2')

    def test_encryption_type_update(self):
        """
        Test encryption-type-update shell command.

        Verify two GETs/one PUT requests are made per command invocation:
        - one GET request to retrieve the relevant volume type information
        - one GET request to retrieve the relevant encryption type information
        - one PUT request to update the encryption type information
        Verify that the PUT request correctly parses encryption-type-update
        parameters from sys.argv
        """
        parameters = {'--provider': 'EncryptionProvider', '--cipher': 'des',
                      '--key-size': 1024, '--control-location': 'back-end'}

        # Construct the argument string for the update call and the
        # expected encryption-type body that should be produced by it
        args = ' '.join(['%s %s' % (k, v) for k, v in parameters.items()])
        expected = {'encryption': {'provider': 'EncryptionProvider',
                                   'cipher': 'des',
                                   'key_size': 1024,
                                   'control_location': 'back-end'}}

        self.run_command('encryption-type-update 1 %s' % args)
        self.assert_called('GET', '/types/1/encryption')
        self.assert_called_anytime('GET', '/types/1')
        self.assert_called_anytime('PUT', '/types/1/encryption/provider',
                                   body=expected)

    def test_encryption_type_update_no_attributes(self):
        """
        Test encryption-type-update shell command.

        Verify two GETs/one PUT requests are made per command invocation:
        - one GET request to retrieve the relevant volume type information
        - one GET request to retrieve the relevant encryption type information
        - one PUT request to update the encryption type information
        """
        expected = {'encryption': {}}
        self.run_command('encryption-type-update 1')
        self.assert_called('GET', '/types/1/encryption')
        self.assert_called_anytime('GET', '/types/1')
        self.assert_called_anytime('PUT', '/types/1/encryption/provider',
                                   body=expected)

    def test_encryption_type_update_default_attributes(self):
        """
        Test encryption-type-update shell command.

        Verify two GETs/one PUT requests are made per command invocation:
        - one GET request to retrieve the relevant volume type information
        - one GET request to retrieve the relevant encryption type information
        - one PUT request to update the encryption type information
        Verify that the encryption-type body produced contains default None
        values for all specified parameters.
        """
        parameters = ['--cipher', '--key-size']

        # Construct the argument string for the update call and the
        # expected encryption-type body that should be produced by it
        args = ' '.join(['%s' % (p) for p in parameters])
        expected_pairs = [(k.strip('-').replace('-', '_'), None) for k in
                          parameters]
        expected = {'encryption': dict(expected_pairs)}

        self.run_command('encryption-type-update 1 %s' % args)
        self.assert_called('GET', '/types/1/encryption')
        self.assert_called_anytime('GET', '/types/1')
        self.assert_called_anytime('PUT', '/types/1/encryption/provider',
                                   body=expected)

    def test_encryption_type_delete(self):
        """
        Test encryption-type-delete shell command.

        Verify one GET/one DELETE requests are made per command invocation:
        - one GET request to retrieve the relevant volume type information
        - one DELETE request to delete the encryption type information
        """
        self.run_command('encryption-type-delete 1')
        self.assert_called('DELETE', '/types/1/encryption/provider')
        self.assert_called_anytime('GET', '/types/1')

    def test_migrate_volume(self):
        self.run_command('migrate 1234 fakehost --force-host-copy=True '
                         '--lock-volume=True')
        expected = {'os-migrate_volume': {'force_host_copy': 'True',
                                          'lock_volume': 'True',
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_migrate_volume_bool_force(self):
        self.run_command('migrate 1234 fakehost --force-host-copy '
                         '--lock-volume')
        expected = {'os-migrate_volume': {'force_host_copy': True,
                                          'lock_volume': True,
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_migrate_volume_bool_force_false(self):
        # Set both --force-host-copy and --lock-volume to False.
        self.run_command('migrate 1234 fakehost --force-host-copy=False '
                         '--lock-volume=False')
        expected = {'os-migrate_volume': {'force_host_copy': 'False',
                                          'lock_volume': 'False',
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

        # Do not set the values to --force-host-copy and --lock-volume.
        self.run_command('migrate 1234 fakehost')
        expected = {'os-migrate_volume': {'force_host_copy': False,
                                          'lock_volume': False,
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action',
                           body=expected)

    def test_snapshot_metadata_set(self):
        self.run_command('snapshot-metadata 1234 set key1=val1 key2=val2')
        self.assert_called('POST', '/snapshots/1234/metadata',
                           {'metadata': {'key1': 'val1', 'key2': 'val2'}})

    def test_snapshot_metadata_unset_dict(self):
        self.run_command('snapshot-metadata 1234 unset key1=val1 key2=val2')
        self.assert_called_anytime('DELETE', '/snapshots/1234/metadata/key1')
        self.assert_called_anytime('DELETE', '/snapshots/1234/metadata/key2')

    def test_snapshot_metadata_unset_keys(self):
        self.run_command('snapshot-metadata 1234 unset key1 key2')
        self.assert_called_anytime('DELETE', '/snapshots/1234/metadata/key1')
        self.assert_called_anytime('DELETE', '/snapshots/1234/metadata/key2')

    def test_volume_metadata_update_all(self):
        self.run_command('metadata-update-all 1234  key1=val1 key2=val2')
        self.assert_called('PUT', '/volumes/1234/metadata',
                           {'metadata': {'key1': 'val1', 'key2': 'val2'}})

    def test_snapshot_metadata_update_all(self):
        self.run_command('snapshot-metadata-update-all\
                         1234 key1=val1 key2=val2')
        self.assert_called('PUT', '/snapshots/1234/metadata',
                           {'metadata': {'key1': 'val1', 'key2': 'val2'}})

    def test_readonly_mode_update(self):
        self.run_command('readonly-mode-update 1234 True')
        expected = {'os-update_readonly_flag': {'readonly': True}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

        self.run_command('readonly-mode-update 1234 False')
        expected = {'os-update_readonly_flag': {'readonly': False}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_service_disable(self):
        self.run_command('service-disable host cinder-volume')
        self.assert_called('PUT', '/os-services/disable',
                           {"binary": "cinder-volume", "host": "host"})

    def test_services_disable_with_reason(self):
        cmd = 'service-disable host cinder-volume --reason no_reason'
        self.run_command(cmd)
        body = {'host': 'host', 'binary': 'cinder-volume',
                'disabled_reason': 'no_reason'}
        self.assert_called('PUT', '/os-services/disable-log-reason', body)

    def test_service_enable(self):
        self.run_command('service-enable host cinder-volume')
        self.assert_called('PUT', '/os-services/enable',
                           {"binary": "cinder-volume", "host": "host"})

    def test_retype_with_policy(self):
        self.run_command('retype 1234 foo --migration-policy=on-demand')
        expected = {'os-retype': {'new_type': 'foo',
                                  'migration_policy': 'on-demand'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_retype_default_policy(self):
        self.run_command('retype 1234 foo')
        expected = {'os-retype': {'new_type': 'foo',
                                  'migration_policy': 'never'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_snapshot_delete(self):
        """Tests delete snapshot without force parameter"""
        self.run_command('snapshot-delete 1234')
        self.assert_called('DELETE', '/snapshots/1234')

    def test_snapshot_delete_multiple(self):
        """Tests delete multiple snapshots without force parameter"""
        self.run_command('snapshot-delete 5678 1234')
        self.assert_called_anytime('DELETE', '/snapshots/5678')
        self.assert_called('DELETE', '/snapshots/1234')

    def test_force_snapshot_delete(self):
        """Tests delete snapshot with default force parameter value(True)"""
        self.run_command('snapshot-delete 1234 --force')
        expected_body = {'os-force_delete': None}
        self.assert_called('POST',
                           '/snapshots/1234/action',
                           expected_body)

    def test_force_snapshot_delete_multiple(self):
        """
        Tests delete multiple snapshots with force parameter

        Snapshot delete with force parameter allows deleting snapshot of a
        volume when its status is other than "available" or "error".
        """
        self.run_command('snapshot-delete 5678 1234 --force')
        expected_body = {'os-force_delete': None}
        self.assert_called_anytime('POST',
                                   '/snapshots/5678/action',
                                   expected_body)
        self.assert_called_anytime('POST',
                                   '/snapshots/1234/action',
                                   expected_body)

    def test_quota_delete(self):
        self.run_command('quota-delete 1234')
        self.assert_called('DELETE', '/os-quota-sets/1234')

    def test_volume_manage(self):
        self.run_command('manage host1 some_fake_name '
                         '--name foo --description bar '
                         '--volume-type baz --availability-zone az '
                         '--metadata k1=v1 k2=v2')
        expected = {'volume': {'host': 'host1',
                               'ref': {'source-name': 'some_fake_name'},
                               'name': 'foo',
                               'description': 'bar',
                               'volume_type': 'baz',
                               'availability_zone': 'az',
                               'metadata': {'k1': 'v1', 'k2': 'v2'},
                               'bootable': False}}
        self.assert_called_anytime('POST', '/os-volume-manage', body=expected)

    def test_volume_manage_bootable(self):
        """
        Tests the --bootable option

        If this flag is specified, then the resulting POST should contain
        bootable: True.
        """
        self.run_command('manage host1 some_fake_name '
                         '--name foo --description bar --bootable '
                         '--volume-type baz --availability-zone az '
                         '--metadata k1=v1 k2=v2')
        expected = {'volume': {'host': 'host1',
                               'ref': {'source-name': 'some_fake_name'},
                               'name': 'foo',
                               'description': 'bar',
                               'volume_type': 'baz',
                               'availability_zone': 'az',
                               'metadata': {'k1': 'v1', 'k2': 'v2'},
                               'bootable': True}}
        self.assert_called_anytime('POST', '/os-volume-manage', body=expected)

    def test_volume_manage_source_name(self):
        """
        Tests the --source-name option.

        Checks that the --source-name option correctly updates the
        ref structure that is passed in the HTTP POST
        """
        self.run_command('manage host1 VolName '
                         '--name foo --description bar '
                         '--volume-type baz --availability-zone az '
                         '--metadata k1=v1 k2=v2')
        expected = {'volume': {'host': 'host1',
                               'ref': {'source-name': 'VolName'},
                               'name': 'foo',
                               'description': 'bar',
                               'volume_type': 'baz',
                               'availability_zone': 'az',
                               'metadata': {'k1': 'v1', 'k2': 'v2'},
                               'bootable': False}}
        self.assert_called_anytime('POST', '/os-volume-manage', body=expected)

    def test_volume_manage_source_id(self):
        """
        Tests the --source-id option.

        Checks that the --source-id option correctly updates the
        ref structure that is passed in the HTTP POST
        """
        self.run_command('manage host1 1234 '
                         '--id-type source-id '
                         '--name foo --description bar '
                         '--volume-type baz --availability-zone az '
                         '--metadata k1=v1 k2=v2')
        expected = {'volume': {'host': 'host1',
                               'ref': {'source-id': '1234'},
                               'name': 'foo',
                               'description': 'bar',
                               'volume_type': 'baz',
                               'availability_zone': 'az',
                               'metadata': {'k1': 'v1', 'k2': 'v2'},
                               'bootable': False}}
        self.assert_called_anytime('POST', '/os-volume-manage', body=expected)

    def test_volume_manageable_list(self):
        self.run_command('manageable-list fakehost')
        self.assert_called('GET', '/os-volume-manage/detail?host=fakehost')

    def test_volume_manageable_list_details(self):
        self.run_command('manageable-list fakehost --detailed True')
        self.assert_called('GET', '/os-volume-manage/detail?host=fakehost')

    def test_volume_manageable_list_no_details(self):
        self.run_command('manageable-list fakehost --detailed False')
        self.assert_called('GET', '/os-volume-manage?host=fakehost')

    def test_volume_unmanage(self):
        self.run_command('unmanage 1234')
        self.assert_called('POST', '/volumes/1234/action',
                           body={'os-unmanage': None})

    def test_create_snapshot_from_volume_with_metadata(self):
        """
        Tests create snapshot with --metadata parameter.

        Checks metadata params are set during create snapshot
        when metadata is passed
        """
        expected = {'snapshot': {'volume_id': 1234,
                                 'metadata': {'k1': 'v1',
                                              'k2': 'v2'}}}
        self.run_command('snapshot-create 1234 --metadata k1=v1 k2=v2 '
                         '--force=True')
        self.assert_called_anytime('POST', '/snapshots', partial_body=expected)

    def test_create_snapshot_from_volume_with_metadata_bool_force(self):
        """
        Tests create snapshot with --metadata parameter.

        Checks metadata params are set during create snapshot
        when metadata is passed
        """
        expected = {'snapshot': {'volume_id': 1234,
                                 'metadata': {'k1': 'v1',
                                              'k2': 'v2'}}}
        self.run_command('snapshot-create 1234 --metadata k1=v1 k2=v2 --force')
        self.assert_called_anytime('POST', '/snapshots', partial_body=expected)

    def test_get_pools(self):
        self.run_command('get-pools')
        self.assert_called('GET', '/scheduler-stats/get_pools')

    def test_get_pools_detail(self):
        self.run_command('get-pools --detail')
        self.assert_called('GET', '/scheduler-stats/get_pools?detail=True')

    def test_list_transfer(self):
        self.run_command('transfer-list')
        self.assert_called('GET', '/os-volume-transfer/detail?all_tenants=0')

    def test_list_transfer_all_tenants(self):
        self.run_command('transfer-list --all-tenants=1')
        self.assert_called('GET', '/os-volume-transfer/detail?all_tenants=1')

    def test_consistencygroup_update(self):
        self.run_command('consisgroup-update '
                         '--name cg2 --description desc2 '
                         '--add-volumes uuid1,uuid2 '
                         '--remove-volumes uuid3,uuid4 '
                         '1234')
        expected = {'consistencygroup': {'name': 'cg2',
                                         'description': 'desc2',
                                         'add_volumes': 'uuid1,uuid2',
                                         'remove_volumes': 'uuid3,uuid4'}}
        self.assert_called('PUT', '/consistencygroups/1234',
                           body=expected)

    def test_consistencygroup_update_invalid_args(self):
        self.assertRaises(exceptions.ClientException,
                          self.run_command,
                          'consisgroup-update 1234')

    def test_consistencygroup_create_from_src_snap(self):
        self.run_command('consisgroup-create-from-src '
                         '--name cg '
                         '--cgsnapshot 1234')
        expected = {
            'consistencygroup-from-src': {
                'name': 'cg',
                'cgsnapshot_id': '1234',
                'description': None,
                'user_id': None,
                'project_id': None,
                'status': 'creating',
                'source_cgid': None
            }
        }
        self.assert_called('POST', '/consistencygroups/create_from_src',
                           expected)

    def test_consistencygroup_create_from_src_cg(self):
        self.run_command('consisgroup-create-from-src '
                         '--name cg '
                         '--source-cg 1234')
        expected = {
            'consistencygroup-from-src': {
                'name': 'cg',
                'cgsnapshot_id': None,
                'description': None,
                'user_id': None,
                'project_id': None,
                'status': 'creating',
                'source_cgid': '1234'
            }
        }
        self.assert_called('POST', '/consistencygroups/create_from_src',
                           expected)

    def test_consistencygroup_create_from_src_fail_no_snap_cg(self):
        self.assertRaises(exceptions.ClientException,
                          self.run_command,
                          'consisgroup-create-from-src '
                          '--name cg')

    def test_consistencygroup_create_from_src_fail_both_snap_cg(self):
        self.assertRaises(exceptions.ClientException,
                          self.run_command,
                          'consisgroup-create-from-src '
                          '--name cg '
                          '--cgsnapshot 1234 '
                          '--source-cg 5678')

    def test_set_image_metadata(self):
        self.run_command('image-metadata 1234 set key1=val1')
        expected = {"os-set_image_metadata": {"metadata": {"key1": "val1"}}}
        self.assert_called('POST', '/volumes/1234/action',
                           body=expected)

    def test_unset_image_metadata(self):
        self.run_command('image-metadata 1234 unset key1')
        expected = {"os-unset_image_metadata": {"key": "key1"}}
        self.assert_called('POST', '/volumes/1234/action',
                           body=expected)

    def _get_params_from_stack(self, pos=-1):
        method, url = self.shell.cs.client.callstack[pos][0:2]
        path, query = parse.splitquery(url)
        params = parse.parse_qs(query)
        return path, params

    def test_backup_list_all_tenants(self):
        self.run_command('backup-list --all-tenants=1 --name=bc '
                         '--status=available --volume-id=1234')
        expected = {
            'all_tenants': ['1'],
            'name': ['bc'],
            'status': ['available'],
            'volume_id': ['1234'],
        }

        path, params = self._get_params_from_stack()

        self.assertEqual('/backups/detail', path)
        self.assertEqual(4, len(params))

        for k in params.keys():
            self.assertEqual(expected[k], params[k])

    def test_backup_list_volume_id(self):
        self.run_command('backup-list --volume-id=1234')
        self.assert_called('GET', '/backups/detail?volume_id=1234')

    def test_backup_list(self):
        self.run_command('backup-list')
        self.assert_called('GET', '/backups/detail')

    @mock.patch("cinderclient.utils.print_list")
    def test_backup_list_sort(self, mock_print_list):
        self.run_command('backup-list --sort id')
        self.assert_called('GET', '/backups/detail?sort=id')
        columns = ['ID', 'Volume ID', 'Status', 'Name', 'Size', 'Object Count',
               'Container']
        mock_print_list.assert_called_once_with(mock.ANY, columns,
            sortby_index=None)

    def test_backup_list_data_timestamp(self):
        self.run_command('backup-list --sort data_timestamp')
        self.assert_called('GET', '/backups/detail?sort=data_timestamp')

    def test_get_capabilities(self):
        self.run_command('get-capabilities host')
        self.assert_called('GET', '/capabilities/host')

    def test_image_metadata_show(self):
        # since the request is not actually sent to cinder API but is
        # calling the method in :class:`v2.fakes.FakeHTTPClient` instead.
        # Thus, ignore any exception which is false negative compare
        # with real API call.
        try:
            self.run_command('image-metadata-show 1234')
        except Exception:
            pass
        expected = {"os-show_image_metadata": None}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_snapshot_manage(self):
        self.run_command('snapshot-manage 1234 some_fake_name '
                         '--name foo --description bar '
                         '--metadata k1=v1 k2=v2')
        expected = {'snapshot': {'volume_id': 1234,
                                 'ref': {'source-name': 'some_fake_name'},
                                 'name': 'foo',
                                 'description': 'bar',
                                 'metadata': {'k1': 'v1', 'k2': 'v2'}
                                 }}
        self.assert_called_anytime('POST', '/os-snapshot-manage',
                                   body=expected)

    def test_snapshot_manageable_list(self):
        self.run_command('snapshot-manageable-list fakehost')
        self.assert_called('GET', '/os-snapshot-manage/detail?host=fakehost')

    def test_snapshot_manageable_list_details(self):
        self.run_command('snapshot-manageable-list fakehost --detailed True')
        self.assert_called('GET', '/os-snapshot-manage/detail?host=fakehost')

    def test_snapshot_manageable_list_no_details(self):
        self.run_command('snapshot-manageable-list fakehost --detailed False')
        self.assert_called('GET', '/os-snapshot-manage?host=fakehost')

    def test_snapshot_unmanage(self):
        self.run_command('snapshot-unmanage 1234')
        self.assert_called('POST', '/snapshots/1234/action',
                           body={'os-unmanage': None})

    def test_extra_specs_list(self):
        self.run_command('extra-specs-list')
        self.assert_called('GET', '/types?is_public=None')

    def test_quota_class_show(self):
        self.run_command('quota-class-show test')
        self.assert_called('GET', '/os-quota-class-sets/test')

    def test_quota_class_update(self):
        expected = {'quota_class_set': {'volumes': 2,
                                        'snapshots': 2,
                                        'gigabytes': 1,
                                        'backups': 1,
                                        'backup_gigabytes': 1,
                                        'per_volume_gigabytes': 1}}
        self.run_command('quota-class-update test '
                         '--volumes 2 '
                         '--snapshots 2 '
                         '--gigabytes 1 '
                         '--backups 1 '
                         '--backup-gigabytes 1 '
                         '--per-volume-gigabytes 1')
        self.assert_called('PUT', '/os-quota-class-sets/test', body=expected)

    def test_translate_attachments(self):
        attachment_id = 'aaaa'
        server_id = 'bbbb'
        obj_id = 'cccc'
        info = {
            'attachments': [{
                'attachment_id': attachment_id,
                'id': obj_id,
                'server_id': server_id}]
            }

        new_info = test_shell._translate_attachments(info)

        self.assertEqual(attachment_id, new_info['attachment_ids'][0])
        self.assertEqual(server_id, new_info['attached_servers'][0])
        self.assertNotIn('id', new_info)
