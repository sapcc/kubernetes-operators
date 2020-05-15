# -*- coding: utf-8 -*-
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


# NOTE(geguileo): For v3 we cannot mock any of the following methods
#   - utils.find_volume
#   - shell_utils.find_backup
#   - shell_utils.find_volume_snapshot
#   - shell_utils.find_group
#   - shell_utils.find_group_snapshot
# because we are caching them in cinderclient.v3.shell:RESET_STATE_RESOURCES
# which means that our tests could fail depending on the mocking and loading
# order.
#
# Alternatives are:
#   - Mock utils.find_resource when we have only 1 call to that method
#   - Use an auxiliary method that will call original method for irrelevant
#     calls.  Example from test_revert_to_snapshot:
#         original = client_utils.find_resource
#
#         def find_resource(manager, name_or_id, **kwargs):
#             if isinstance(manager, volume_snapshots.SnapshotManager):
#                 return volume_snapshots.Snapshot(self,
#                                                  {'id': '5678',
#                                                   'volume_id': '1234'})
#             return original(manager, name_or_id, **kwargs)

import ddt
import fixtures
import mock
from requests_mock.contrib import fixture as requests_mock_fixture
import six
from six.moves.urllib import parse

import cinderclient
from cinderclient import api_versions
from cinderclient import base
from cinderclient import client
from cinderclient import exceptions
from cinderclient import shell
from cinderclient import utils as cinderclient_utils
from cinderclient.v3 import attachments
from cinderclient.v3 import volume_snapshots
from cinderclient.v3 import volumes

from cinderclient.tests.unit.fixture_data import keystone_client
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes


