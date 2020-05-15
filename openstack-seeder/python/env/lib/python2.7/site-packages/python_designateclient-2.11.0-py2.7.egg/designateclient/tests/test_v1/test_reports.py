# Copyright 2015 NEC Corporation.  All rights reserved.
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

import mock
from mock import patch

from designateclient.tests import test_v1
from designateclient.v1 import reports


class TestReports(test_v1.APIV1TestCase, test_v1.CrudMixin):

    @patch.object(reports.ReportsController, "count_all")
    def test_count_all(self, count_all):
        self.client.reports.count_all()
        self.client.reports.count_all.assert_called_with()

    @patch.object(reports.ReportsController, "count_domains")
    def test_count_domain(self, count_domains):
        self.client.reports.count_domains()
        self.client.reports.count_domains.assert_called_once_with()

    @patch.object(reports.ReportsController, "count_tenants")
    def test_count_tenants(self, count_tenants):
        self.client.reports.count_tenants()
        self.client.reports.count_tenants.assert_called_once_with()

    @patch.object(reports.ReportsController, "count_records")
    def test_count_records(self, count_records):
        self.client.reports.count_records()
        self.client.reports.count_records.assert_called_once_with()

    @patch.object(reports.ReportsController, "tenants_all")
    def test_tenants_all(self, tenants_all):
        self.client.reports.tenants_all()
        self.client.reports.tenants_all.assert_called_once_with()

    @patch.object(reports.ReportsController, "tenant_domains")
    def test_tenant_domains(self, tenant_domains):
        args = mock.MagicMock()
        args.other_tenant_id = "uuid"
        self.client.reports.tenant_domains(args.other_tenant_id)
        self.client.reports.tenant_domains.assert_called_once_with("uuid")
