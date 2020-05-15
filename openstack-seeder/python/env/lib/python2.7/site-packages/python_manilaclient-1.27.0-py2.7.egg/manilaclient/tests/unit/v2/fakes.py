# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2011 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import manilaclient
from manilaclient import api_versions
from manilaclient.tests.unit.v2 import fake_clients as fakes
from manilaclient.v2 import client


class FakeClient(fakes.FakeClient):

    def __init__(self, *args, **kwargs):
        client.Client.__init__(
            self,
            manilaclient.API_MAX_VERSION,
            'username',
            'password',
            'project_id',
            'auth_url',
            input_auth_token='token',
            extensions=kwargs.get('extensions'),
            service_catalog_url='http://localhost:8786',
            api_version=kwargs.get("api_version", manilaclient.API_MAX_VERSION)
        )
        self.client = FakeHTTPClient(**kwargs)

fake_share_instance = {
    'id': 1234,
    'share_id': 'fake',
    'status': 'available',
    'availability_zone': 'fake',
    'share_network_id': 'fake',
    'share_server_id': 'fake',
}


def get_fake_export_location():
    return {
        'uuid': 'foo_el_uuid',
        'path': '/foo/el/path',
        'share_instance_id': 'foo_share_instance_id',
        'is_admin_only': False,
        'created_at': '2015-12-17T13:14:15Z',
        'updated_at': '2015-12-17T14:15:16Z',
    }


def get_fake_snapshot_export_location():
    return {
        'uuid': 'foo_el_uuid',
        'path': '/foo/el/path',
        'share_snapshot_instance_id': 'foo_share_instance_id',
        'is_admin_only': False,
        'created_at': '2017-01-17T13:14:15Z',
        'updated_at': '2017-01-17T14:15:16Z',
    }


