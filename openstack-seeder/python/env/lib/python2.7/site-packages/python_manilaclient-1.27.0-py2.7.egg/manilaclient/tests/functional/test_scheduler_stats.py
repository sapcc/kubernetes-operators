# Copyright (c) 2015 Clinton Knight.  All rights reserved.
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

from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions

from manilaclient.tests.functional import base


class ManilaClientTestSchedulerStatsReadOnly(base.BaseTestCase):

    def test_pools_list(self):
        self.clients['admin'].manila('pool-list')

    def test_pools_list_with_debug_flag(self):
        self.clients['admin'].manila('pool-list', flags='--debug')

    def test_pools_list_with_detail(self):
        self.clients['admin'].manila('pool-list', params='--detail')

    def test_pools_list_with_share_type_filter(self):
        share_type = self.create_share_type(
            name=data_utils.rand_name('manilaclient_functional_test'),
            snapshot_support=True,
        )
        self.clients['admin'].manila('pool-list',
                                     params='--share_type ' +
                                            share_type['ID'])

    def test_pools_list_with_filters(self):
        self.clients['admin'].manila(
            'pool-list',
            params='--host myhost --backend mybackend --pool mypool')

    def test_pools_list_by_user(self):
        self.assertRaises(exceptions.CommandFailed,
                          self.clients['user'].manila,
                          'pool-list')