@ddt.ddt
@mock.patch.object(client, 'Client', fakes.FakeClient)
class ShellTest(utils.TestCase):

    FAKE_ENV = {
        'CINDER_USERNAME': 'username',
        'CINDER_PASSWORD': 'password',
        'CINDER_PROJECT_ID': 'project_id',
        'OS_VOLUME_API_VERSION': '3',
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

    def run_command(self, cmd):
        # Ensure the version negotiation indicates that
        # all versions are supported
        with mock.patch('cinderclient.api_versions._get_server_version_range',
                return_value=(api_versions.APIVersion('3.0'),
                              api_versions.APIVersion('3.99'))):
            self.shell.main(cmd.split())

    def assert_called(self, method, url, body=None,
                      partial_body=None, **kwargs):
        return self.shell.cs.assert_called(method, url, body,
                                           partial_body, **kwargs)

    def assert_call_contained(self, url_part):
        self.shell.cs.assert_in_call(url_part)

    @ddt.data({'resource': None, 'query_url': None},
              {'resource': 'volume', 'query_url': '?resource=volume'},
              {'resource': 'group', 'query_url': '?resource=group'})
    @ddt.unpack
    def test_list_filters(self, resource, query_url):
        url = '/resource_filters'
        if resource is not None:
            url += query_url
            self.run_command('--os-volume-api-version 3.33 '
                             'list-filters --resource=%s' % resource)
        else:
            self.run_command('--os-volume-api-version 3.33 list-filters')

        self.assert_called('GET', url)

    @ddt.data(
        # testcases for list volume
        {'command':
            'list --name=123 --filters name=456',
         'expected':
             '/volumes/detail?name=456'},
        {'command':
             'list --filters name=123',
         'expected':
             '/volumes/detail?name=123'},
        {'command':
             'list --filters metadata={key1:value1}',
         'expected':
             '/volumes/detail?metadata=%7B%27key1%27%3A+%27value1%27%7D'},
        {'command':
             'list --filters name~=456',
         'expected':
             '/volumes/detail?name~=456'},
        {'command':
             u'list --filters name~=Σ',
         'expected':
             '/volumes/detail?name~=%CE%A3'},
        {'command':
             u'list --filters name=abc --filters size=1',
         'expected':
             '/volumes/detail?name=abc&size=1'},
        # testcases for list group
        {'command':
             'group-list --filters name=456',
         'expected':
             '/groups/detail?name=456'},
        {'command':
             'group-list --filters status=available',
         'expected':
             '/groups/detail?status=available'},
        {'command':
             'group-list --filters name~=456',
         'expected':
             '/groups/detail?name~=456'},
        {'command':
             'group-list --filters name=abc --filters status=available',
         'expected':
             '/groups/detail?name=abc&status=available'},
        # testcases for list group-snapshot
        {'command':
             'group-snapshot-list --status=error --filters status=available',
         'expected':
             '/group_snapshots/detail?status=available'},
        {'command':
             'group-snapshot-list --filters availability_zone=123',
         'expected':
             '/group_snapshots/detail?availability_zone=123'},
        {'command':
             'group-snapshot-list --filters status~=available',
         'expected':
             '/group_snapshots/detail?status~=available'},
        {'command':
             'group-snapshot-list --filters status=available '
             '--filters availability_zone=123',
         'expected':
             '/group_snapshots/detail?availability_zone=123&status=available'},
        # testcases for list message
        {'command':
             'message-list --event_id=123 --filters event_id=456',
         'expected':
             '/messages?event_id=456'},
        {'command':
             'message-list --filters request_id=123',
         'expected':
             '/messages?request_id=123'},
        {'command':
             'message-list --filters request_id~=123',
         'expected':
             '/messages?request_id~=123'},
        {'command':
             'message-list --filters request_id=123 --filters event_id=456',
         'expected':
             '/messages?event_id=456&request_id=123'},
        # testcases for list attachment
        {'command':
             'attachment-list --volume-id=123 --filters volume_id=456',
         'expected':
             '/attachments?volume_id=456'},
        {'command':
             'attachment-list --filters mountpoint=123',
         'expected':
             '/attachments?mountpoint=123'},
        {'command':
             'attachment-list --filters volume_id~=456',
         'expected':
             '/attachments?volume_id~=456'},
        {'command':
             'attachment-list --filters volume_id=123 '
             '--filters mountpoint=456',
         'expected':
             '/attachments?mountpoint=456&volume_id=123'},
        # testcases for list backup
        {'command':
             'backup-list --volume-id=123 --filters volume_id=456',
         'expected':
             '/backups/detail?volume_id=456'},
        {'command':
             'backup-list --filters name=123',
         'expected':
             '/backups/detail?name=123'},
        {'command':
             'backup-list --filters volume_id~=456',
         'expected':
             '/backups/detail?volume_id~=456'},
        {'command':
             'backup-list --filters volume_id=123 --filters name=456',
         'expected':
             '/backups/detail?name=456&volume_id=123'},
        # testcases for list snapshot
        {'command':
             'snapshot-list --volume-id=123 --filters volume_id=456',
         'expected':
             '/snapshots/detail?volume_id=456'},
        {'command':
             'snapshot-list --filters name=123',
         'expected':
             '/snapshots/detail?name=123'},
        {'command':
             'snapshot-list --filters volume_id~=456',
         'expected':
             '/snapshots/detail?volume_id~=456'},
        {'command':
             'snapshot-list --filters volume_id=123 --filters name=456',
         'expected':
             '/snapshots/detail?name=456&volume_id=123'},
        # testcases for get pools
        {'command':
             'get-pools --filters name=456 --detail',
         'expected':
             '/scheduler-stats/get_pools?detail=True&name=456'},
        {'command':
             'get-pools --filters name=456',
         'expected':
             '/scheduler-stats/get_pools?name=456'},
        {'command':
             'get-pools --filters name=456 --filters detail=True',
         'expected':
             '/scheduler-stats/get_pools?detail=True&name=456'}
    )
    @ddt.unpack
    def test_list_with_filters_mixed(self, command, expected):
        self.run_command('--os-volume-api-version 3.33 %s' % command)
        self.assert_called('GET', expected)

    def test_list(self):
        self.run_command('list')
        # NOTE(jdg): we default to detail currently
        self.assert_called('GET', '/volumes/detail')

    def test_list_with_with_count(self):
        self.run_command('--os-volume-api-version 3.45 list --with-count')
        self.assert_called('GET', '/volumes/detail?with_count=True')

    def test_summary(self):
        self.run_command('--os-volume-api-version 3.12 summary')
        self.assert_called('GET', '/volumes/summary')

    def test_list_with_group_id_before_3_10(self):
        self.assertRaises(exceptions.UnsupportedAttribute,
                          self.run_command,
                          'list --group_id fake_id')

    def test_type_list_with_filters_invalid(self):
        self.assertRaises(exceptions.UnsupportedAttribute,
                          self.run_command,
                          '--os-volume-api-version 3.51 type-list '
                          '--filters key=value')

    def test_type_list_with_filters(self):
        self.run_command('--os-volume-api-version 3.52 type-list '
                         '--filters extra_specs={key:value}')
        self.assert_called('GET', mock.ANY)
        self.assert_call_contained(
            parse.urlencode(
                {'extra_specs':
                    {six.text_type('key'): six.text_type('value')}}))
        self.assert_call_contained(parse.urlencode({'is_public': None}))

    def test_type_list_public(self):
        self.run_command('--os-volume-api-version 3.52 type-list '
                         '--filters is_public=True')
        self.assert_called('GET', '/types?is_public=True')

    def test_type_list_private(self):
        self.run_command('--os-volume-api-version 3.52 type-list '
                         '--filters is_public=False')
        self.assert_called('GET', '/types?is_public=False')

    def test_type_list_public_private(self):
        self.run_command('--os-volume-api-version 3.52 type-list')
        self.assert_called('GET', '/types?is_public=None')

    @ddt.data("3.10", "3.11")
    def test_list_with_group_id_after_3_10(self, version):
        command = ('--os-volume-api-version %s list --group_id fake_id' %
                   version)
        self.run_command(command)
        self.assert_called('GET', '/volumes/detail?group_id=fake_id')

    @mock.patch("cinderclient.utils.print_list")
    def test_list_duplicate_fields(self, mock_print):
        self.run_command('list --field Status,id,Size,status')
        self.assert_called('GET', '/volumes/detail')
        key_list = ['ID', 'Status', 'Size']
        mock_print.assert_called_once_with(mock.ANY, key_list,
            exclude_unavailable=True, sortby_index=0)

    @mock.patch("cinderclient.shell.OpenStackCinderShell.downgrade_warning")
    def test_list_version_downgrade(self, mock_warning):
        self.run_command('--os-volume-api-version 3.998 list')
        mock_warning.assert_called_once_with(
            api_versions.APIVersion('3.998'),
            api_versions.APIVersion(api_versions.MAX_VERSION)
        )

    def test_list_availability_zone(self):
        self.run_command('availability-zone-list')
        self.assert_called('GET', '/os-availability-zone')

    @ddt.data({'cmd': '1234 1233',
               'body': {'instance_uuid': '1233',
                        'connector': {},
                        'volume_uuid': '1234'}},
              {'cmd': '1234 1233 '
                      '--connect True '
                      '--ip 10.23.12.23 --host server01 '
                      '--platform x86_xx '
                      '--ostype 123 '
                      '--multipath true '
                      '--mountpoint /123 '
                      '--initiator aabbccdd',
               'body': {'instance_uuid': '1233',
                        'connector': {'ip': '10.23.12.23',
                                      'host': 'server01',
                                      'os_type': '123',
                                      'multipath': 'true',
                                      'mountpoint': '/123',
                                      'initiator': 'aabbccdd',
                                      'platform': 'x86_xx'},
                        'volume_uuid': '1234'}},
              {'cmd': 'abc 1233',
               'body': {'instance_uuid': '1233',
                        'connector': {},
                        'volume_uuid': '1234'}})
    @mock.patch('cinderclient.utils.find_resource')
    @ddt.unpack
    def test_attachment_create(self, mock_find_volume, cmd, body):
        mock_find_volume.return_value = volumes.Volume(self,
                                                       {'id': '1234'},
                                                       loaded=True)
        command = '--os-volume-api-version 3.27 attachment-create '
        command += cmd
        self.run_command(command)
        expected = {'attachment': body}
        self.assertTrue(mock_find_volume.called)
        self.assert_called('POST', '/attachments', body=expected)

    @ddt.data({'cmd': '1234 1233',
               'body': {'instance_uuid': '1233',
                        'connector': {},
                        'volume_uuid': '1234',
                        'mode': 'ro'}},
              {'cmd': '1234 1233 '
                      '--connect True '
                      '--ip 10.23.12.23 --host server01 '
                      '--platform x86_xx '
                      '--ostype 123 '
                      '--multipath true '
                      '--mountpoint /123 '
                      '--initiator aabbccdd',
               'body': {'instance_uuid': '1233',
                        'connector': {'ip': '10.23.12.23',
                                      'host': 'server01',
                                      'os_type': '123',
                                      'multipath': 'true',
                                      'mountpoint': '/123',
                                      'initiator': 'aabbccdd',
                                      'platform': 'x86_xx'},
                        'volume_uuid': '1234',
                        'mode': 'ro'}},
              {'cmd': 'abc 1233',
               'body': {'instance_uuid': '1233',
                        'connector': {},
                        'volume_uuid': '1234',
                        'mode': 'ro'}})
    @mock.patch('cinderclient.utils.find_resource')
    @ddt.unpack
    def test_attachment_create_with_mode(self, mock_find_volume, cmd, body):
        mock_find_volume.return_value = volumes.Volume(self,
                                                       {'id': '1234'},
                                                       loaded=True)
        command = ('--os-volume-api-version 3.54 '
                   'attachment-create '
                   '--mode ro ')
        command += cmd
        self.run_command(command)
        expected = {'attachment': body}
        self.assertTrue(mock_find_volume.called)
        self.assert_called('POST', '/attachments', body=expected)

    @mock.patch.object(volumes.VolumeManager, 'findall')
    def test_attachment_create_duplicate_name_vol(self, mock_findall):
        found = [volumes.Volume(self, {'id': '7654', 'name': 'abc'},
                                loaded=True),
                 volumes.Volume(self, {'id': '9876', 'name': 'abc'},
                                loaded=True)]
        mock_findall.return_value = found
        self.assertRaises(exceptions.CommandError,
                          self.run_command,
                          '--os-volume-api-version 3.27 '
                          'attachment-create abc 789')

    @ddt.data({'cmd': '',
               'expected': ''},
              {'cmd': '--volume-id 1234',
               'expected': '?volume_id=1234'},
              {'cmd': '--status error',
               'expected': '?status=error'},
              {'cmd': '--all-tenants 1',
               'expected': '?all_tenants=1'},
              {'cmd': '--all-tenants 1 --volume-id 12345',
               'expected': '?all_tenants=1&volume_id=12345'},
              {'cmd': '--all-tenants 1 --tenant 12345',
               'expected': '?all_tenants=1&project_id=12345'},
              {'cmd': '--tenant 12345',
               'expected': '?all_tenants=1&project_id=12345'}

              )
    @ddt.unpack
    def test_attachment_list(self, cmd, expected):
        command = '--os-volume-api-version 3.27 attachment-list '
        command += cmd
        self.run_command(command)
        self.assert_called('GET', '/attachments%s' % expected)

    @mock.patch('cinderclient.utils.print_list')
    @mock.patch.object(cinderclient.v3.attachments.VolumeAttachmentManager,
            'list')
    def test_attachment_list_setattr(self, mock_list, mock_print):
        command = '--os-volume-api-version 3.27 attachment-list '
        fake_attachment = [attachments.VolumeAttachment(mock.ANY, attachment)
                for attachment in fakes.fake_attachment_list['attachments']]
        mock_list.return_value = fake_attachment
        self.run_command(command)
        for attach in fake_attachment:
            setattr(attach, 'server_id', getattr(attach, 'instance'))
        columns = ['ID', 'Volume ID', 'Status', 'Server ID']
        mock_print.assert_called_once_with(fake_attachment, columns,
                sortby_index=0)

    def test_revert_to_snapshot(self):
        original = cinderclient_utils.find_resource

        def find_resource(manager, name_or_id, **kwargs):
            if isinstance(manager, volume_snapshots.SnapshotManager):
                return volume_snapshots.Snapshot(self,
                                                 {'id': '5678',
                                                  'volume_id': '1234'})
            return original(manager, name_or_id, **kwargs)

        with mock.patch('cinderclient.utils.find_resource',
                        side_effect=find_resource):
            self.run_command(
                '--os-volume-api-version 3.40 revert-to-snapshot 5678')

        self.assert_called('POST', '/volumes/1234/action',
                           body={'revert': {'snapshot_id': '5678'}})

    def test_attachment_show(self):
        self.run_command('--os-volume-api-version 3.27 attachment-show 1234')
        self.assert_called('GET', '/attachments/1234')

    @ddt.data({'cmd': '1234 '
                      '--ip 10.23.12.23 --host server01 '
                      '--platform x86_xx '
                      '--ostype 123 '
                      '--multipath true '
                      '--mountpoint /123 '
                      '--initiator aabbccdd',
               'body': {'connector': {'ip': '10.23.12.23',
                                      'host': 'server01',
                                      'os_type': '123',
                                      'multipath': 'true',
                                      'mountpoint': '/123',
                                      'initiator': 'aabbccdd',
                                      'platform': 'x86_xx'}}})
    @ddt.unpack
    def test_attachment_update(self, cmd, body):
        command = '--os-volume-api-version 3.27 attachment-update '
        command += cmd
        self.run_command(command)
        self.assert_called('PUT', '/attachments/1234', body={'attachment':
                                                             body})

    @ddt.unpack
    def test_attachment_complete(self):
        command = '--os-volume-api-version 3.44 attachment-complete 1234'
        self.run_command(command)
        self.assert_called('POST', '/attachments/1234/action', body=None)

    def test_attachment_delete(self):
        self.run_command('--os-volume-api-version 3.27 '
                         'attachment-delete 1234')
        self.assert_called('DELETE', '/attachments/1234')

    def test_upload_to_image(self):
        expected = {'os-volume_upload_image': {'force': False,
                                               'container_format': 'bare',
                                               'disk_format': 'raw',
                                               'image_name': 'test-image'}}
        self.run_command('upload-to-image 1234 test-image')
        self.assert_called_anytime('GET', '/volumes/1234')
        self.assert_called_anytime('POST', '/volumes/1234/action',
                                   body=expected)

    def test_upload_to_image_private_not_protected(self):
        expected = {'os-volume_upload_image': {'force': False,
                                               'container_format': 'bare',
                                               'disk_format': 'raw',
                                               'image_name': 'test-image',
                                               'protected': False,
                                               'visibility': 'private'}}
        self.run_command('--os-volume-api-version 3.1 '
                         'upload-to-image 1234 test-image')
        self.assert_called_anytime('GET', '/volumes/1234')
        self.assert_called_anytime('POST', '/volumes/1234/action',
                                   body=expected)

    def test_upload_to_image_public_protected(self):
        expected = {'os-volume_upload_image': {'force': False,
                                               'container_format': 'bare',
                                               'disk_format': 'raw',
                                               'image_name': 'test-image',
                                               'protected': 'True',
                                               'visibility': 'public'}}
        self.run_command('--os-volume-api-version 3.1 '
                         'upload-to-image --visibility=public '
                         '--protected=True 1234 test-image')
        self.assert_called_anytime('GET', '/volumes/1234')
        self.assert_called_anytime('POST', '/volumes/1234/action',
                                   body=expected)

    def test_backup_update(self):
        self.run_command('--os-volume-api-version 3.9 '
                         'backup-update --name new_name 1234')
        expected = {'backup': {'name': 'new_name'}}
        self.assert_called('PUT', '/backups/1234', body=expected)

    def test_backup_list_with_with_count(self):
        self.run_command(
            '--os-volume-api-version 3.45 backup-list --with-count')
        self.assert_called('GET', '/backups/detail?with_count=True')

    def test_backup_update_with_description(self):
        self.run_command('--os-volume-api-version 3.9 '
                         'backup-update 1234 --description=new-description')
        expected = {'backup': {'description': 'new-description'}}
        self.assert_called('PUT', '/backups/1234', body=expected)

    def test_backup_update_with_metadata(self):
        cmd = '--os-volume-api-version 3.43 '
        cmd += 'backup-update '
        cmd += '--metadata foo=bar '
        cmd += '1234'
        self.run_command(cmd)
        expected = {'backup': {'metadata': {'foo': 'bar'}}}
        self.assert_called('PUT', '/backups/1234', body=expected)

    def test_backup_update_all(self):
        # rename and change description
        self.run_command('--os-volume-api-version 3.43 '
                         'backup-update --name new-name '
                         '--description=new-description '
                         '--metadata foo=bar 1234')
        expected = {'backup': {
            'name': 'new-name',
            'description': 'new-description',
            'metadata': {'foo': 'bar'}
        }}
        self.assert_called('PUT', '/backups/1234', body=expected)

    def test_backup_update_without_arguments(self):
        # Call rename with no arguments
        self.assertRaises(SystemExit, self.run_command,
                          '--os-volume-api-version 3.9 backup-update')

    def test_backup_update_bad_request(self):
        self.assertRaises(exceptions.ClientException,
                          self.run_command,
                          '--os-volume-api-version 3.9 backup-update 1234')

    def test_backup_update_wrong_version(self):
        self.assertRaises(SystemExit,
                          self.run_command,
                          '--os-volume-api-version 3.8 '
                          'backup-update --name new-name 1234')

    def test_group_type_list(self):
        self.run_command('--os-volume-api-version 3.11 group-type-list')
        self.assert_called_anytime('GET', '/group_types?is_public=None')

    def test_group_type_list_public(self):
        self.run_command('--os-volume-api-version 3.52 group-type-list '
                         '--filters is_public=True')
        self.assert_called('GET', '/group_types?is_public=True')

    def test_group_type_list_private(self):
        self.run_command('--os-volume-api-version 3.52 group-type-list '
                         '--filters is_public=False')
        self.assert_called('GET', '/group_types?is_public=False')

    def test_group_type_list_public_private(self):
        self.run_command('--os-volume-api-version 3.52 group-type-list')
        self.assert_called('GET', '/group_types?is_public=None')

    def test_group_type_show(self):
        self.run_command('--os-volume-api-version 3.11 '
                         'group-type-show 1')
        self.assert_called('GET', '/group_types/1')

    def test_group_type_create(self):
        self.run_command('--os-volume-api-version 3.11 '
                         'group-type-create test-type-1')
        self.assert_called('POST', '/group_types')

    def test_group_type_create_public(self):
        expected = {'group_type': {'name': 'test-type-1',
                                   'description': 'test_type-1-desc',
                                   'is_public': True}}
        self.run_command('--os-volume-api-version 3.11 '
                         'group-type-create test-type-1 '
                         '--description=test_type-1-desc '
                         '--is-public=True')
        self.assert_called('POST', '/group_types', body=expected)

    def test_group_type_create_private(self):
        expected = {'group_type': {'name': 'test-type-3',
                                   'description': 'test_type-3-desc',
                                   'is_public': False}}
        self.run_command('--os-volume-api-version 3.11 '
                         'group-type-create test-type-3 '
                         '--description=test_type-3-desc '
                         '--is-public=False')
        self.assert_called('POST', '/group_types', body=expected)

    def test_group_specs_list(self):
        self.run_command('--os-volume-api-version 3.11 group-specs-list')
        self.assert_called('GET', '/group_types?is_public=None')

    def test_create_volume_with_group(self):
        self.run_command('--os-volume-api-version 3.13 create --group-id 5678 '
                         '--volume-type 4321 1')
        self.assert_called('GET', '/volumes/1234')
        expected = {'volume': {'imageRef': None,
                               'size': 1,
                               'availability_zone': None,
                               'source_volid': None,
                               'consistencygroup_id': None,
                               'group_id': '5678',
                               'name': None,
                               'snapshot_id': None,
                               'metadata': {},
                               'volume_type': '4321',
                               'description': None,
                               'backup_id': None}}
        self.assert_called_anytime('POST', '/volumes', expected)

    @ddt.data({'cmd': '--os-volume-api-version 3.47 create --backup-id 1234',
               'update': {'backup_id': '1234'}},
              {'cmd': '--os-volume-api-version 3.47 create 2',
               'update': {'size': 2}}
              )
    @ddt.unpack
    def test_create_volume_with_backup(self, cmd, update):
        self.run_command(cmd)
        self.assert_called('GET', '/volumes/1234')
        expected = {'volume': {'imageRef': None,
                               'size': None,
                               'availability_zone': None,
                               'source_volid': None,
                               'consistencygroup_id': None,
                               'name': None,
                               'snapshot_id': None,
                               'metadata': {},
                               'volume_type': None,
                               'description': None,
                               'backup_id': None}}
        expected['volume'].update(update)
        self.assert_called_anytime('POST', '/volumes', body=expected)

    def test_group_list(self):
        self.run_command('--os-volume-api-version 3.13 group-list')
        self.assert_called_anytime('GET', '/groups/detail')

    def test_group_list__with_all_tenant(self):
        self.run_command(
            '--os-volume-api-version 3.13 group-list --all-tenants')
        self.assert_called_anytime('GET', '/groups/detail?all_tenants=1')

    def test_group_show(self):
        self.run_command('--os-volume-api-version 3.13 '
                         'group-show 1234')
        self.assert_called('GET', '/groups/1234')

    def test_group_show_with_list_volume(self):
        self.run_command('--os-volume-api-version 3.25 '
                         'group-show 1234 --list-volume')
        self.assert_called('GET', '/groups/1234?list_volume=True')

    @ddt.data(True, False)
    def test_group_delete(self, delete_vol):
        cmd = '--os-volume-api-version 3.13 group-delete 1234'
        if delete_vol:
            cmd += ' --delete-volumes'
        self.run_command(cmd)
        expected = {'delete': {'delete-volumes': delete_vol}}
        self.assert_called('POST', '/groups/1234/action', expected)

    def test_group_create(self):
        expected = {'group': {'name': 'test-1',
                              'description': 'test-1-desc',
                              'group_type': 'my_group_type',
                              'volume_types': ['type1', 'type2'],
                              'availability_zone': 'zone1'}}
        self.run_command('--os-volume-api-version 3.13 '
                         'group-create --name test-1 '
                         '--description test-1-desc '
                         '--availability-zone zone1 '
                         'my_group_type type1,type2')
        self.assert_called_anytime('POST', '/groups', body=expected)

    def test_group_update(self):
        self.run_command('--os-volume-api-version 3.13 group-update '
                         '--name group2 --description desc2 '
                         '--add-volumes uuid1,uuid2 '
                         '--remove-volumes uuid3,uuid4 '
                         '1234')
        expected = {'group': {'name': 'group2',
                              'description': 'desc2',
                              'add_volumes': 'uuid1,uuid2',
                              'remove_volumes': 'uuid3,uuid4'}}
        self.assert_called('PUT', '/groups/1234',
                           body=expected)

    def test_group_update_invalid_args(self):
        self.assertRaises(exceptions.ClientException,
                          self.run_command,
                          '--os-volume-api-version 3.13 group-update 1234')

    def test_group_snapshot_list(self):
        self.run_command('--os-volume-api-version 3.14 group-snapshot-list')
        self.assert_called_anytime('GET',
                                   '/group_snapshots/detail')

    def test_group_snapshot_show(self):
        self.run_command('--os-volume-api-version 3.14 '
                         'group-snapshot-show 1234')
        self.assert_called('GET', '/group_snapshots/1234')

    def test_group_snapshot_delete(self):
        cmd = '--os-volume-api-version 3.14 group-snapshot-delete 1234'
        self.run_command(cmd)
        self.assert_called('DELETE', '/group_snapshots/1234')

    def test_group_snapshot_create(self):
        expected = {'group_snapshot': {'name': 'test-1',
                                       'description': 'test-1-desc',
                                       'group_id': '1234'}}
        self.run_command('--os-volume-api-version 3.14 '
                         'group-snapshot-create --name test-1 '
                         '--description test-1-desc 1234')
        self.assert_called_anytime('POST', '/group_snapshots', body=expected)

    @ddt.data(
        {'grp_snap_id': '1234', 'src_grp_id': None,
         'src': '--group-snapshot 1234'},
        {'grp_snap_id': None, 'src_grp_id': '1234',
         'src': '--source-group 1234'},
    )
    @ddt.unpack
    def test_group_create_from_src(self, grp_snap_id, src_grp_id, src):
        expected = {'create-from-src': {'name': 'test-1',
                                        'description': 'test-1-desc'}}
        if grp_snap_id:
            expected['create-from-src']['group_snapshot_id'] = grp_snap_id
        elif src_grp_id:
            expected['create-from-src']['source_group_id'] = src_grp_id

        cmd = ('--os-volume-api-version 3.14 '
               'group-create-from-src --name test-1 '
               '--description test-1-desc ')
        cmd += src
        self.run_command(cmd)
        self.assert_called_anytime('POST', '/groups/action', body=expected)

    def test_volume_manageable_list(self):
        self.run_command('--os-volume-api-version 3.8 '
                         'manageable-list fakehost')
        self.assert_called('GET', '/manageable_volumes/detail?host=fakehost')

    def test_volume_manageable_list_details(self):
        self.run_command('--os-volume-api-version 3.8 '
                         'manageable-list fakehost --detailed True')
        self.assert_called('GET', '/manageable_volumes/detail?host=fakehost')

    def test_volume_manageable_list_no_details(self):
        self.run_command('--os-volume-api-version 3.8 '
                         'manageable-list fakehost --detailed False')
        self.assert_called('GET', '/manageable_volumes?host=fakehost')

    def test_volume_manageable_list_cluster(self):
        self.run_command('--os-volume-api-version 3.17 '
                         'manageable-list --cluster dest')
        self.assert_called('GET', '/manageable_volumes/detail?cluster=dest')

    def test_snapshot_manageable_list(self):
        self.run_command('--os-volume-api-version 3.8 '
                         'snapshot-manageable-list fakehost')
        self.assert_called('GET', '/manageable_snapshots/detail?host=fakehost')

    def test_snapshot_manageable_list_details(self):
        self.run_command('--os-volume-api-version 3.8 '
                         'snapshot-manageable-list fakehost --detailed True')
        self.assert_called('GET', '/manageable_snapshots/detail?host=fakehost')

    def test_snapshot_manageable_list_no_details(self):
        self.run_command('--os-volume-api-version 3.8 '
                         'snapshot-manageable-list fakehost --detailed False')
        self.assert_called('GET', '/manageable_snapshots?host=fakehost')

    def test_snapshot_manageable_list_cluster(self):
        self.run_command('--os-volume-api-version 3.17 '
                         'snapshot-manageable-list --cluster dest')
        self.assert_called('GET', '/manageable_snapshots/detail?cluster=dest')

    @ddt.data('', 'snapshot-')
    def test_manageable_list_cluster_before_3_17(self, prefix):
        self.assertRaises(exceptions.UnsupportedAttribute,
                          self.run_command,
                          '--os-volume-api-version 3.16 '
                         '%smanageable-list --cluster dest' % prefix)

    @mock.patch('cinderclient.shell.CinderClientArgumentParser.error')
    @ddt.data('', 'snapshot-')
    def test_manageable_list_mutual_exclusion(self, prefix, error_mock):
        error_mock.side_effect = SystemExit
        self.assertRaises(SystemExit,
                          self.run_command,
                          '--os-volume-api-version 3.17 '
                         '%smanageable-list fakehost --cluster dest' % prefix)

    @mock.patch('cinderclient.shell.CinderClientArgumentParser.error')
    @ddt.data('', 'snapshot-')
    def test_manageable_list_missing_required(self, prefix, error_mock):
        error_mock.side_effect = SystemExit
        self.assertRaises(SystemExit,
                          self.run_command,
                          '--os-volume-api-version 3.17 '
                         '%smanageable-list' % prefix)

    def test_list_messages(self):
        self.run_command('--os-volume-api-version 3.3 message-list')
        self.assert_called('GET', '/messages')

    @ddt.data('volume', 'backup', 'snapshot', None)
    def test_reset_state_entity_not_found(self, entity_type):
        cmd = 'reset-state 999999'
        if entity_type is not None:
            cmd += ' --type %s' % entity_type
        self.assertRaises(exceptions.CommandError, self.run_command, cmd)

    @ddt.data({'entity_types': [{'name': 'volume', 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': 'backup', 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': 'snapshot', 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': None, 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': 'group', 'version': '3.20',
                                 'command': 'reset_status'},
                                {'name': 'group-snapshot', 'version': '3.19',
                                 'command': 'reset_status'}],
               'r_id': ['1234'],
               'states': ['available', 'error', None]},
              {'entity_types': [{'name': 'volume', 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': 'backup', 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': 'snapshot', 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': None, 'version': '3.0',
                                 'command': 'os-reset_status'},
                                {'name': 'group', 'version': '3.20',
                                 'command': 'reset_status'},
                                {'name': 'group-snapshot', 'version': '3.19',
                                 'command': 'reset_status'}],
               'r_id': ['1234', '5678'],
               'states': ['available', 'error', None]})
    @ddt.unpack
    def test_reset_state_normal(self, entity_types, r_id, states):
        for state in states:
            for t in entity_types:
                if state is None:
                    expected = {t['command']: {}}
                    cmd = ('--os-volume-api-version '
                           '%s reset-state %s') % (t['version'],
                                                   ' '.join(r_id))
                else:
                    expected = {t['command']: {'status': state}}
                    cmd = ('--os-volume-api-version '
                           '%s reset-state '
                           '--state %s %s') % (t['version'],
                                               state, ' '.join(r_id))
                if t['name'] is not None:
                    cmd += ' --type %s' % t['name']

                self.run_command(cmd)

                name = t['name'] if t['name'] else 'volume'
                for re in r_id:
                    self.assert_called_anytime('POST', '/%ss/%s/action'
                                               % (name.replace('-', '_'), re),
                                               body=expected)

    @ddt.data({'command': '--attach-status detached',
               'expected': {'attach_status': 'detached'}},
              {'command': '--state in-use --attach-status attached',
               'expected': {'status': 'in-use',
                            'attach_status': 'attached'}},
              {'command': '--reset-migration-status',
               'expected': {'migration_status': 'none'}})
    @ddt.unpack
    def test_reset_state_volume_additional_status(self, command, expected):
        self.run_command('reset-state %s 1234' % command)
        expected = {'os-reset_status': expected}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_snapshot_list_with_with_count(self):
        self.run_command(
            '--os-volume-api-version 3.45 snapshot-list --with-count')
        self.assert_called('GET', '/snapshots/detail?with_count=True')

    def test_snapshot_list_with_metadata(self):
        self.run_command('--os-volume-api-version 3.22 '
                         'snapshot-list --metadata key1=val1')
        expected = ("/snapshots/detail?metadata=%s"
                    % parse.quote_plus("{'key1': 'val1'}"))
        self.assert_called('GET', expected)

    @ddt.data(('resource_type',), ('event_id',), ('resource_uuid',),
              ('level', 'message_level'), ('request_id',))
    def test_list_messages_with_filters(self, filter):
        self.run_command('--os-volume-api-version 3.5 message-list --%s=TEST'
                         % filter[0])
        self.assert_called('GET', '/messages?%s=TEST' % filter[-1])

    def test_list_messages_with_sort(self):
        self.run_command('--os-volume-api-version 3.5 '
                         'message-list --sort=id:asc')
        self.assert_called('GET', '/messages?sort=id%3Aasc')

    def test_list_messages_with_limit(self):
        self.run_command('--os-volume-api-version 3.5 message-list --limit=1')
        self.assert_called('GET', '/messages?limit=1')

    def test_list_messages_with_marker(self):
        self.run_command('--os-volume-api-version 3.5 message-list --marker=1')
        self.assert_called('GET', '/messages?marker=1')

    def test_list_with_image_metadata_before_3_4(self):
        self.assertRaises(exceptions.UnsupportedAttribute,
                          self.run_command,
                          'list --image_metadata image_name=1234')

    def test_list_filter_image_metadata(self):
        self.run_command('--os-volume-api-version 3.4 '
                         'list --image_metadata image_name=1234')
        url = ('/volumes/detail?%s' %
               parse.urlencode([('glance_metadata', {"image_name": "1234"})]))
        self.assert_called('GET', url)

    def test_show_message(self):
        self.run_command('--os-volume-api-version 3.5 message-show 1234')
        self.assert_called('GET', '/messages/1234')

    def test_delete_message(self):
        self.run_command('--os-volume-api-version 3.5 message-delete 1234')
        self.assert_called('DELETE', '/messages/1234')

    def test_delete_messages(self):
        self.run_command(
            '--os-volume-api-version 3.3 message-delete 1234 12345')
        self.assert_called_anytime('DELETE', '/messages/1234')
        self.assert_called_anytime('DELETE', '/messages/12345')

    @mock.patch('cinderclient.utils.find_resource')
    def test_delete_metadata(self, mock_find_volume):
        mock_find_volume.return_value = volumes.Volume(self,
                                                       {'id': '1234',
                                                        'metadata':
                                                            {'k1': 'v1',
                                                             'k2': 'v2',
                                                             'k3': 'v3'}},
                                                       loaded = True)
        expected = {'metadata': {'k2': 'v2'}}
        self.run_command('--os-volume-api-version 3.15 '
                         'metadata 1234 unset k1 k3')
        self.assert_called('PUT', '/volumes/1234/metadata', body=expected)

    @ddt.data(("3.0", None), ("3.6", None),
              ("3.7", True), ("3.7", False), ("3.7", ""))
    @ddt.unpack
    def test_service_list_withreplication(self, version, replication):
        command = ('--os-volume-api-version %s service-list' %
                   version)
        if replication is not None:
            command += ' --withreplication %s' % replication
        self.run_command(command)
        self.assert_called('GET', '/os-services')

    def test_group_enable_replication(self):
        cmd = '--os-volume-api-version 3.38 group-enable-replication 1234'
        self.run_command(cmd)
        expected = {'enable_replication': {}}
        self.assert_called('POST', '/groups/1234/action', body=expected)

    def test_group_disable_replication(self):
        cmd = '--os-volume-api-version 3.38 group-disable-replication 1234'
        self.run_command(cmd)
        expected = {'disable_replication': {}}
        self.assert_called('POST', '/groups/1234/action', body=expected)

    @ddt.data((False, None), (True, None),
              (False, "backend1"), (True, "backend1"),
              (False, "default"), (True, "default"))
    @ddt.unpack
    def test_group_failover_replication(self, attach_vol, backend):
        attach = '--allow-attached-volume ' if attach_vol else ''
        backend_id = ('--secondary-backend-id ' + backend) if backend else ''
        cmd = ('--os-volume-api-version 3.38 '
               'group-failover-replication 1234 ' + attach + backend_id)
        self.run_command(cmd)
        expected = {'failover_replication':
                    {'allow_attached_volume': attach_vol,
                     'secondary_backend_id': backend if backend else None}}
        self.assert_called('POST', '/groups/1234/action', body=expected)

    def test_group_list_replication_targets(self):
        cmd = ('--os-volume-api-version 3.38 group-list-replication-targets'
               ' 1234')
        self.run_command(cmd)
        expected = {'list_replication_targets': {}}
        self.assert_called('POST', '/groups/1234/action', body=expected)

    @mock.patch('cinderclient.v3.services.ServiceManager.get_log_levels')
    def test_service_get_log_before_3_32(self, get_levels_mock):
        self.assertRaises(SystemExit,
                          self.run_command, '--os-volume-api-version 3.28 '
                         'service-get-log')
        get_levels_mock.assert_not_called()

    @mock.patch('cinderclient.v3.services.ServiceManager.get_log_levels')
    @mock.patch('cinderclient.utils.print_list')
    def test_service_get_log_no_params(self, print_mock, get_levels_mock):
        self.run_command('--os-volume-api-version 3.32 service-get-log')
        get_levels_mock.assert_called_once_with('', '', '')
        print_mock.assert_called_once_with(get_levels_mock.return_value,
                                           ('Binary', 'Host', 'Prefix',
                                            'Level'))

    @ddt.data('*', 'cinder-api', 'cinder-volume', 'cinder-scheduler',
              'cinder-backup')
    @mock.patch('cinderclient.v3.services.ServiceManager.get_log_levels')
    @mock.patch('cinderclient.utils.print_list')
    def test_service_get_log(self, binary, print_mock, get_levels_mock):
        server = 'host1'
        prefix = 'sqlalchemy'

        self.run_command('--os-volume-api-version 3.32 service-get-log '
                         '--binary %s --server %s --prefix %s' % (
                             binary, server, prefix))
        get_levels_mock.assert_called_once_with(binary, server, prefix)
        print_mock.assert_called_once_with(get_levels_mock.return_value,
                                           ('Binary', 'Host', 'Prefix',
                                            'Level'))

    @mock.patch('cinderclient.v3.services.ServiceManager.set_log_levels')
    def test_service_set_log_before_3_32(self, set_levels_mock):
        self.assertRaises(SystemExit,
                          self.run_command, '--os-volume-api-version 3.28 '
                         'service-set-log debug')
        set_levels_mock.assert_not_called()

    @mock.patch('cinderclient.v3.services.ServiceManager.set_log_levels')
    @mock.patch('cinderclient.shell.CinderClientArgumentParser.error')
    def test_service_set_log_missing_required(self, error_mock,
                                              set_levels_mock):
        error_mock.side_effect = SystemExit
        self.assertRaises(SystemExit,
                          self.run_command, '--os-volume-api-version 3.32 '
                          'service-set-log')
        set_levels_mock.assert_not_called()
        # Different error message from argparse library in Python 2 and 3
        if six.PY3:
            msg = 'the following arguments are required: <log-level>'
        else:
            msg = 'too few arguments'
        error_mock.assert_called_once_with(msg)

    @ddt.data('debug', 'DEBUG', 'info', 'INFO', 'warning', 'WARNING', 'error',
              'ERROR')
    @mock.patch('cinderclient.v3.services.ServiceManager.set_log_levels')
    def test_service_set_log_min_params(self, level, set_levels_mock):
        self.run_command('--os-volume-api-version 3.32 '
                         'service-set-log %s' % level)
        set_levels_mock.assert_called_once_with(level, '', '', '')

    @ddt.data('*', 'cinder-api', 'cinder-volume', 'cinder-scheduler',
              'cinder-backup')
    @mock.patch('cinderclient.v3.services.ServiceManager.set_log_levels')
    def test_service_set_log_levels(self, binary, set_levels_mock):
        level = 'debug'
        server = 'host1'
        prefix = 'sqlalchemy.'
        self.run_command('--os-volume-api-version 3.32 '
                         'service-set-log %s --binary %s --server %s '
                         '--prefix %s' % (level, binary, server, prefix))
        set_levels_mock.assert_called_once_with(level, binary, server, prefix)

    @mock.patch('cinderclient.shell_utils._poll_for_status')
    def test_create_with_poll(self, poll_method):
        self.run_command('create --poll 1')
        self.assert_called_anytime('GET', '/volumes/1234')
        volume = self.shell.cs.volumes.get('1234')
        info = dict()
        info.update(volume._info)
        self.assertEqual(1, poll_method.call_count)
        timeout_period = 3600
        poll_method.assert_has_calls([mock.call(self.shell.cs.volumes.get,
            1234, info, 'creating', ['available'], timeout_period,
            self.shell.cs.client.global_request_id,
            self.shell.cs.messages)])

    @mock.patch('cinderclient.shell_utils.time')
    def test_poll_for_status(self, mock_time):
        poll_period = 2
        some_id = "some-id"
        global_request_id = "req-someid"
        action = "some"
        updated_objects = (
            base.Resource(None, info={"not_default_field": "creating"}),
            base.Resource(None, info={"not_default_field": "available"}))
        poll_fn = mock.MagicMock(side_effect=updated_objects)
        cinderclient.shell_utils._poll_for_status(
            poll_fn = poll_fn,
            obj_id = some_id,
            global_request_id = global_request_id,
            messages = base.Resource(None, {}),
            info = {},
            action = action,
            status_field = "not_default_field",
            final_ok_states = ['available'],
            timeout_period=3600)
        self.assertEqual([mock.call(poll_period)] * 2,
                mock_time.sleep.call_args_list)
        self.assertEqual([mock.call(some_id)] * 2, poll_fn.call_args_list)

    @mock.patch('cinderclient.v3.messages.MessageManager.list')
    @mock.patch('cinderclient.shell_utils.time')
    def test_poll_for_status_error(self, mock_time, mock_message_list):
        poll_period = 2
        some_id = "some_id"
        global_request_id = "req-someid"
        action = "some"
        updated_objects = (
            base.Resource(None, info={"not_default_field": "creating"}),
            base.Resource(None, info={"not_default_field": "error"}))
        poll_fn = mock.MagicMock(side_effect=updated_objects)
        msg_object = base.Resource(cinderclient.v3.messages.MessageManager,
                info = {"user_message": "ERROR!"})
        mock_message_list.return_value = (msg_object,)
        self.assertRaises(exceptions.ResourceInErrorState,
                cinderclient.shell_utils._poll_for_status,
                poll_fn=poll_fn,
                obj_id=some_id,
                global_request_id=global_request_id,
                messages=cinderclient.v3.messages.MessageManager(api=3.34),
                info=dict(),
                action=action,
                final_ok_states=['available'],
                status_field="not_default_field",
                timeout_period=3600)
        self.assertEqual([mock.call(poll_period)] * 2,
                mock_time.sleep.call_args_list)
        self.assertEqual([mock.call(some_id)] * 2, poll_fn.call_args_list)

    def test_backup(self):
        self.run_command('--os-volume-api-version 3.42 backup-create '
                         '--name 1234 1234')
        expected = {'backup': {'volume_id': 1234,
                               'container': None,
                               'name': '1234',
                               'description': None,
                               'incremental': False,
                               'force': False,
                               'snapshot_id': None,
                               }}
        self.assert_called('POST', '/backups', body=expected)

    def test_backup_with_metadata(self):
        self.run_command('--os-volume-api-version 3.43 backup-create '
                         '--metadata foo=bar --name 1234 1234')
        expected = {'backup': {'volume_id': 1234,
                               'container': None,
                               'name': '1234',
                               'description': None,
                               'incremental': False,
                               'force': False,
                               'snapshot_id': None,
                               'metadata': {'foo': 'bar'}, }}
        self.assert_called('POST', '/backups', body=expected)

    def test_backup_with_az(self):
        self.run_command('--os-volume-api-version 3.51 backup-create '
                         '--availability-zone AZ2 --name 1234 1234')
        expected = {'backup': {'volume_id': 1234,
                               'container': None,
                               'name': '1234',
                               'description': None,
                               'incremental': False,
                               'force': False,
                               'snapshot_id': None,
                               'availability_zone': 'AZ2'}}
        self.assert_called('POST', '/backups', body=expected)

    @mock.patch("cinderclient.utils.print_list")
    def test_snapshot_list_with_userid(self, mock_print_list):
        """Ensure 3.41 provides User ID header."""
        self.run_command('--os-volume-api-version 3.41 snapshot-list')
        self.assert_called('GET', '/snapshots/detail')
        columns = ['ID', 'Volume ID', 'Status', 'Name', 'Size', 'User ID']
        mock_print_list.assert_called_once_with(mock.ANY, columns,
                                                sortby_index=0)

    @mock.patch('cinderclient.v3.volumes.Volume.migrate_volume')
    def test_migrate_volume_before_3_16(self, v3_migrate_mock):
        self.run_command('--os-volume-api-version 3.15 '
                         'migrate 1234 fakehost')

        v3_migrate_mock.assert_called_once_with(
            'fakehost', False, False, None)

    @mock.patch('cinderclient.v3.volumes.Volume.migrate_volume')
    def test_migrate_volume_3_16(self, v3_migrate_mock):
        self.run_command('--os-volume-api-version 3.16 '
                         'migrate 1234 fakehost')
        self.assertEqual(4, len(v3_migrate_mock.call_args[0]))

    def test_migrate_volume_with_cluster_before_3_16(self):
        self.assertRaises(exceptions.UnsupportedAttribute,
                          self.run_command,
                          '--os-volume-api-version 3.15 '
                          'migrate 1234 fakehost --cluster fakecluster')

    @mock.patch('cinderclient.shell.CinderClientArgumentParser.error')
    def test_migrate_volume_mutual_exclusion(self, error_mock):
        error_mock.side_effect = SystemExit
        self.assertRaises(SystemExit,
                          self.run_command,
                          '--os-volume-api-version 3.16 '
                          'migrate 1234 fakehost --cluster fakecluster')
        msg = 'argument --cluster: not allowed with argument <host>'
        error_mock.assert_called_once_with(msg)

    @mock.patch('cinderclient.shell.CinderClientArgumentParser.error')
    def test_migrate_volume_missing_required(self, error_mock):
        error_mock.side_effect = SystemExit
        self.assertRaises(SystemExit,
                          self.run_command,
                          '--os-volume-api-version 3.16 '
                          'migrate 1234')
        msg = 'one of the arguments <host> --cluster is required'
        error_mock.assert_called_once_with(msg)

    def test_migrate_volume_host(self):
        self.run_command('--os-volume-api-version 3.16 '
                         'migrate 1234 fakehost')
        expected = {'os-migrate_volume': {'force_host_copy': False,
                                          'lock_volume': False,
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_migrate_volume_cluster(self):
        self.run_command('--os-volume-api-version 3.16 '
                         'migrate 1234 --cluster mycluster')
        expected = {'os-migrate_volume': {'force_host_copy': False,
                                          'lock_volume': False,
                                          'cluster': 'mycluster'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_migrate_volume_bool_force(self):
        self.run_command('--os-volume-api-version 3.16 '
                         'migrate 1234 fakehost --force-host-copy '
                         '--lock-volume')
        expected = {'os-migrate_volume': {'force_host_copy': True,
                                          'lock_volume': True,
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

    def test_migrate_volume_bool_force_false(self):
        # Set both --force-host-copy and --lock-volume to False.
        self.run_command('--os-volume-api-version 3.16 '
                         'migrate 1234 fakehost --force-host-copy=False '
                         '--lock-volume=False')
        expected = {'os-migrate_volume': {'force_host_copy': 'False',
                                          'lock_volume': 'False',
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action', body=expected)

        # Do not set the values to --force-host-copy and --lock-volume.
        self.run_command('--os-volume-api-version 3.16 '
                         'migrate 1234 fakehost')
        expected = {'os-migrate_volume': {'force_host_copy': False,
                                          'lock_volume': False,
                                          'host': 'fakehost'}}
        self.assert_called('POST', '/volumes/1234/action',
                           body=expected)

    @ddt.data({'bootable': False, 'by_id': False, 'cluster': None},
              {'bootable': True, 'by_id': False, 'cluster': None},
              {'bootable': False, 'by_id': True, 'cluster': None},
              {'bootable': True, 'by_id': True, 'cluster': None},
              {'bootable': True, 'by_id': True, 'cluster': 'clustername'})
    @ddt.unpack
    def test_volume_manage(self, bootable, by_id, cluster):
        cmd = ('--os-volume-api-version 3.16 '
               'manage host1 some_fake_name --name foo --description bar '
               '--volume-type baz --availability-zone az '
               '--metadata k1=v1 k2=v2')
        if by_id:
            cmd += ' --id-type source-id'
        if bootable:
            cmd += ' --bootable'
        if cluster:
            cmd += ' --cluster ' + cluster

        self.run_command(cmd)
        ref = 'source-id' if by_id else 'source-name'
        expected = {'volume': {'host': 'host1',
                               'ref': {ref: 'some_fake_name'},
                               'name': 'foo',
                               'description': 'bar',
                               'volume_type': 'baz',
                               'availability_zone': 'az',
                               'metadata': {'k1': 'v1', 'k2': 'v2'},
                               'bootable': bootable}}
        if cluster:
            expected['volume']['cluster'] = cluster
        self.assert_called_anytime('POST', '/os-volume-manage', body=expected)

    def test_volume_manage_before_3_16(self):
        """Cluster optional argument was not acceptable."""
        self.assertRaises(exceptions.UnsupportedAttribute,
                          self.run_command,
                          'manage host1 some_fake_name '
                          '--cluster clustername'
                          '--name foo --description bar --bootable '
                          '--volume-type baz --availability-zone az '
                          '--metadata k1=v1 k2=v2')

    def test_worker_cleanup_before_3_24(self):
        self.assertRaises(SystemExit,
                          self.run_command,
                          'work-cleanup fakehost')

    def test_worker_cleanup(self):
        self.run_command('--os-volume-api-version 3.24 '
                         'work-cleanup --cluster clustername --host hostname '
                         '--binary binaryname --is-up false --disabled true '
                         '--resource-id uuid --resource-type Volume '
                         '--service-id 1')
        expected = {'cluster_name': 'clustername',
                    'host': 'hostname',
                    'binary': 'binaryname',
                    'is_up': 'false',
                    'disabled': 'true',
                    'resource_id': 'uuid',
                    'resource_type': 'Volume',
                    'service_id': 1}

        self.assert_called('POST', '/workers/cleanup', body=expected)

    def test_create_transfer(self):
        self.run_command('transfer-create 1234')
        expected = {'transfer': {'volume_id': 1234,
                                 'name': None,
                                 }}
        self.assert_called('POST', '/os-volume-transfer', body=expected)

    def test_create_transfer_no_snaps(self):
        self.run_command('--os-volume-api-version 3.55 transfer-create '
                         '--no-snapshots 1234')
        expected = {'transfer': {'volume_id': 1234,
                                 'name': None,
                                 'no_snapshots': True
                                 }}
        self.assert_called('POST', '/volume-transfers', body=expected)

    def test_list_transfer_sorty_not_sorty(self):
        self.run_command(
            '--os-volume-api-version 3.59 transfer-list')
        url = ('/volume-transfers/detail')
        self.assert_called('GET', url)

    def test_subcommand_parser(self):
        """Ensure that all the expected commands show up.

        This test ensures that refactoring code does not somehow result in
        a command accidentally ceasing to exist.

        TODO: add a similar test for 3.59 or so
        """
        p = self.shell.get_subcommand_parser(api_versions.APIVersion("3.0"),
                                             input_args=['help'], do_help=True)
        help_text = p.format_help()

        # These are v3.0 commands only
        expected_commands = ('absolute-limits',
                             'api-version',
                             'availability-zone-list',
                             'backup-create',
                             'backup-delete',
                             'backup-export',
                             'backup-import',
                             'backup-list',
                             'backup-reset-state',
                             'backup-restore',
                             'backup-show',
                             'cgsnapshot-create',
                             'cgsnapshot-delete',
                             'cgsnapshot-list',
                             'cgsnapshot-show',
                             'consisgroup-create',
                             'consisgroup-create-from-src',
                             'consisgroup-delete',
                             'consisgroup-list',
                             'consisgroup-show',
                             'consisgroup-update',
                             'create',
                             'delete',
                             'encryption-type-create',
                             'encryption-type-delete',
                             'encryption-type-list',
                             'encryption-type-show',
                             'encryption-type-update',
                             'extend',
                             'extra-specs-list',
                             'failover-host',
                             'force-delete',
                             'freeze-host',
                             'get-capabilities',
                             'get-pools',
                             'image-metadata',
                             'image-metadata-show',
                             'list',
                             'manage',
                             'metadata',
                             'metadata-show',
                             'metadata-update-all',
                             'migrate',
                             'qos-associate',
                             'qos-create',
                             'qos-delete',
                             'qos-disassociate',
                             'qos-disassociate-all',
                             'qos-get-association',
                             'qos-key',
                             'qos-list',
                             'qos-show',
                             'quota-class-show',
                             'quota-class-update',
                             'quota-defaults',
                             'quota-delete',
                             'quota-show',
                             'quota-update',
                             'quota-usage',
                             'rate-limits',
                             'readonly-mode-update',
                             'rename',
                             'reset-state',
                             'retype',
                             'service-disable',
                             'service-enable',
                             'service-list',
                             'set-bootable',
                             'show',
                             'snapshot-create',
                             'snapshot-delete',
                             'snapshot-list',
                             'snapshot-manage',
                             'snapshot-metadata',
                             'snapshot-metadata-show',
                             'snapshot-metadata-update-all',
                             'snapshot-rename',
                             'snapshot-reset-state',
                             'snapshot-show',
                             'snapshot-unmanage',
                             'thaw-host',
                             'transfer-accept',
                             'transfer-create',
                             'transfer-delete',
                             'transfer-list',
                             'transfer-show',
                             'type-access-add',
                             'type-access-list',
                             'type-access-remove',
                             'type-create',
                             'type-default',
                             'type-delete',
                             'type-key',
                             'type-list',
                             'type-show',
                             'type-update',
                             'unmanage',
                             'upload-to-image',
                             'version-list',
                             'bash-completion',
                             'help',)

        for e in expected_commands:
            self.assertIn('    ' + e, help_text)