class FakeHTTPClient(fakes.FakeHTTPClient):

    def get_(self, **kw):
        body = {
            "versions": [
                {
                    "status": "CURRENT",
                    "updated": "2015-07-30T11:33:21Z",
                    "links": [
                        {
                            "href": "http://docs.openstack.org/",
                            "type": "text/html",
                            "rel": "describedby",
                        },
                        {
                            "href": "http://localhost:8786/v2/",
                            "rel": "self",
                        }
                    ],
                    "min_version": "2.0",
                    "version": self.default_headers[
                        "X-Openstack-Manila-Api-Version"],
                    "id": "v2.0",
                }
            ]
        }
        return (200, {}, body)

    def get_availability_zones(self):
        availability_zones = {
            "availability_zones": [
                {"id": "368c5780-ad72-4bcf-a8b6-19e45f4fafoo",
                 "name": "foo",
                 "created_at": "2016-07-08T14:13:12.000000",
                 "updated_at": "2016-07-08T15:14:13.000000"},
                {"id": "368c5780-ad72-4bcf-a8b6-19e45f4fabar",
                 "name": "bar",
                 "created_at": "2016-07-08T14:13:12.000000",
                 "updated_at": "2016-07-08T15:14:13.000000"},
            ]
        }
        return (200, {}, availability_zones)

    def get_os_services(self, **kw):
        services = {
            "services": [
                {"status": "enabled",
                 "binary": "manila-scheduler",
                 "zone": "foozone",
                 "state": "up",
                 "updated_at": "2015-10-09T13:54:09.000000",
                 "host": "lucky-star",
                 "id": 1},
                {"status": "enabled",
                 "binary": "manila-share",
                 "zone": "foozone",
                 "state": "up",
                 "updated_at": "2015-10-09T13:54:05.000000",
                 "host": "lucky-star",
                 "id": 2},
            ]
        }
        return (200, {}, services)

    get_services = get_os_services

    def put_os_services_enable(self, **kw):
        return (200, {}, {'host': 'foo', 'binary': 'manila-share',
                          'disabled': False})

    put_services_enable = put_os_services_enable

    def put_os_services_disable(self, **kw):
        return (200, {}, {'host': 'foo', 'binary': 'manila-share',
                          'disabled': True})

    put_services_disable = put_os_services_disable

    def get_v2(self, **kw):
        body = {
            "versions": [
                {
                    "status": "CURRENT",
                    "updated": "2015-07-30T11:33:21Z",
                    "links": [
                        {
                            "href": "http://docs.openstack.org/",
                            "type": "text/html",
                            "rel": "describedby",
                        },
                        {
                            "href": "http://localhost:8786/v2/",
                            "rel": "self",
                        }
                    ],
                    "min_version": "2.0",
                    "version": "2.5",
                    "id": "v1.0",
                }
            ]
        }
        return (200, {}, body)

    def get_shares_1234(self, **kw):
        share = {'share': {'id': 1234, 'name': 'sharename'}}
        return (200, {}, share)

    def get_share_servers_1234(self, **kw):
        share_servers = {
            'share_server': {
                'id': 1234,
                'share_network_id': 'fake_network_id_1',
                'backend_details': {},
            },
        }
        return (200, {}, share_servers)

    def get_share_servers_5678(self, **kw):
        share_servers = {
            'share_server': {
                'id': 5678,
                'share_network_id': 'fake_network_id_2',
            },
        }
        return (200, {}, share_servers)

    def get_shares_1111(self, **kw):
        share = {'share': {'id': 1111, 'name': 'share1111'}}
        return (200, {}, share)

    def get_shares(self, **kw):
        endpoint = "http://127.0.0.1:8786/v2"
        share_id = '1234'
        shares = {
            'shares': [
                {
                    'id': share_id,
                    'name': 'sharename',
                    'links': [
                        {"href": endpoint + "/fake_project/shares/" + share_id,
                         "rel": "self"},
                    ],
                },
            ]
        }
        return (200, {}, shares)

    def get_shares_detail(self, **kw):
        endpoint = "http://127.0.0.1:8786/v2"
        share_id = '1234'
        shares = {
            'shares': [
                {
                    'id': share_id,
                    'name': 'sharename',
                    'status': 'fake_status',
                    'size': 1,
                    'host': 'fake_host',
                    'export_location': 'fake_export_location',
                    'snapshot_id': 'fake_snapshot_id',
                    'links': [
                        {"href": endpoint + "/fake_project/shares/" + share_id,
                         "rel": "self"},
                    ],
                },
            ],
            'count': 2,
        }
        return (200, {}, shares)

    def get_snapshots_1234(self, **kw):
        snapshot = {'snapshot': {'id': 1234, 'name': 'sharename'}}
        return (200, {}, snapshot)

    def get_share_servers(self, **kw):
        share_servers = {
            'share_servers': [
                {
                    'id': 1234,
                    'host': 'fake_host',
                    'status': 'fake_status',
                    'share_network': 'fake_share_nw',
                    'project_id': 'fake_project_id',
                    'updated_at': 'fake_updated_at',
                    'name': 'fake_name',
                    'share_name': 'fake_share_name',
                }
            ]
        }
        return (200, {}, share_servers)

    def post_snapshots_1234_action(self, body, **kw):
        _body = None
        resp = 202
        assert len(list(body)) == 1
        action = list(body)[0]
        if action in ('reset_status', 'os-reset_status'):
            assert 'status' in body.get(
                'reset_status', body.get('os-reset_status'))
        elif action in ('force_delete', 'os-force_delete'):
            assert body[action] is None
        elif action in ('unmanage', ):
            assert body[action] is None
        elif action in 'allow_access':
            assert 'access_type' in body['allow_access']
            assert 'access_to' in body['allow_access']
            _body = {'snapshot_access': body['allow_access']}
        elif action in 'deny_access':
            assert 'access_id' in body['deny_access']
        else:
            raise AssertionError("Unexpected action: %s" % action)
        return (resp, {}, _body)

    post_snapshots_5678_action = post_snapshots_1234_action

    def post_snapshots_manage(self, body, **kw):
        _body = {'snapshot': {'id': 'fake'}}
        resp = 202

        if not ('share_id' in body['snapshot']
                and 'provider_location' in body['snapshot']
                and 'driver_options' in body['snapshot']):
            resp = 422

        result = (resp, {}, _body)
        return result

    def _share_instances(self):
        instances = {
            'share_instances': [
                fake_share_instance
            ]
        }
        return (200, {}, instances)

    def put_quota_sets_1234(self, *args, **kwargs):
        return (200, {}, {})

    def get_quota_sets_1234(self, *args, **kwargs):
        quota_set = {
            'quota_set': {
                'id': '1234',
                'shares': 50,
                'gigabytes': 1000,
                'snapshots': 50,
                'snapshot_gigabytes': 1000,
                'share_networks': 10,
            }
        }
        return (200, {}, quota_set)

    def get_quota_sets_1234_detail(self, *args, **kwargs):
        quota_set = {
            'quota_set': {
                'id': '1234',
                'shares': {'in_use': 0,
                           'limit': 50,
                           'reserved': 0},
                'gigabytes': {'in_use': 0,
                              'limit': 10000,
                              'reserved': 0},
                'snapshots': {'in_use': 0,
                              'limit': 50,
                              'reserved': 0},
                'snapshot_gigabytes': {'in_use': 0,
                                       'limit': 1000,
                                       'reserved': 0},
                'share_networks': {'in_use': 0,
                                   'limit': 10,
                                   'reserved': 0},
            }
        }
        return (200, {}, quota_set)

    def get_share_instances(self, **kw):
        return self._share_instances()

    def get_share_instances_1234_export_locations(self, **kw):
        export_locations = {
            'export_locations': [
                get_fake_export_location(),
            ]
        }
        return (200, {}, export_locations)

    get_shares_1234_export_locations = (
        get_share_instances_1234_export_locations)

    def get_share_instances_1234_export_locations_fake_el_uuid(self, **kw):
        export_location = {'export_location': get_fake_export_location()}
        return (200, {}, export_location)

    get_shares_1234_export_locations_fake_el_uuid = (
        get_share_instances_1234_export_locations_fake_el_uuid)

    def get_shares_fake_instances(self, **kw):
        return self._share_instances()

    def get_shares_1234_instances(self, **kw):
        return self._share_instances()

    def get_share_instances_1234(self):
        return (200, {}, {'share_instance': fake_share_instance})

    def post_share_instances_1234_action(self, body, **kw):
        _body = None
        resp = 202
        assert len(list(body)) == 1
        action = list(body)[0]
        if action in ('reset_status', 'os-reset_status'):
            assert 'status' in body.get(
                'reset_status', body.get('os-reset_status'))
        elif action == 'os-force_delete':
            assert body[action] is None
        else:
            raise AssertionError("Unexpected share action: %s" % action)
        return (resp, {}, _body)

    def get_snapshots(self, **kw):
        snapshots = {
            'snapshots': [
                {
                    'id': 1234,
                    'status': 'available',
                    'name': 'sharename',
                }
            ]
        }
        return (200, {}, snapshots)

    def get_snapshots_detail(self, **kw):
        snapshots = {'snapshots': [{
            'id': 1234,
            'created_at': '2012-08-27T00:00:00.000000',
            'share_size': 1,
            'share_id': 4321,
            'status': 'available',
            'name': 'sharename',
            'display_description': 'description',
            'share_proto': 'type',
            'export_location': 'location',
        }]}
        return (200, {}, snapshots)

    def post_os_share_manage(self, body, **kw):
        _body = {'share': {'id': 'fake'}}
        resp = 202

        if not ('service_host' in body['share']
                and 'share_type' in body['share']
                and 'export_path' in body['share']
                and 'protocol' in body['share']
                and 'driver_options' in body['share']):
            resp = 422

        result = (resp, {}, _body)
        return result

    post_shares_manage = post_os_share_manage

    def post_share_servers_manage(self, body, **kw):
        _body = {'share_server': {'id': 'fake'}}
        resp = 202

        if not ('host' in body['share_server']
                and 'share_network' in body['share_server']
                and 'identifier' in body['share_server']):
            resp = 422

        result = (resp, {}, _body)
        return result

    def post_share_servers_1234_action(self, body, **kw):
        _body = None
        assert len(list(body)) == 1
        action = list(body)[0]

        if action in ('reset_status', ):
            assert 'status' in body.get(
                'reset_status', body.get('os-reset_status'))
            _body = {
                'reset_status': {'status': body['reset_status']['status']}
            }
        elif action in ('unmanage', ):
            assert 'force' in body[action]

        resp = 202
        result = (resp, {}, _body)
        return result

    def post_os_share_unmanage_1234_unmanage(self, **kw):
        _body = None
        resp = 202
        result = (resp, {}, _body)
        return result

    def post_shares_1234_action(self, body, **kw):
        _body = None
        resp = 202
        assert len(list(body)) == 1
        action = list(body)[0]
        if action in ('os-allow_access', 'allow_access'):
            expected = ['access_to', 'access_type']
            actual = sorted(list(body[action]))
            err_msg = "expected '%s', actual is '%s'" % (expected, actual)
            assert expected == actual, err_msg
            _body = {'access': {}}
        elif action in ('os-deny_access', 'deny_access'):
            assert list(body[action]) == ['access_id']
        elif action in ('os-access_list', 'access_list'):
            assert body[action] is None
        elif action in ('os-reset_status', 'reset_status'):
            assert 'status' in body.get(
                'reset_status', body.get('os-reset_status'))
        elif action in ('os-force_delete', 'force_delete'):
            assert body[action] is None
        elif action in ('os-extend', 'os-shrink', 'extend', 'shrink'):
            assert body[action] is not None
            assert body[action]['new_size'] is not None
        elif action in ('unmanage', ):
            assert body[action] is None
        elif action in ('revert', ):
            assert body[action] is not None
            assert body[action]['snapshot_id'] is not None
        elif action in (
                'migration_cancel', 'migration_complete',
                'migration_get_progress'):
            assert body[action] is None
            if 'migration_get_progress' == action:
                _body = {'total_progress': 50}
                return 200, {}, _body
        elif action in (
                'os-migrate_share', 'migrate_share',
                'migration_start'):
            assert 'host' in body[action]
        elif action == 'reset_task_state':
            assert 'task_state' in body[action]
        else:
            raise AssertionError("Unexpected share action: %s" % action)
        return (resp, {}, _body)

    def post_shares_1111_action(self, body, **kw):
        _body = None
        resp = 202
        assert len(list(body)) == 1
        action = list(body)[0]
        if action in ('allow_access', 'os-allow_access'):
            expected = ['access_level', 'access_to', 'access_type']
            actual = sorted(list(body[action]))
            err_msg = "expected '%s', actual is '%s'" % (expected, actual)
            assert expected == actual, err_msg
            _body = {'access': {}}
        elif action in ('access_list', 'os-access_list'):
            assert body[action] is None
            _body = {
                'access_list': [{
                    'access_level': 'rw',
                    'state': 'active',
                    'id': '1122',
                    'access_type': 'ip',
                    'access_to': '10.0.0.7'
                }]
            }
        else:
            raise AssertionError("Unexpected share action: %s" % action)
        return (resp, {}, _body)

    def get_share_access_rules(self, **kw):
        access = {
            'access_list': [{
                'access_level': 'rw',
                'state': 'active',
                'id': '1122',
                'access_type': 'ip',
                'access_to': '10.0.0.7',
                'metadata': {'key1': 'v1'}
            }]
        }
        return (200, {}, access)

    def get_share_access_rules_9999(self, **kw):
        access = {
            'access': {
                'access_level': 'rw',
                'state': 'active',
                'id': '9999',
                'access_type': 'ip',
                'access_to': '10.0.0.7',
                'metadata': {'key1': 'v1'}
            }
        }
        return (200, {}, access)

    def put_share_access_rules_9999_metadata(self, **kw):
        return (200, {}, {'metadata': {'key1': 'v1', 'key2': 'v2'}})

    def delete_share_access_rules_9999_metadata_key1(self, **kw):
        return (200, {}, None)

    def get_shares_2222(self, **kw):
        share = {'share': {'id': 2222, 'name': 'sharename'}}
        return (200, {}, share)

    def post_shares_2222_action(self, body, **kw):
        return (202, {}, {'access': {}})

    def post_share_networks(self, **kwargs):
        return (202, {}, {'share_network': {}})

    def post_shares(self, **kwargs):
        return (202, {}, {'share': {}})

    def post_snapshots(self, **kwargs):
        return (202, {}, {'snapshot': {}})

    def delete_shares_1234(self, **kw):
        return (202, {}, None)

    def delete_snapshots_1234(self, **kwargs):
        return (202, {}, None)

    def delete_share_servers_1234(self, **kwargs):
        return (202, {}, None)

    def delete_share_servers_5678(self, **kwargs):
        return (202, {}, None)

    def delete_security_services_fake_security_service1(self, **kwargs):
        return (202, {}, None)

    def delete_security_services_fake_security_service2(self, **kwargs):
        return (202, {}, None)

    def delete_share_networks_fake_share_network1(self, **kwargs):
        return (202, {}, None)

    def delete_share_networks_fake_share_network2(self, **kwargs):
        return (202, {}, None)

    def delete_snapshots_fake_snapshot1(self, **kwargs):
        return (202, {}, None)

    def delete_snapshots_fake_snapshot2(self, **kwargs):
        return (202, {}, None)

    def post_snapshots_fake_snapshot_force1_action(self, **kwargs):
        return (202, {}, None)

    def post_snapshots_fake_snapshot_force2_action(self, **kwargs):
        return (202, {}, None)

    def delete_types_fake_type1(self, **kwargs):
        return (202, {}, None)

    def delete_types_fake_type2(self, **kwargs):
        return (202, {}, None)

    def delete_share_servers_fake_share_server1(self, **kwargs):
        return (202, {}, None)

    def delete_share_servers_fake_share_server2(self, **kwargs):
        return (202, {}, None)

    def put_share_networks_1111(self, **kwargs):
        share_network = {'share_network': {'id': 1111}}
        return (200, {}, share_network)

    def put_shares_1234(self, **kwargs):
        share = {'share': {'id': 1234, 'name': 'sharename'}}
        return (200, {}, share)

    def put_snapshots_1234(self, **kwargs):
        snapshot = {'snapshot': {'id': 1234, 'name': 'snapshot_name'}}
        return (200, {}, snapshot)

    def get_share_networks_1111(self, **kw):
        share_nw = {'share_network': {'id': 1111, 'name': 'fake_share_nw'}}
        return (200, {}, share_nw)

    def post_share_networks_1234_action(self, **kw):
        share_nw = {'share_network': {'id': 1111, 'name': 'fake_share_nw'}}
        return (200, {}, share_nw)

    def get_share_networks_detail(self, **kw):
        share_nw = {
            'share_networks': [
                {'id': 1234, 'name': 'fake_share_nw'},
                {'id': 4321, 'name': 'duplicated_name'},
                {'id': 4322, 'name': 'duplicated_name'},
            ]
        }
        return (200, {}, share_nw)

    def get_security_services(self, **kw):
        security_services = {
            'security_services': [
                {
                    'id': 1111,
                    'name': 'fake_security_service',
                    'type': 'fake_type',
                    'status': 'fake_status',
                },
            ],
        }
        return (200, {}, security_services)

    def get_security_services_detail(self, **kw):
        security_services = {
            'security_services': [
                {
                    'id': 1111,
                    'name': 'fake_security_service',
                    'description': 'fake_description',
                    'share_network_id': 'fake_share-network_id',
                    'user': 'fake_user',
                    'password': 'fake_password',
                    'domain': 'fake_domain',
                    'server': 'fake_server',
                    'dns_ip': 'fake_dns_ip',
                    'ou': 'fake_ou',
                    'type': 'fake_type',
                    'status': 'fake_status',
                    'project_id': 'fake_project_id',
                    'updated_at': 'fake_updated_at',
                },
            ],
        }
        return (200, {}, security_services)

    def get_security_services_1111(self, **kw):
        ss = {'security_service': {'id': 1111, 'name': 'fake_ss'}}
        return (200, {}, ss)

    def put_security_services_1111(self, **kwargs):
        ss = {'security_service': {'id': 1111, 'name': 'fake_ss'}}
        return (200, {}, ss)

    def get_scheduler_stats_pools(self, **kw):
        pools = {
            'pools': [
                {
                    'name': 'host1@backend1#pool1',
                    'host': 'host1',
                    'backend': 'backend1',
                    'pool': 'pool1',
                },
                {
                    'name': 'host1@backend1#pool2',
                    'host': 'host1',
                    'backend': 'backend1',
                    'pool': 'pool2',
                }
            ]
        }
        return (200, {}, pools)

    def get_scheduler_stats_pools_detail(self, **kw):
        pools = {
            'pools': [
                {
                    'name': 'host1@backend1#pool1',
                    'host': 'host1',
                    'backend': 'backend1',
                    'pool': 'pool1',
                    'capabilities': {'qos': True},
                },
                {
                    'name': 'host1@backend1#pool2',
                    'host': 'host1',
                    'backend': 'backend1',
                    'pool': 'pool2',
                    'capabilities': {'qos': False},
                }
            ]
        }
        return (200, {}, pools)

    fake_share_group = {
        'id': '1234',
        'availability_zone': 'nova',
        'share_network_id': None,
        'status': 'available',
        'name': 'share group name',
        'description': 'my share group',
    }

    def get_share_groups_detail(self, **kw):
        share_groups = {'share_groups': [self.fake_share_group]}
        return 200, {}, share_groups

    def get_share_groups_1234(self, **kw):
        share_group = {'share_group': self.fake_share_group}
        return 200, {}, share_group

    def put_share_groups_1234(self, **kwargs):
        share_group = {'share_group': self.fake_share_group}
        return 200, {}, share_group

    def delete_share_groups_1234(self, **kw):
        return 202, {}, None

    def post_share_groups_1234_action(self, **kw):
        return 202, {}, None

    def post_share_groups(self, body, **kw):
        share_group = {
            'share_group': {
                'id': 'fake-sg-id',
                'name': 'fake_name',
            }
        }
        return 202, {}, share_group

    fake_share_group_snapshot = {
        'id': '1234',
        'status': 'available',
        'name': 'share group name',
        'description': 'my share group',
    }

    def get_share_group_snapshots(self, **kw):
        sg_snapshots = {
            'share_group_snapshots': [self.fake_share_group_snapshot],
        }
        return 200, {}, sg_snapshots

    def get_share_group_snapshots_detail(self, **kw):
        sg_snapshots = {
            'share_group_snapshots': [self.fake_share_group_snapshot],
        }
        return 200, {}, sg_snapshots

    def get_share_group_snapshots_1234(self, **kw):
        sg_snapshot = {'share_group_snapshot': self.fake_share_group_snapshot}
        return 200, {}, sg_snapshot

    def put_share_group_snapshots_1234(self, **kwargs):
        sg_snapshot = {
            'share_group_snapshot': self.fake_share_group_snapshot,
        }
        return 200, {}, sg_snapshot

    def delete_share_group_snapshots_1234(self, **kw):
        return 202, {}, None

    def post_share_group_snapshots_1234_action(self, **kw):
        return 202, {}, None

    def post_share_group_snapshots(self, body, **kw):
        sg_snapshot = {
            'share_group_snapshot': {
                'id': 3,
                'name': 'cust_snapshot',
            }
        }
        return 202, {}, sg_snapshot

    fake_share_replica = {
        "id": "5678",
        "share_id": "1234",
        "availability_zone": "nova",
        "share_network_id": None,
        "export_locations": [],
        "share_server_id": None,
        "host": "",
        "status": "error",
        "replica_state": "error",
        "created_at": "2015-10-05T18:21:33.000000",
        "export_location": None,
    }

    def delete_share_replicas_1234(self, **kw):
        return (202, {}, None)

    def delete_share_replicas_fake_replica_0(self, **kw):
        return (202, {}, None)

    def delete_share_replicas_fake_replica_1(self, **kw):
        return (202, {}, None)

    def get_share_replicas_detail(self, **kw):
        replicas = {
            'share_replicas': [
                self.fake_share_replica,
            ]
        }
        return (200, {}, replicas)

    def get_share_replicas_5678(self, **kw):
        replicas = {'share_replica': self.fake_share_replica}
        return (200, {}, replicas)

    def get_share_replicas_5678_export_locations(self, **kw):
        export_locations = {
            'export_locations': [
                get_fake_export_location(),
            ]
        }
        return (200, {}, export_locations)

    def get_share_replicas_1234_export_locations(self, **kw):
        export_locations = {
            'export_locations': [
                get_fake_export_location(),
            ]
        }
        return (200, {}, export_locations)

    def get_share_replicas_1234_export_locations_fake_el_uuid(self, **kw):
        export_location = {'export_location': get_fake_export_location()}
        return (200, {}, export_location)

    def post_share_replicas(self, **kw):
        return (202, {}, {'share_replica': self.fake_share_replica})

    def post_share_replicas_1234_action(self, body, **kw):
        _body = None
        resp = 202
        assert len(list(body)) == 1
        action = list(body)[0]
        if action in ('reset_status', 'reset_replica_state'):
            attr = action.split('reset_')[1]
            assert attr in body.get(action)
        elif action in ('force_delete', 'resync', 'promote'):
            assert body[action] is None
        else:
            raise AssertionError("Unexpected share action: %s" % action)
        return (resp, {}, _body)

    #
    # Set/Unset metadata
    #
    def delete_shares_1234_metadata_test_key(self, **kw):
        return (204, {}, None)

    def delete_shares_1234_metadata_key1(self, **kw):
        return (204, {}, None)

    def delete_shares_1234_metadata_key2(self, **kw):
        return (204, {}, None)

    def post_shares_1234_metadata(self, **kw):
        return (204, {}, {'metadata': {'test_key': 'test_value'}})

    def put_shares_1234_metadata(self, **kw):
        return (200, {}, {"metadata": {"key1": "val1", "key2": "val2"}})

    def get_shares_1234_metadata(self, **kw):
        return (200, {}, {"metadata": {"key1": "val1", "key2": "val2"}})

    def get_types_default(self, **kw):
        return self.get_types_1(**kw)

    def get_types_1234(self, **kw):
        return (200, {}, {
            'share_type': {'id': 1,
                           'name': 'test-type-1',
                           'extra_specs': {'test': 'test'},
                           'required_extra_specs': {'test': 'test'}}})

    def get_types(self, **kw):
        req_version = self.default_headers['X-Openstack-Manila-Api-Version']
        if not isinstance(req_version, api_versions.APIVersion):
            req_version = api_versions.APIVersion(req_version)
        response_body = {
            'share_types': [{'id': 1,
                             'name': 'test-type-1',
                             'extra_specs': {'test1': 'test1'},
                             'required_extra_specs': {'test': 'test'}},
                            {'id': 2,
                             'name': 'test-type-2',
                             'extra_specs': {'test1': 'test1'},
                             'required_extra_specs': {'test': 'test'}}]
        }

        if req_version >= api_versions.APIVersion('2.46'):
            response_body['share_types'][0]['is_default'] = False
            response_body['share_types'][1]['is_default'] = False

        return 200, {}, response_body

    def get_types_1(self, **kw):
        return (200, {}, {'share_type': {
            'id': 1,
            'name': 'test-type-1',
            'extra_specs': {'test': 'test'},
            'required_extra_specs': {'test': 'test'}}})

    def get_types_2(self, **kw):
        return (200, {}, {'share_type': {
            'id': 2,
            'name': 'test-type-2',
            'extra_specs': {'test': 'test'},
            'required_extra_specs': {'test': 'test'}}})

    def get_types_3(self, **kw):
        return (200, {}, {
            'share_type': {
                'id': 3,
                'name': 'test-type-3',
                'extra_specs': {},
                'os-share-type-access:is_public': False
            }
        })

    def get_types_4(self, **kw):
        return (200, {}, {
            'share_type': {
                'id': 4,
                'name': 'test-type-3',
                'extra_specs': {},
                'os-share-type-access:is_public': True
            }
        })

    def post_types(self, body, **kw):
        share_type = body['share_type']
        required_extra_specs = {
            "driver_handles_share_servers": share_type[
                'extra_specs']['driver_handles_share_servers'],
        }
        return (202, {}, {
            'share_type': {
                'id': 3,
                'name': 'test-type-3',
                'is_default': False,
                'description': 'test description',
                'extra_specs': share_type['extra_specs'],
                'required_extra_specs': required_extra_specs,
            }
        })

    def post_types_3_action(self, body, **kw):
        _body = None
        resp = 202
        assert len(list(body)) == 1
        action = list(body)[0]
        if action == 'addProjectAccess':
            assert 'project' in body['addProjectAccess']
        elif action == 'removeProjectAccess':
            assert 'project' in body['removeProjectAccess']
        else:
            raise AssertionError('Unexpected action: %s' % action)
        return (resp, {}, _body)

    def post_types_1_extra_specs(self, body, **kw):
        assert list(body) == ['extra_specs']
        return (200, {}, {'extra_specs': {'k': 'v'}})

    def delete_types_1_extra_specs_k(self, **kw):
        return(204, {}, None)

    def delete_types_1(self, **kw):
        return (202, {}, None)

    def get_types_3_os_share_type_access(self, **kw):
        return (200, {}, {'share_type_access': [
            {'share_type_id': '11111111-1111-1111-1111-111111111111',
             'project_id': '00000000-0000-0000-0000-000000000000'}
        ]})

    get_types_3_share_type_access = get_types_3_os_share_type_access

    fake_snapshot_instance = {
        "id": "1234",
        "snapshot_id": "5678",
        "status": "error",
    }

    def get_snapshot_instances(self, **kw):
        instances = {
            'snapshot_instances': [
                self.fake_snapshot_instance,
            ]
        }
        return (200, {}, instances)

    def get_snapshot_instances_detail(self, **kw):
        instances = {
            'snapshot_instances': [
                {
                    'id': '1234',
                    'snapshot_id': '5679',
                    'created_at': 'fake',
                    'updated_at': 'fake',
                    'status': 'fake',
                    'share_id': 'fake',
                    'share_instance_id': 'fake',
                    'progress': 'fake',
                    'provider_location': 'fake',
                }
            ]
        }
        return (200, {}, instances)

    def get_snapshot_instances_1234(self, **kw):
        instances = {'snapshot_instance': self.fake_snapshot_instance}
        return (200, {}, instances)

    def get_snapshot_instances_1234_export_locations_fake_el_id(self, **kw):
        return (200, {}, {'share_snapshot_export_location': {
            'id': 'fake_id', 'path': '/fake_path'}})

    def get_snapshots_1234_export_locations_fake_el_id(self, **kw):
        return (200, {}, {'share_snapshot_export_location': {
            'id': 'fake_id', 'path': '/fake_path'}})

    def get_snapshot_instances_1234_export_locations(
            self, **kw):
        snapshot_export_location = {'share_snapshot_export_locations':
                                    [get_fake_export_location()]}
        return (200, {}, snapshot_export_location)

    def get_snapshots_1234_export_locations(self):
        snapshot_export_location = {'share_snapshot_export_locations':
                                    [get_fake_export_location()]}
        return (200, {}, snapshot_export_location)

    def get_snapshots_1234_access_list(self, **kw):
        access_list = {'snapshot_access_list': [{
            'state': 'active',
            'id': '1234',
            'access_type': 'ip',
            'access_to': '6.6.6.6'
        }]}
        return (200, {}, access_list)

    def post_snapshot_instances_1234_action(self, body, **kw):
        _body = None
        resp = 202
        assert len(list(body)) == 1
        action = list(body)[0]
        if action == 'reset_status':
            assert 'status' in body.get(action)
        else:
            raise AssertionError("Unexpected share action: %s" % action)
        return (resp, {}, _body)

    def get_share_group_types_default(self, **kw):
        return self.get_share_group_types_1(**kw)

    def get_share_group_types(self, **kw):
        share_group_types = {
            'share_group_types': [
                {
                    'id': 1,
                    'name': 'test-group-type-1',
                    'group_specs': {
                        'key1': 'value1',
                    },
                    'share_types': [
                        'type1',
                        'type2',
                    ],
                    'is_public': True,
                }, {
                    'id': 2,
                    'name': 'test-type-2',
                    'group_specs': {
                        'key2': 'value2',
                    },
                    'share_types': [
                        'type3',
                        'type4',
                    ],
                    'is_public': False,
                },
            ],
        }

        req_version = self.default_headers['X-Openstack-Manila-Api-Version']
        if req_version >= api_versions.APIVersion('2.46'):
            share_group_types['share_group_types'][0]['is_default'] = False
            share_group_types['share_group_types'][1]['is_default'] = False

        return 200, {}, share_group_types

    def get_share_group_types_1(self, **kw):
        share_group_type = {
            'share_group_type': {
                'id': 1,
                'name': 'test-group-type-1',
                'group_specs': {
                    'key1': 'value1',
                },
                'share_types': [
                    'type1',
                    'type2',
                ],
                'is_public': True,
            },
        }
        return 200, {}, share_group_type

    def get_share_group_types_2(self, **kw):
        share_group_type = {
            'share_type': {
                'id': 2,
                'name': 'test-group-type-2',
                'group_specs': {
                    'key2': 'value2',
                },
                'share_types': [
                    'type3',
                    'type4',
                ],
                'is_public': True,
            },
        }
        return 200, {}, share_group_type

    def post_share_group_types(self, body, **kw):
        share_group_type = {
            'share_group_type': {
                'id': 1,
                'name': 'test-group-type-1',
                'share_types': body['share_group_type']['share_types'],
                'is_public': True,
            },
        }
        return 202, {}, share_group_type

    def post_share_group_types_1234_action(self, body, **kw):
        assert len(list(body)) == 1
        action = list(body)[0]
        if action == 'addProjectAccess':
            assert 'project' in body['addProjectAccess']
        elif action == 'removeProjectAccess':
            assert 'project' in body['removeProjectAccess']
        else:
            raise AssertionError('Unexpected action: %s' % action)
        return 202, {}, None

    def post_share_group_types_1_specs(self, body, **kw):
        assert list(body) == ['group_specs']
        return 200, {}, {'group_specs': {'k': 'v'}}

    def delete_share_group_types_1_specs_k(self, **kw):
        return 204, {}, None

    def delete_share_group_types_1234(self, **kw):
        return 202, {}, None

    def get_share_group_types_1234_access(self, **kw):
        sg_type_access = {
            'share_group_type_access': [{
                'group_type_id': '11111111-1111-1111-1111-111111111111',
                'project_id': '00000000-0000-0000-0000-000000000000',
            }],
        }
        return 200, {}, sg_type_access

    fake_message = {
        'id': 'fake message id',
        'action_id': '001',
        'detail_id': '002',
        'user_message': 'user message',
        'message_level': 'ERROR',
        'resource_type': 'SHARE',
        'resource_id': 'resource id',
        'created_at': '2015-08-27T09:49:58-05:00',
        'expires_at': '2015-09-27T09:49:58-05:00',
        'request_id': 'req-936666d2-4c8f-4e41-9ac9-237b43f8b848',
    }

    def get_messages(self, **kw):
        messages = {
            'messages': [self.fake_message],
        }
        return 200, {}, messages

    def get_messages_1234(self, **kw):
        message = {'message': self.fake_message}
        return 200, {}, message

    def delete_messages_1234(self, **kw):
        return 202, {}, None

    def delete_messages_5678(self, **kw):
        return 202, {}, None


