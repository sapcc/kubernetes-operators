# Copyright (c) 2017 Hitachi Data Systems
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
from tempest.lib import exceptions as tempest_lib_exc
import testtools

from manilaclient import config
from manilaclient.tests.functional import base
from manilaclient.tests.functional import utils

CONF = config.CONF


@utils.skip_if_microversion_not_supported('2.32')
class SnapshotAccessReadBase(base.BaseTestCase):
    protocol = None

    @classmethod
    def setUpClass(cls):
        super(SnapshotAccessReadBase, cls).setUpClass()
        if cls.protocol not in CONF.enable_protocols:
            message = "%s tests are disabled." % cls.protocol
            raise cls.skipException(message)
        cls.access_types = CONF.access_types_mapping.get(
            cls.protocol, '').split(' ')
        if not cls.access_types:
            raise cls.skipException("No access types were provided for %s "
                                    "snapshot access tests." % cls.protocol)

        cls.share = cls.create_share(share_protocol=cls.protocol,
                                     public=True,
                                     cleanup_in_class=True,
                                     client=cls.get_user_client())
        int_range = range(0, 10)

        cls.access_to = {
            'ip': ['99.88.77.%d' % i for i in int_range],
            'user': ['foo_user_%d' % i for i in int_range],
            'cert': ['tenant_%d.example.com' % i for i in int_range],
        }

    def _test_create_list_access_rule_for_snapshot(self, snapshot_id):
        access = []
        access_type = self.access_types[0]

        for i in range(5):
            access_ = self.user_client.snapshot_access_allow(
                snapshot_id, access_type,
                self.access_to[access_type][i])
            access.append(access_)

        return access

    def test_create_list_access_rule_for_snapshot(self):
        snapshot = self.create_snapshot(share=self.share['id'],
                                        client=self.get_user_client(),
                                        cleanup_in_class=False)

        access = self._test_create_list_access_rule_for_snapshot(
            snapshot['id'])

        access_list = self.user_client.list_access(
            snapshot['id'], is_snapshot=True)

        for i in range(5):
            self.assertIn(access[i]['id'],
                          [access_list[j]['id'] for j in range(5)])
            self.assertIn(access[i]['access_type'],
                          [access_list[j]['access_type'] for j in range(5)])
            self.assertIn(access[i]['access_to'],
                          [access_list[j]['access_to'] for j in range(5)])
            self.assertIsNotNone(access_list[i]['access_type'])
            self.assertIsNotNone(access_list[i]['access_to'])

    def test_create_list_access_rule_for_snapshot_select_column(self):
        snapshot = self.create_snapshot(share=self.share['id'],
                                        client=self.get_user_client(),
                                        cleanup_in_class=False)

        self._test_create_list_access_rule_for_snapshot(snapshot['id'])

        access_list = self.user_client.list_access(
            snapshot['id'], columns="access_type,access_to", is_snapshot=True)

        self.assertTrue(any(x['Access_Type'] is not None for x in access_list))
        self.assertTrue(any(x['Access_To'] is not None for x in access_list))

    def _create_delete_access_rule(self, snapshot_id, access_type, access_to):

        if access_type not in self.access_types:
            raise self.skipException(
                "'%(access_type)s' access rules is disabled for protocol "
                "'%(protocol)s'." % {"access_type": access_type,
                                     "protocol": self.protocol})

        access = self.user_client.snapshot_access_allow(
            snapshot_id, access_type, access_to)

        self.assertEqual(access_type, access.get('access_type'))
        self.assertEqual(access_to.replace('\\\\', '\\'),
                         access.get('access_to'))

        self.user_client.wait_for_access_rule_status(
            snapshot_id, access['id'], is_snapshot=True)
        self.user_client.snapshot_access_deny(snapshot_id, access['id'])
        self.user_client.wait_for_access_rule_deletion(
            snapshot_id, access['id'], is_snapshot=True)

        self.assertRaises(tempest_lib_exc.NotFound,
                          self.user_client.get_access, snapshot_id,
                          access['id'], is_snapshot=True)

    def test_create_delete_snapshot_ip_access_rule(self):
        snapshot = self.create_snapshot(share=self.share['id'],
                                        client=self.get_user_client(),
                                        cleanup_in_class=False)
        self._create_delete_access_rule(
            snapshot['id'], 'ip', self.access_to['ip'][0])

    def test_create_delete_snapshot_user_access_rule(self):
        snapshot = self.create_snapshot(share=self.share['id'],
                                        client=self.get_user_client(),
                                        cleanup_in_class=False)
        self._create_delete_access_rule(
            snapshot['id'], 'user', CONF.username_for_user_rules)

    def test_create_delete_snapshot_cert_access_rule(self):
        snapshot = self.create_snapshot(share=self.share['id'],
                                        client=self.get_user_client(),
                                        cleanup_in_class=False)
        self._create_delete_access_rule(
            snapshot['id'], 'cert', self.access_to['cert'][0])


@testtools.skipUnless(CONF.run_snapshot_tests and
                      CONF.run_mount_snapshot_tests,
                      "Snapshots or mountable snapshots tests are disabled.")
class NFSSnapshotAccessTest(SnapshotAccessReadBase):
    protocol = 'nfs'


@testtools.skipUnless(CONF.run_snapshot_tests and
                      CONF.run_mount_snapshot_tests,
                      "Snapshots or mountable snapshots tests are disabled.")
class CIFSSnapshotAccessTest(SnapshotAccessReadBase):
    protocol = 'cifs'


@testtools.skipUnless(CONF.run_snapshot_tests and
                      CONF.run_mount_snapshot_tests,
                      "Snapshots or mountable snapshots tests are disabled.")
class GlusterFSSnapshotAccessTest(SnapshotAccessReadBase):
    protocol = 'glusterfs'


@testtools.skipUnless(CONF.run_snapshot_tests and
                      CONF.run_mount_snapshot_tests,
                      "Snapshots or mountable snapshots tests are disabled.")
class HDFSSnapshotAccessTest(SnapshotAccessReadBase):
    protocol = 'hdfs'


@testtools.skipUnless(CONF.run_snapshot_tests and
                      CONF.run_mount_snapshot_tests,
                      "Snapshots or mountable snapshots tests are disabled.")
class MAPRFSSnapshotAccessTest(SnapshotAccessReadBase):
    protocol = 'maprfs'


def load_tests(loader, tests, _):
    result = []
    for test_case in tests:
        if type(test_case._tests[0]) is SnapshotAccessReadBase:
            continue
        result.append(test_case)
    return loader.suiteClass(result)
