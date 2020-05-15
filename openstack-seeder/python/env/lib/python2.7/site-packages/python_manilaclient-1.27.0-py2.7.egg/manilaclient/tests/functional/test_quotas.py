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

from random import randint

import ddt
from tempest.lib.cli import output_parser
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions

from manilaclient import api_versions
from manilaclient.tests.functional import base
from manilaclient.tests.functional import utils


def _get_share_type_quota_values(project_quota_value):
    project_quota_value = int(project_quota_value)
    if project_quota_value == -1:
        return randint(1, 999)
    elif project_quota_value == 0:
        return 0
    else:
        return project_quota_value - 1


@ddt.ddt
@utils.skip_if_microversion_not_supported("2.39")
class QuotasReadWriteTest(base.BaseTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()
        self.microversion = "2.39"
        self.project_id = self.admin_client.get_project_id(
            self.admin_client.tenant_name)

        # Create share type
        self.share_type = self.create_share_type(
            name=data_utils.rand_name("manilaclient_functional_test"),
            driver_handles_share_servers=False,
            is_public=True,
            microversion=self.microversion,
            cleanup_in_class=False,
        )
        self.st_id = self.share_type["ID"]

    def _verify_current_st_quotas_equal_to(self, quotas, microversion):
        # Read share type quotas
        cmd = 'quota-show --tenant-id %s --share-type %s' % (
            self.project_id, self.st_id)
        st_quotas_raw = self.admin_client.manila(
            cmd, microversion=microversion)
        st_quotas = output_parser.details(st_quotas_raw)

        # Verify that quotas
        self.assertGreater(len(st_quotas), 3)
        for key, value in st_quotas.items():
            if key not in ('shares', 'gigabytes', 'snapshots',
                           'snapshot_gigabytes'):
                continue
            self.assertIn(key, quotas)
            self.assertEqual(int(quotas[key]), int(value))

    def _verify_current_quotas_equal_to(self, quotas, microversion):
        # Read quotas
        cmd = 'quota-show --tenant-id %s' % self.project_id
        quotas_raw = self.admin_client.manila(
            cmd, microversion=microversion)
        quotas = output_parser.details(quotas_raw)

        # Verify that quotas
        self.assertGreater(len(quotas), 3)
        for key, value in quotas.items():
            if key not in ('shares', 'gigabytes', 'snapshots',
                           'snapshot_gigabytes',
                           'share_groups', 'share_group_snapshots'):
                continue
            self.assertIn(key, quotas)
            self.assertEqual(int(quotas[key]), int(value))

    @ddt.data(*set([
        "2.40", api_versions.MAX_VERSION,
    ]))
    def test_update_quotas_for_share_groups(self, microversion):
        if not utils.is_microversion_supported(microversion):
            msg = "Microversion '%s' not supported." % microversion
            raise self.skipException(msg)

        # Get default quotas
        cmd = 'quota-defaults'
        quotas_raw = self.admin_client.manila(cmd, microversion=microversion)
        default_quotas = output_parser.details(quotas_raw)

        # Get project quotas
        cmd = 'quota-show --tenant-id %s ' % self.project_id
        quotas_raw = self.admin_client.manila(cmd, microversion=microversion)
        p_quotas = output_parser.details(quotas_raw)

        # Define custom share group quotas for project
        p_custom_quotas = {
            'share_groups': -1 if int(p_quotas['share_groups']) != -1 else 999,
            'share_group_snapshots': -1 if int(
                p_quotas['share_group_snapshots']) != -1 else 999,
        }

        # Update share group quotas for project
        cmd = ('quota-update %s --share-groups %s '
               '--share-group-snapshots %s') % (
            self.project_id,
            p_custom_quotas['share_groups'],
            p_custom_quotas['share_group_snapshots'],
        )
        self.admin_client.manila(cmd, microversion=microversion)

        # Verify quotas
        self._verify_current_quotas_equal_to(p_custom_quotas, microversion)

        # Reset quotas
        cmd = 'quota-delete --tenant-id %s --share-type %s' % (
            self.project_id, self.st_id)
        self.admin_client.manila(cmd, microversion=microversion)

        # Verify quotas after reset
        self._verify_current_quotas_equal_to(default_quotas, microversion)

        # Return project quotas back
        cmd = ('quota-update %s --share-groups %s '
               '--share-group-snapshots %s') % (
            self.project_id,
            p_quotas['share_groups'], p_quotas['share_group_snapshots'])
        self.admin_client.manila(cmd, microversion=microversion)

        # Verify quotas after reset
        self._verify_current_quotas_equal_to(p_quotas, microversion)

    @ddt.data('--share-groups', '--share-group-snapshots')
    @utils.skip_if_microversion_not_supported("2.39")
    def test_update_quotas_for_share_groups_using_too_old_microversion(self,
                                                                       arg):
        cmd = 'quota-update %s %s 13' % (self.project_id, arg)
        self.assertRaises(
            exceptions.CommandFailed,
            self.admin_client.manila,
            cmd, microversion='2.39')

    @ddt.data('--share-groups', '--share-group-snapshots')
    @utils.skip_if_microversion_not_supported("2.40")
    def test_update_share_type_quotas_for_share_groups(self, arg):
        cmd = 'quota-update %s --share-type %s %s 13' % (
            self.project_id, self.st_id, arg)
        self.assertRaises(
            exceptions.CommandFailed,
            self.admin_client.manila,
            cmd, microversion='2.40')

    @ddt.data(*set([
        "2.39", "2.40", api_versions.MAX_VERSION,
    ]))
    def test_update_share_type_quotas_positive(self, microversion):
        if not utils.is_microversion_supported(microversion):
            msg = "Microversion '%s' not supported." % microversion
            raise self.skipException(msg)

        # Get project quotas
        cmd = 'quota-show --tenant-id %s ' % self.project_id
        quotas_raw = self.admin_client.manila(cmd, microversion=microversion)
        p_quotas = output_parser.details(quotas_raw)

        # Define share type quotas
        st_custom_quotas = {
            'shares': _get_share_type_quota_values(p_quotas['shares']),
            'snapshots': _get_share_type_quota_values(p_quotas['snapshots']),
            'gigabytes': _get_share_type_quota_values(p_quotas['gigabytes']),
            'snapshot_gigabytes': _get_share_type_quota_values(
                p_quotas['snapshot_gigabytes']),
        }

        # Update quotas for share type
        cmd = ('quota-update %s --share-type %s '
               '--shares %s --gigabytes %s --snapshots %s '
               '--snapshot-gigabytes %s') % (
                   self.project_id, self.st_id,
                   st_custom_quotas['shares'],
                   st_custom_quotas['gigabytes'],
                   st_custom_quotas['snapshots'],
                   st_custom_quotas['snapshot_gigabytes'])
        self.admin_client.manila(cmd, microversion=microversion)

        # Verify share type quotas
        self._verify_current_st_quotas_equal_to(st_custom_quotas, microversion)

        # Reset share type quotas
        cmd = 'quota-delete --tenant-id %s --share-type %s' % (
            self.project_id, self.st_id)
        self.admin_client.manila(cmd, microversion=microversion)

        # Verify share type quotas after reset
        self._verify_current_st_quotas_equal_to(p_quotas, microversion)

    @utils.skip_if_microversion_not_supported("2.38")
    def test_read_share_type_quotas_with_too_old_microversion(self):
        cmd = 'quota-show --tenant-id %s --share-type %s' % (
            self.project_id, self.st_id)
        self.assertRaises(
            exceptions.CommandFailed,
            self.admin_client.manila,
            cmd, microversion='2.38')

    @utils.skip_if_microversion_not_supported("2.38")
    def test_update_share_type_quotas_with_too_old_microversion(self):
        cmd = 'quota-update --tenant-id %s --share-type %s --shares %s' % (
            self.project_id, self.st_id, '0')
        self.assertRaises(
            exceptions.CommandFailed,
            self.admin_client.manila,
            cmd, microversion='2.38')

    @utils.skip_if_microversion_not_supported("2.38")
    def test_delete_share_type_quotas_with_too_old_microversion(self):
        cmd = 'quota-delete --tenant-id %s --share-type %s' % (
            self.project_id, self.st_id)
        self.assertRaises(
            exceptions.CommandFailed,
            self.admin_client.manila,
            cmd, microversion='2.38')


@ddt.ddt
class ManilaClientTestQuotasReadOnly(base.BaseTestCase):

    def test_quota_class_show_by_admin(self):
        roles = self.parser.listing(
            self.clients['admin'].manila('quota-class-show', params='abc'))
        self.assertTableStruct(roles, ('Property', 'Value'))

    def test_quota_class_show_by_user(self):
        self.assertRaises(
            exceptions.CommandFailed,
            self.clients['user'].manila,
            'quota-class-show',
            params='abc')

    def _get_quotas(self, role, operation, microversion):
        roles = self.parser.listing(self.clients[role].manila(
            'quota-%s' % operation, microversion=microversion))
        self.assertTableStruct(roles, ('Property', 'Value'))

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("1.0")
    def test_quota_defaults_api_1_0(self, role):
        self._get_quotas(role, "defaults", "1.0")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("2.0")
    def test_quota_defaults_api_2_0(self, role):
        self._get_quotas(role, "defaults", "2.0")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("2.6")
    def test_quota_defaults_api_2_6(self, role):
        self._get_quotas(role, "defaults", "2.6")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("2.7")
    def test_quota_defaults_api_2_7(self, role):
        self._get_quotas(role, "defaults", "2.7")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("1.0")
    def test_quota_show_api_1_0(self, role):
        self._get_quotas(role, "show", "1.0")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("2.0")
    def test_quota_show_api_2_0(self, role):
        self._get_quotas(role, "show", "2.0")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("2.6")
    def test_quota_show_api_2_6(self, role):
        self._get_quotas(role, "show", "2.6")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("2.7")
    def test_quota_show_api_2_7(self, role):
        self._get_quotas(role, "show", "2.7")

    @ddt.data('admin', 'user')
    @utils.skip_if_microversion_not_supported("2.25")
    def test_quota_show_api_2_25(self, role):
        self._get_quotas(role, "show  --detail", "2.25")
