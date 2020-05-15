# Copyright 2015 Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ast

import ddt
from tempest.lib import exceptions as tempest_lib_exc

from manilaclient import api_versions
from manilaclient import config
from manilaclient.tests.functional import base

CONF = config.CONF


@ddt.ddt
class ShareAccessReadWriteBase(base.BaseTestCase):
    protocol = None
    access_level = None

    @classmethod
    def setUpClass(cls):
        super(ShareAccessReadWriteBase, cls).setUpClass()
        if cls.protocol not in CONF.enable_protocols:
            message = "%s tests are disabled." % cls.protocol
            raise cls.skipException(message)
        if cls.access_level not in CONF.access_levels_mapping.get(
                cls.protocol, '').split(' '):
            raise cls.skipException("%(level)s tests for %(protocol)s share "
                                    "access are disabled." % {
                                        'level': cls.access_level,
                                        'protocol': cls.protocol
                                    })
        cls.access_types = CONF.access_types_mapping.get(
            cls.protocol, '').split(' ')
        if not cls.access_types:
            raise cls.skipException("No access levels were provided for %s "
                                    "share access tests." % cls.protoco)

        cls.share = cls.create_share(share_protocol=cls.protocol,
                                     public=True,
                                     cleanup_in_class=True)
        cls.share_id = cls.share['id']

        # NOTE(vponomaryov): increase following int range when significant
        # amount of new tests is added.
        int_range = range(20, 50)
        cls.access_to = {
            # NOTE(vponomaryov): list of unique values is required for ability
            # to create lots of access rules for one share using different
            # API microversions.
            'ip': ['99.88.77.%d' % i for i in int_range],
            # NOTE(vponomaryov): following users are fakes and access rules
            # that use it are expected to fail, but they are used only for
            # API testing.
            'user': ['foo_user_%d' % i for i in int_range],
            'cert': ['tenant_%d.example.com' % i for i in int_range],
            'ipv6': ['2001:db8::%d' % i for i in int_range],
        }

    def _test_create_list_access_rule_for_share(
            self, microversion, metadata=None):
        access_type = self.access_types[0]

        access = self.user_client.access_allow(
            self.share['id'], access_type, self.access_to[access_type].pop(),
            self.access_level, metadata=metadata, microversion=microversion)

        return access

    @ddt.data(*set([
        "1.0", "2.0", "2.6", "2.7", "2.21", "2.33", "2.44", "2.45",
        api_versions.MAX_VERSION]))
    def test_create_list_access_rule_for_share(self, microversion):
        self.skip_if_microversion_not_supported(microversion)
        access = self._test_create_list_access_rule_for_share(
            microversion=microversion)
        access_list = self.user_client.list_access(
            self.share['id'],
            microversion=microversion
        )
        self.assertTrue(any(
            [item for item in access_list if access['id'] == item['id']]))
        self.assertTrue(any(a['access_type'] is not None for a in access_list))
        self.assertTrue(any(a['access_to'] is not None for a in access_list))
        self.assertTrue(any(a['access_level'] is not None
                        for a in access_list))
        if (api_versions.APIVersion(microversion) >=
                api_versions.APIVersion("2.33")):
            self.assertTrue(
                all(all(key in access for key in (
                    'access_key', 'created_at', 'updated_at'))
                    for access in access_list))
        elif (api_versions.APIVersion(microversion) >=
                api_versions.APIVersion("2.21")):
            self.assertTrue(all('access_key' in a for a in access_list))
        else:
            self.assertTrue(all('access_key' not in a for a in access_list))

    @ddt.data("1.0", "2.0", "2.6", "2.7")
    def test_create_list_access_rule_for_share_select_column(
            self,
            microversion):
        self.skip_if_microversion_not_supported(microversion)
        self._test_create_list_access_rule_for_share(
            microversion=microversion)
        access_list = self.user_client.list_access(
            self.share['id'],
            columns="access_type,access_to",
            microversion=microversion
        )
        self.assertTrue(any(a['Access_Type'] is not None for a in access_list))
        self.assertTrue(any(a['Access_To'] is not None for a in access_list))
        self.assertTrue(all('Access_Level' not in a for a in access_list))
        self.assertTrue(all('access_level' not in a for a in access_list))

    def _create_delete_access_rule(self, share_id, access_type, access_to,
                                   microversion=None):
        self.skip_if_microversion_not_supported(microversion)
        if access_type not in self.access_types:
            raise self.skipException(
                "'%(access_type)s' access rules is disabled for protocol "
                "'%(protocol)s'." % {"access_type": access_type,
                                     "protocol": self.protocol})

        access = self.user_client.access_allow(
            share_id, access_type, access_to, self.access_level,
            microversion=microversion)

        self.assertEqual(share_id, access.get('share_id'))
        self.assertEqual(access_type, access.get('access_type'))
        self.assertEqual(access_to.replace('\\\\', '\\'),
                         access.get('access_to'))
        self.assertEqual(self.access_level, access.get('access_level'))
        if (api_versions.APIVersion(microversion) >=
                api_versions.APIVersion("2.33")):
            self.assertIn('access_key', access)
            self.assertIn('created_at', access)
            self.assertIn('updated_at', access)
        elif (api_versions.APIVersion(microversion) >=
                api_versions.APIVersion("2.21")):
            self.assertIn('access_key', access)
        else:
            self.assertNotIn('access_key', access)

        self.user_client.wait_for_access_rule_status(share_id, access['id'])
        self.user_client.access_deny(share_id, access['id'])
        self.user_client.wait_for_access_rule_deletion(share_id, access['id'])

        self.assertRaises(tempest_lib_exc.NotFound,
                          self.user_client.get_access, share_id, access['id'])

    @ddt.data(*set(["2.45", api_versions.MAX_VERSION]))
    def test_create_list_access_rule_with_metadata(self, microversion):
        self.skip_if_microversion_not_supported(microversion)

        md1 = {"key1": "value1", "key2": "value2"}
        md2 = {"key3": "value3", "key4": "value4"}
        self._test_create_list_access_rule_for_share(
            metadata=md1, microversion=microversion)
        access = self._test_create_list_access_rule_for_share(
            metadata=md2, microversion=microversion)
        access_list = self.user_client.list_access(
            self.share['id'], metadata={"key4": "value4"},
            microversion=microversion)
        self.assertEqual(1, len(access_list))
        # Verify share metadata
        get_access = self.user_client.access_show(
            access_list[0]['id'], microversion=microversion)
        metadata = ast.literal_eval(get_access['metadata'])
        self.assertEqual(2, len(metadata))
        self.assertIn('key3', metadata)
        self.assertIn('key4', metadata)
        self.assertEqual(md2['key3'], metadata['key3'])
        self.assertEqual(md2['key4'], metadata['key4'])
        self.assertEqual(access['id'], access_list[0]['id'])

        self.user_client.access_deny(access['share_id'], access['id'])
        self.user_client.wait_for_access_rule_deletion(access['share_id'],
                                                       access['id'])

    @ddt.data(*set(["2.45", api_versions.MAX_VERSION]))
    def test_create_update_show_access_rule_with_metadata(self, microversion):
        self.skip_if_microversion_not_supported(microversion)

        md1 = {"key1": "value1", "key2": "value2"}
        md2 = {"key3": "value3", "key2": "value4"}
        # create a access rule with metadata
        access = self._test_create_list_access_rule_for_share(
            metadata=md1, microversion=microversion)
        # get the access rule
        get_access = self.user_client.access_show(
            access['id'], microversion=microversion)
        # verify access rule
        self.assertEqual(access['id'], get_access['id'])
        self.assertEqual(md1, ast.literal_eval(get_access['metadata']))

        # update access rule metadata
        self.user_client.access_set_metadata(
            access['id'], metadata=md2, microversion=microversion)
        get_access = self.user_client.access_show(
            access['id'], microversion=microversion)

        # verify access rule after update access rule metadata
        self.assertEqual(
            {"key1": "value1", "key2": "value4", "key3": "value3"},
            ast.literal_eval(get_access['metadata']))
        self.assertEqual(access['id'], get_access['id'])

    @ddt.data(*set(["2.45", api_versions.MAX_VERSION]))
    def test_delete_access_rule_metadata(self, microversion):
        self.skip_if_microversion_not_supported(microversion)

        md = {"key1": "value1", "key2": "value2"}
        # create a access rule with metadata
        access = self._test_create_list_access_rule_for_share(
            metadata=md, microversion=microversion)
        # get the access rule
        get_access = self.user_client.access_show(
            access['id'], microversion=microversion)

        # verify access rule
        self.assertEqual(access['id'], get_access['id'])
        self.assertEqual(md, ast.literal_eval(get_access['metadata']))

        # delete access rule metadata
        self.user_client.access_unset_metadata(
            access['id'], keys=["key1", "key2"], microversion=microversion)
        get_access = self.user_client.access_show(
            access['id'], microversion=microversion)

        # verify access rule after delete access rule metadata
        self.assertEqual({}, ast.literal_eval(get_access['metadata']))
        self.assertEqual(access['id'], get_access['id'])

    @ddt.data("1.0", "2.0", "2.6", "2.7", "2.21", "2.33")
    def test_create_delete_ip_access_rule(self, microversion):
        self._create_delete_access_rule(
            self.share_id, 'ip', self.access_to['ip'].pop(), microversion)

    @ddt.data("1.0", "2.0", "2.6", "2.7", "2.21", "2.33")
    def test_create_delete_user_access_rule(self, microversion):
        self._create_delete_access_rule(
            self.share_id, 'user', CONF.username_for_user_rules, microversion)

    @ddt.data("1.0", "2.0", "2.6", "2.7", "2.21", "2.33")
    def test_create_delete_cert_access_rule(self, microversion):
        self._create_delete_access_rule(
            self.share_id, 'cert', self.access_to['cert'].pop(), microversion)

    @ddt.data("2.38", api_versions.MAX_VERSION)
    def test_create_delete_ipv6_access_rule(self, microversion):
        self._create_delete_access_rule(
            self.share_id, 'ip', self.access_to['ipv6'].pop(), microversion)


class NFSShareRWAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'nfs'
    access_level = 'rw'


class NFSShareROAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'nfs'
    access_level = 'ro'


class CIFSShareRWAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'cifs'
    access_level = 'rw'


class CIFSShareROAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'cifs'
    access_level = 'ro'


class GlusterFSShareRWAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'glusterfs'
    access_level = 'rw'


class GlusterFSShareROAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'glusterfs'
    access_level = 'ro'


class HDFSShareRWAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'hdfs'
    access_level = 'rw'


class HDFSShareROAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'hdfs'
    access_level = 'ro'


class MAPRFSShareRWAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'maprfs'
    access_level = 'rw'


class MAPRFSShareROAccessReadWriteTest(ShareAccessReadWriteBase):
    protocol = 'maprfs'
    access_level = 'ro'


def load_tests(loader, tests, _):
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is ShareAccessReadWriteBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