def fake_create(url, body, response_key):
    return {'url': url, 'body': body, 'resp_key': response_key}


def fake_update(url, body, response_key):
    return {'url': url, 'body': body, 'resp_key': response_key}


class FakeQuotaSet(object):

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def to_dict(self):
        return self.dictionary


class ShareNetwork(object):
    id = 'fake share network id'
    name = 'fake share network name'


class ShareType(object):
    id = 'fake share type id'
    name = 'fake share type name'


class ShareGroupType(object):
    id = 'fake group type id'
    name = 'fake group type name'
    share_types = [ShareType().id]
    is_public = False


class ShareGroupTypeAccess(object):
    id = 'fake group type access id'
    name = 'fake group type access name'


class ShareGroup(object):
    id = 'fake group id'
    share_types = [ShareType().id]
    group_type_id = ShareGroupType().id
    share_network_id = ShareNetwork().id
    name = 'fake name'
    description = 'fake description'
    availability_zone = 'fake az'


class ShareGroupSnapshot(object):
    id = 'fake group snapshot id'
    share_group_id = ShareGroup().id,
    share_network_id = ShareNetwork().id
    name = 'fake name'
    description = 'fake description'


class Message(object):
    id = 'fake message id'
    action_id = '001'
    detail_id = '002'
    user_message = 'user message'
    message_level = 'ERROR'
    resource_type = 'SHARE'
    resource_id = 'resource id'
    created_at = '2015-08-27T09:49:58-05:00'
    expires_at = '2015-09-27T09:49:58-05:00'
    request_id = 'req-936666d2-4c8f-4e41-9ac9-237b43f8b848'
