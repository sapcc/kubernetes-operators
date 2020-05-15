# Copyright 2016 FUJITSU LIMITED
# Copyright (c) 2016 EMC Corporation
#
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

from cinderclient import api_versions
from cinderclient import exceptions
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes
from cinderclient.v3 import volume_snapshots
from cinderclient.v3 import volumes

from six.moves.urllib import parse


@ddt.ddt
class VolumesTest(utils.TestCase):

    def test_volume_manager_upload_to_image(self):
        expected = {'os-volume_upload_image':
                    {'force': False,
                     'container_format': 'bare',
                     'disk_format': 'raw',
                     'image_name': 'name',
                     'visibility': 'public',
                     'protected': True}}
        api_version = api_versions.APIVersion('3.1')
        cs = fakes.FakeClient(api_version)
        manager = volumes.VolumeManager(cs)
        fake_volume = volumes.Volume(manager,
                                     {'id': 1234, 'name': 'sample-volume'},
                                     loaded=True)
        fake_volume.upload_to_image(False, 'name', 'bare', 'raw',
                                    visibility='public', protected=True)
        cs.assert_called_anytime('POST', '/volumes/1234/action', body=expected)

    @ddt.data('3.39', '3.40')
    def test_revert_to_snapshot(self, version):

        api_version = api_versions.APIVersion(version)
        cs = fakes.FakeClient(api_version)
        manager = volumes.VolumeManager(cs)
        fake_snapshot = volume_snapshots.Snapshot(
            manager, {'id': 12345, 'name': 'fake-snapshot'}, loaded=True)
        fake_volume = volumes.Volume(manager,
                                     {'id': 1234, 'name': 'sample-volume'},
                                     loaded=True)
        expected = {'revert': {'snapshot_id': 12345}}

        if version == '3.40':
            fake_volume.revert_to_snapshot(fake_snapshot)

            cs.assert_called_anytime('POST', '/volumes/1234/action',
                                     body=expected)
        else:
            self.assertRaises(exceptions.VersionNotFoundForAPIMethod,
                              fake_volume.revert_to_snapshot, fake_snapshot)

    def test_create_volume(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.13'))
        vol = cs.volumes.create(1, group_id='1234', volume_type='5678')
        expected = {'volume': {'description': None,
                               'availability_zone': None,
                               'source_volid': None,
                               'snapshot_id': None,
                               'size': 1,
                               'name': None,
                               'imageRef': None,
                               'volume_type': '5678',
                               'metadata': {},
                               'consistencygroup_id': None,
                               'group_id': '1234',
                               'backup_id': None}}
        cs.assert_called('POST', '/volumes', body=expected)
        self._assert_request_id(vol)

    @ddt.data((False, '/volumes/summary'),
              (True, '/volumes/summary?all_tenants=True'))
    def test_volume_summary(self, all_tenants_input):
        all_tenants, url = all_tenants_input
        cs = fakes.FakeClient(api_versions.APIVersion('3.12'))
        cs.volumes.summary(all_tenants=all_tenants)
        cs.assert_called('GET', url)

    def test_volume_manage_cluster(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.16'))
        vol = cs.volumes.manage(None, {'k': 'v'}, cluster='cluster1')
        expected = {'host': None, 'name': None, 'availability_zone': None,
                    'description': None, 'metadata': None, 'ref': {'k': 'v'},
                    'volume_type': None, 'bootable': False,
                    'cluster': 'cluster1'}
        cs.assert_called('POST', '/os-volume-manage', {'volume': expected})
        self._assert_request_id(vol)

    def test_volume_list_manageable(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.8'))
        cs.volumes.list_manageable('host1', detailed=False)
        cs.assert_called('GET', '/manageable_volumes?host=host1')

    def test_volume_list_manageable_detailed(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.8'))
        cs.volumes.list_manageable('host1', detailed=True)
        cs.assert_called('GET', '/manageable_volumes/detail?host=host1')

    def test_snapshot_list_manageable(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.8'))
        cs.volume_snapshots.list_manageable('host1', detailed=False)
        cs.assert_called('GET', '/manageable_snapshots?host=host1')

    def test_snapshot_list_manageable_detailed(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.8'))
        cs.volume_snapshots.list_manageable('host1', detailed=True)
        cs.assert_called('GET', '/manageable_snapshots/detail?host=host1')

    def test_snapshot_list_with_metadata(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.22'))
        cs.volume_snapshots.list(search_opts={'metadata': {'key1': 'val1'}})
        expected = ("/snapshots/detail?metadata=%s"
                    % parse.quote_plus("{'key1': 'val1'}"))
        cs.assert_called('GET', expected)

    def test_list_with_image_metadata(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.0'))
        cs.volumes.list(search_opts={'glance_metadata': {'key1': 'val1'}})
        expected = ("/volumes/detail?glance_metadata=%s"
                    % parse.quote_plus("{'key1': 'val1'}"))
        cs.assert_called('GET', expected)

    @ddt.data(True, False)
    def test_get_pools_filter_by_name(self, detail):
        cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.33'))
        vol = cs.volumes.get_pools(detail, {'name': 'pool1'})
        request_url = '/scheduler-stats/get_pools?name=pool1'
        if detail:
            request_url = '/scheduler-stats/get_pools?detail=True&name=pool1'
        cs.assert_called('GET', request_url)
        self._assert_request_id(vol)

    def test_migrate_host(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.0'))
        v = cs.volumes.get('1234')
        self._assert_request_id(v)
        vol = cs.volumes.migrate_volume(v, 'host_dest', False, False)
        cs.assert_called('POST', '/volumes/1234/action',
                         {'os-migrate_volume': {'host': 'host_dest',
                                                'force_host_copy': False,
                                                'lock_volume': False}})
        self._assert_request_id(vol)

    def test_migrate_with_lock_volume(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.0'))
        v = cs.volumes.get('1234')
        self._assert_request_id(v)
        vol = cs.volumes.migrate_volume(v, 'dest', False, True)
        cs.assert_called('POST', '/volumes/1234/action',
                         {'os-migrate_volume': {'host': 'dest',
                                                'force_host_copy': False,
                                                'lock_volume': True}})
        self._assert_request_id(vol)

    def test_migrate_cluster(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.16'))
        v = cs.volumes.get('fake')
        self._assert_request_id(v)
        vol = cs.volumes.migrate_volume(v, 'host_dest', False, False,
                                        'cluster_dest')
        cs.assert_called('POST', '/volumes/fake/action',
                         {'os-migrate_volume': {'cluster': 'cluster_dest',
                                                'force_host_copy': False,
                                                'lock_volume': False}})
        self._assert_request_id(vol)
