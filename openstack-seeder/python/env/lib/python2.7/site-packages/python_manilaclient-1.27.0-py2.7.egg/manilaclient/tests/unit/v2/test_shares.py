# Copyright 2010 Jacob Kaplan-Moss

# Copyright 2011 OpenStack Foundation
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
import mock

from manilaclient import api_versions
from manilaclient.common.apiclient import exceptions as client_exceptions
from manilaclient import exceptions
from manilaclient import extension
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import shares

extensions = [
    extension.Extension('shares', shares),
]
cs = fakes.FakeClient(extensions=extensions)


@ddt.ddt
class SharesTest(utils.TestCase):

    # Testcases for class Share
    def setUp(self):
        super(SharesTest, self).setUp()
        self.share = shares.Share(None, {'id': 1})
        self.share.manager = mock.Mock()

    def test_share_allow_access(self):
        access_level = 'fake_level'
        access_to = 'fake_credential'
        access_type = 'fake_type'

        self.share.allow(access_type, access_to, access_level)

        self.share.manager.allow.assert_called_once_with(
            self.share, access_type, access_to, access_level, None)

    # Testcases for class ShareManager

    @ddt.data('nfs', 'cifs', 'cephfs', 'glusterfs', 'hdfs', 'maprfs')
    def test_create_share_with_protocol(self, protocol):
        expected = {
            'size': 1,
            'snapshot_id': None,
            'name': None,
            'description': None,
            'metadata': dict(),
            'share_proto': protocol,
            'share_network_id': None,
            'share_type': None,
            'is_public': False,
            'availability_zone': None,
        }
        cs.shares.create(protocol, 1)
        cs.assert_called('POST', '/shares', {'share': expected})

    @ddt.data(
        type('ShareNetworkUUID', (object, ), {'uuid': 'fake_nw'}),
        type('ShareNetworkID', (object, ), {'id': 'fake_nw'}),
        'fake_nw')
    def test_create_share_with_share_network(self, share_network):
        expected = {
            'size': 1,
            'snapshot_id': None,
            'name': None,
            'description': None,
            'metadata': dict(),
            'share_proto': 'nfs',
            'share_network_id': 'fake_nw',
            'share_type': None,
            'is_public': False,
            'availability_zone': None,
        }
        cs.shares.create('nfs', 1, share_network=share_network)
        cs.assert_called('POST', '/shares', {'share': expected})

    @ddt.data(
        type('ShareTypeUUID', (object, ), {'uuid': 'fake_st'}),
        type('ShareTypeID', (object, ), {'id': 'fake_st'}),
        'fake_st')
    def test_create_share_with_share_type(self, share_type):
        expected = {
            'size': 1,
            'snapshot_id': None,
            'name': None,
            'description': None,
            'metadata': dict(),
            'share_proto': 'nfs',
            'share_network_id': None,
            'share_type': 'fake_st',
            'is_public': False,
            'availability_zone': None,
        }
        cs.shares.create('nfs', 1, share_type=share_type)
        cs.assert_called('POST', '/shares', {'share': expected})

    @ddt.data({'is_public': True,
               'availability_zone': 'nova'},
              {'is_public': False,
               'availability_zone': 'fake_azzzzz'})
    @ddt.unpack
    def test_create_share_with_all_params_defined(self, is_public,
                                                  availability_zone):
        body = {
            'share': {
                'is_public': is_public,
                'share_type': None,
                'name': None,
                'snapshot_id': None,
                'description': None,
                'metadata': {},
                'share_proto': 'nfs',
                'share_network_id': None,
                'size': 1,
                'availability_zone': availability_zone,
            }
        }
        cs.shares.create('nfs', 1, is_public=is_public,
                         availability_zone=availability_zone)
        cs.assert_called('POST', '/shares', body)

    @ddt.data(
        type('ShareUUID', (object, ), {'uuid': '1234'}),
        type('ShareID', (object, ), {'id': '1234'}),
        '1234')
    def test_get_share(self, share):
        share = cs.shares.get(share)
        cs.assert_called('GET', '/shares/1234')

    @ddt.data(
        type('ShareUUID', (object, ), {'uuid': '1234'}),
        type('ShareID', (object, ), {'id': '1234'}),
        '1234')
    def test_get_update(self, share):
        data = dict(foo='bar', quuz='foobar')
        share = cs.shares.update(share, **data)
        cs.assert_called('PUT', '/shares/1234', {'share': data})

    def test_delete_share(self):
        share = cs.shares.get('1234')
        cs.shares.delete(share)
        cs.assert_called('DELETE', '/shares/1234')

    @ddt.data(
        ("2.6", "/os-share-manage", None),
        ("2.7", "/shares/manage", None),
        ("2.8", "/shares/manage", True),
        ("2.8", "/shares/manage", False),
        ("2.49", "/shares/manage", False, '1234'),
    )
    @ddt.unpack
    def test_manage_share(self, microversion, resource_path, is_public=False,
                          share_server_id=None):
        service_host = "fake_service_host"
        protocol = "fake_protocol"
        export_path = "fake_export_path"
        driver_options = "fake_driver_options"
        share_type = "fake_share_type"
        name = "foo_name"
        description = "bar_description"
        expected_body = {
            "service_host": service_host,
            "share_type": share_type,
            "protocol": protocol,
            "export_path": export_path,
            "driver_options": driver_options,
            "name": name,
            "description": description,
            "share_server_id": share_server_id,
        }
        version = api_versions.APIVersion(microversion)
        if version >= api_versions.APIVersion('2.8'):
            expected_body["is_public"] = is_public

        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_create",
                               mock.Mock(return_value="fake")):
            if version < api_versions.APIVersion('2.8'):
                result = manager.manage(
                    service_host, protocol, export_path, driver_options,
                    share_type, name, description)
            elif (api_versions.APIVersion('2.8') <= version
                    < api_versions.APIVersion('2.49')):
                result = manager.manage(
                    service_host, protocol, export_path, driver_options,
                    share_type, name, description, is_public)
            else:
                result = manager.manage(
                    service_host, protocol, export_path, driver_options,
                    share_type, name, description, is_public, share_server_id)

            self.assertEqual(manager._create.return_value, result)
            manager._create.assert_called_once_with(
                resource_path, {"share": expected_body}, "share")

    @ddt.data(
        type("ShareUUID", (object, ), {"uuid": "1234"}),
        type("ShareID", (object, ), {"id": "1234"}),
        "1234")
    def test_unmanage_share_v2_6(self, share):
        version = api_versions.APIVersion("2.6")
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.unmanage(share)

            self.assertFalse(manager._action.called)
            self.assertNotEqual("fake", result)
            self.assertEqual(manager.api.client.post.return_value, result)
            manager.api.client.post.assert_called_once_with(
                "/os-share-unmanage/1234/unmanage")

    def test_unmanage_share_v2_7(self):
        share = "fake_share"
        version = api_versions.APIVersion("2.7")
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.unmanage(share)

            manager._action.assert_called_once_with("unmanage", share)
            self.assertEqual("fake", result)

    def test_revert_to_snapshot(self):

        share = 'fake_share'
        snapshot = 'fake_snapshot'
        version = api_versions.APIVersion("2.27")
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)
        mock_action = self.mock_object(
            manager, '_action', mock.Mock(return_value='fake'))

        result = manager.revert_to_snapshot(share, snapshot)

        self.assertEqual('fake', result)
        mock_action.assert_called_once_with(
            'revert', 'fake_share', info={'snapshot_id': 'fake_snapshot'})

    def test_revert_to_snapshot_not_supported(self):

        share = 'fake_share'
        snapshot = 'fake_snapshot'
        version = api_versions.APIVersion("2.26")
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        self.assertRaises(client_exceptions.UnsupportedVersion,
                          manager.revert_to_snapshot,
                          share,
                          snapshot)

    @ddt.data(
        ("2.6", "os-force_delete"),
        ("2.7", "force_delete"),
    )
    @ddt.unpack
    def test_force_delete_share(self, microversion, action_name):
        share = "fake_share"
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.force_delete(share)

            manager._action.assert_called_once_with(action_name, share)
            self.assertEqual("fake", result)

    def test_list_shares_index(self):
        cs.shares.list(detailed=False)
        cs.assert_called('GET', '/shares?is_public=True')

    def test_list_shares_index_with_search_opts(self):
        search_opts = {
            'fake_str': 'fake_str_value',
            'fake_int': 1,
            'name~': 'fake_name',
            'description~': 'fake_description',
        }
        cs.shares.list(detailed=False, search_opts=search_opts)
        cs.assert_called(
            'GET',
            '/shares?description~=fake_description&fake_int=1&'
            'fake_str=fake_str_value&is_public=True&name~=fake_name')

    @ddt.data(('id', 'b4991315-eb7d-43ec-979e-5715d4399827', True),
              ('id', 'b4991315-eb7d-43ec-979e-5715d4399827', False),
              ('path', 'fake_path', False),
              ('path', 'fake_path', True))
    @ddt.unpack
    def test_list_shares_index_with_export_location(self, filter_type,
                                                    value, detailed):
        search_opts = {
            'export_location': value,
        }
        cs.shares.list(detailed=detailed, search_opts=search_opts)
        if detailed:
            cs.assert_called(
                'GET', ('/shares/detail?export_location_' + filter_type +
                        '=' + value + '&is_public=True'))
        else:
            cs.assert_called(
                'GET', ('/shares?export_location_' + filter_type + '='
                        + value + '&is_public=True'))

    def test_list_shares_detailed(self):
        search_opts = {
            'with_count': 'True',
        }
        shares, count = cs.shares.list(detailed=True, search_opts=search_opts)
        cs.assert_called(
            'GET', '/shares/detail?is_public=True&with_count=True')
        self.assertEqual(2, count)
        self.assertEqual(1, len(shares))

    def test_list_shares_detailed_with_count(self):
        cs.shares.list(detailed=True)
        cs.assert_called('GET', '/shares/detail?is_public=True')

    def test_list_shares_detailed_with_search_opts(self):
        search_opts = {
            'fake_str': 'fake_str_value',
            'fake_int': 1,
        }
        cs.shares.list(detailed=True, search_opts=search_opts)
        cs.assert_called(
            'GET',
            '/shares/detail?fake_int=1&fake_str=fake_str_value&is_public=True')

    def test_list_shares_sort_by_asc_and_host_key(self):
        cs.shares.list(detailed=False, sort_key='host', sort_dir='asc')
        cs.assert_called('GET',
                         '/shares?is_public=True&sort_dir=asc&sort_key=host')

    def test_list_shares_sort_by_desc_and_size_key(self):
        cs.shares.list(detailed=False, sort_key='size', sort_dir='desc')
        cs.assert_called('GET',
                         '/shares?is_public=True&sort_dir=desc&sort_key=size')

    def test_list_shares_filter_by_share_network_alias(self):
        cs.shares.list(detailed=False, sort_key='share_network')
        cs.assert_called('GET',
                         '/shares?is_public=True&sort_key=share_network_id')

    def test_list_shares_filter_by_snapshot_alias(self):
        cs.shares.list(detailed=False, sort_key='snapshot')
        cs.assert_called('GET', '/shares?is_public=True&sort_key=snapshot_id')

    def test_list_shares_filter_by_share_type_alias(self):
        cs.shares.list(detailed=False, sort_key='share_type')
        cs.assert_called('GET',
                         '/shares?is_public=True&sort_key=share_type_id')

    def test_list_shares_by_improper_direction(self):
        self.assertRaises(ValueError, cs.shares.list, sort_dir='fake')

    def test_list_shares_by_improper_key(self):
        self.assertRaises(ValueError, cs.shares.list, sort_key='fake')

    @ddt.data(
        {'access_to': '127.0.0.1', 'access_type': 'ip',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': '1' * 4, 'access_type': 'user',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': '1' * 255, 'access_type': 'user',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': 'fake${.-_\'`}', 'access_type': 'user',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': 'MYDOMAIN-Administrator', 'access_type': 'user',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': 'test group name', 'access_type': 'user',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': 'x', 'access_type': 'cert',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': 'x' * 64, 'access_type': 'cert',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': 'tenant.example.com', 'access_type': 'cert',
         'action_name': 'os-allow_access', 'microversion': '2.0'},
        {'access_to': '127.0.0.1', 'access_type': 'ip',
         'action_name': 'allow_access', 'microversion': '2.7'},
        {'access_to': 'test group name', 'access_type': 'user',
         'action_name': 'allow_access', 'microversion': '2.7'},
        {'access_to': 'alice', 'access_type': 'cephx',
         'action_name': 'allow_access', 'microversion': '2.13'},
        {'access_to': 'alice_bob', 'access_type': 'cephx',
         'action_name': 'allow_access', 'microversion': '2.13'},
        {'access_to': 'alice bob', 'access_type': 'cephx',
         'action_name': 'allow_access', 'microversion': '2.13'},
        {'access_to': 'test group name', 'access_type': 'user',
         'action_name': 'allow_access', 'microversion': '2.13'},
        {'access_to': 'AD80:0000:0000:0000:ABAA:0000:00C2:0002',
         'access_type': 'ip', 'action_name': 'allow_access',
         'microversion': '2.38'},
        {'access_to': 'AD80::/36',
         'access_type': 'ip', 'action_name': 'allow_access',
         'microversion': '2.38'},
        {'access_to': 'AD80:ABAA::/128',
         'access_type': 'ip', 'action_name': 'allow_access',
         'microversion': '2.38'},
        {'access_to': 'ad80::abaa:0:c2:2',
         'access_type': 'ip', 'action_name': 'allow_access',
         'microversion': '2.38'},
        {'access_to': 'test group name', 'access_type': 'user',
         'action_name': 'allow_access', 'microversion': '2.38'},
    )
    @ddt.unpack
    def test_allow_access_to_share(self, access_to, access_type,
                                   action_name, microversion):
        access = ('foo', {'access': 'bar'})
        access_level = 'fake_access_level'
        share = 'fake_share'
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, '_action',
                               mock.Mock(return_value=access)):
            result = manager.allow(share, access_type, access_to, access_level)

            manager._action.assert_called_once_with(
                action_name, share, {'access_level': access_level,
                                     'access_type': access_type,
                                     'access_to': access_to})
            self.assertEqual('bar', result)

    @ddt.data(
        {'access_to': 'localhost', 'access_type': 'ip',
         'microversion': '2.0'},
        {'access_to': '127.0.0.*', 'access_type': 'ip',
         'microversion': '2.0'},
        {'access_to': '127.0.0.0/33', 'access_type': 'ip',
         'microversion': '2.0'},
        {'access_to': '127.0.0.256', 'access_type': 'ip',
         'microversion': '2.0'},
        {'access_to': '1', 'access_type': 'user',
         'microversion': '2.0'},
        {'access_to': '1' * 3, 'access_type': 'user',
         'microversion': '2.0'},
        {'access_to': '1' * 256, 'access_type': 'user',
         'microversion': '2.0'},
        {'access_to': 'root+=', 'access_type': 'user',
         'microversion': '2.0'},
        {'access_to': '', 'access_type': 'cert',
         'microversion': '2.0'},
        {'access_to': ' ', 'access_type': 'cert',
         'microversion': '2.0'},
        {'access_to': 'x' * 65, 'access_type': 'cert',
         'microversion': '2.0'},
        {'access_to': 'alice', 'access_type': 'cephx',
         'microversion': '2.0'},
        {'access_to': '', 'access_type': 'cephx',
         'microversion': '2.13'},
        {'access_to': u"bj\u00F6rn", 'access_type': 'cephx',
         'microversion': '2.13'},
        {'access_to': "AD80:0000:0000:0000:ABAA:0000:00C2:0002/65",
         'access_type': 'ip', 'microversion': '2.38'},
        {'access_to': "AD80:0000:0000:0000:ABAA:0000:00C2:0002*32",
         'access_type': 'ip', 'microversion': '2.38'},
        {'access_to': "AD80:0000:0000:0000:ABAA:0000:00C2:0002",
         'access_type': 'ip', 'microversion': '2.37'},
    )
    @ddt.unpack
    def test_allow_access_to_share_error_invalid_access(self, access_to,
                                                        access_type,
                                                        microversion):
        access = ('foo', {'access': 'bar'})
        access_level = 'fake_access_level'
        share = 'fake_share'
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, '_action',
                               mock.Mock(return_value=access)):
            self.assertRaises(exceptions.CommandError, manager.allow,
                              share, access_type, access_to, access_level)

            manager._action.assert_not_called()

    @ddt.data(
        ("2.6", "os-deny_access"),
        ("2.7", "deny_access"),
    )
    @ddt.unpack
    def test_deny_access_to_share(self, microversion, action_name):
        access_id = "fake_access_id"
        share = "fake_share"
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.deny(share, access_id)

            manager._action.assert_called_once_with(
                action_name, share, {"access_id": access_id})
            self.assertEqual("fake", result)

    def test_get_metadata(self):
        cs.shares.get_metadata(1234)
        cs.assert_called('GET', '/shares/1234/metadata')

    def test_set_metadata(self):
        cs.shares.set_metadata(1234, {'k1': 'v2'})
        cs.assert_called('POST', '/shares/1234/metadata',
                         {'metadata': {'k1': 'v2'}})

    @ddt.data(
        type('ShareUUID', (object, ), {'uuid': '1234'}),
        type('ShareID', (object, ), {'id': '1234'}),
        '1234')
    def test_delete_metadata(self, share):
        keys = ['key1']
        cs.shares.delete_metadata(share, keys)
        cs.assert_called('DELETE', '/shares/1234/metadata/key1')

    @ddt.data(
        type('ShareUUID', (object, ), {'uuid': '1234'}),
        type('ShareID', (object, ), {'id': '1234'}),
        '1234')
    def test_metadata_update_all(self, share):
        cs.shares.update_all_metadata(share, {'k1': 'v1'})
        cs.assert_called('PUT', '/shares/1234/metadata',
                         {'metadata': {'k1': 'v1'}})

    @ddt.data(
        ("2.6", "os-reset_status"),
        ("2.7", "reset_status"),
    )
    @ddt.unpack
    def test_reset_share_state(self, microversion, action_name):
        state = "available"
        share = "fake_share"
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.reset_state(share, state)

            manager._action.assert_called_once_with(
                action_name, share, {"status": state})
            self.assertEqual("fake", result)

    @ddt.data(
        ("2.6", "os-extend"),
        ("2.7", "extend"),
    )
    @ddt.unpack
    def test_extend_share(self, microversion, action_name):
        size = 123
        share = "fake_share"
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.extend(share, size)

            manager._action.assert_called_once_with(
                action_name, share, {"new_size": size})
            self.assertEqual("fake", result)

    @ddt.data(
        ("2.6", "os-shrink"),
        ("2.7", "shrink"),
    )
    @ddt.unpack
    def test_shrink_share(self, microversion, action_name):
        size = 123
        share = "fake_share"
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        manager = shares.ShareManager(api=mock_microversion)

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.shrink(share, size)

            manager._action.assert_called_once_with(
                action_name, share, {"new_size": size})
            self.assertEqual("fake", result)

    def test_list_share_instances(self):
        share = type('ShareID', (object, ), {'id': '1234'})
        cs.shares.list_instances(share)
        cs.assert_called('GET', '/shares/1234/instances')

    def test_migration_start(self):
        share = "fake_share"
        host = "fake_host"
        version = api_versions.APIVersion('2.29')
        manager = shares.ShareManager(
            api=fakes.FakeClient(api_version=version))

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.migration_start(
                share, host, force_host_assisted_migration=True,
                preserve_metadata=True, writable=True, nondisruptive=True,
                preserve_snapshots=True)
            manager._action.assert_called_once_with(
                'migration_start', share, {
                    "host": host,
                    "force_host_assisted_migration": True,
                    "preserve_metadata": True,
                    "writable": True,
                    "nondisruptive": True,
                    "preserve_snapshots": True,
                    "new_share_network_id": None,
                    "new_share_type_id": None,
                })

            self.assertEqual("fake", result)

    def test_migration_complete(self):
        share = "fake_share"
        manager = shares.ShareManager(api=fakes.FakeClient())

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.migration_complete(share)

            manager._action.assert_called_once_with(
                "migration_complete", share)
            self.assertEqual("fake", result)

    def test_migration_get_progress(self):
        share = "fake_share"
        manager = shares.ShareManager(api=fakes.FakeClient())

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.migration_get_progress(share)

            manager._action.assert_called_once_with(
                "migration_get_progress", share)
            self.assertEqual("fake", result)

    def test_reset_task_state(self):
        share = "fake_share"
        state = "fake_state"
        manager = shares.ShareManager(api=fakes.FakeClient())

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.reset_task_state(share, state)

            manager._action.assert_called_once_with(
                "reset_task_state", share, {'task_state': state})
            self.assertEqual("fake", result)

    def test_migration_cancel(self):
        share = "fake_share"
        manager = shares.ShareManager(api=fakes.FakeClient())

        with mock.patch.object(manager, "_action",
                               mock.Mock(return_value="fake")):
            result = manager.migration_cancel(share)

            manager._action.assert_called_once_with(
                "migration_cancel", share)
            self.assertEqual("fake", result)
