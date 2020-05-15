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

import ddt

from manilaclient.tests.functional import base


@ddt.ddt
class ManilaClientTestServicesReadOnly(base.BaseTestCase):

    @ddt.data("1.0", "2.0", "2.6", "2.7")
    def test_services_list(self, microversion):
        self.skip_if_microversion_not_supported(microversion)
        self.admin_client.manila('service-list', microversion=microversion)

    def test_list_with_debug_flag(self):
        self.clients['admin'].manila('service-list', flags='--debug')

    def test_shares_list_filter_by_host(self):
        self.clients['admin'].manila('service-list', params='--host host')

    def test_shares_list_filter_by_binary(self):
        self.clients['admin'].manila('service-list', params='--binary binary')

    def test_shares_list_filter_by_zone(self):
        self.clients['admin'].manila('service-list', params='--zone zone')

    def test_shares_list_filter_by_status(self):
        self.clients['admin'].manila('service-list', params='--status status')

    def test_shares_list_filter_by_state(self):
        self.clients['admin'].manila('service-list', params='--state state')
