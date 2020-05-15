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
from designateclient.v1 import quotas


class TestQuota(test_v1.APIV1TestCase, test_v1.CrudMixin):

    @patch.object(quotas.QuotasController, "get")
    def test_get(self, quota_get):
        QUOTA = {"domains": 10,
                 "recordset_records": 20,
                 "domain_records": 500,
                 "domain_recordsets": 500}
        quota_get.return_value = QUOTA
        response = self.client.quotas.get("foo")
        self.assertEqual(QUOTA, response)

    @patch.object(quotas.QuotasController, "update")
    def test_update(self, quota_update):
        args = mock.MagicMock()
        args.tenant_id = "1234"
        args.value = {"domains": 1000}
        self.client.quotas.update(args.tenant_id, args.value)
        self.client.quotas.update.assert_called_with(args.tenant_id,
                                                     args.value)

    @patch.object(quotas.QuotasController, "reset")
    def test_reset(self, quota_reset):
        args = mock.MagicMock()
        args.tenant_id = "1234"
        self.client.quotas.reset(args.tenant_id)
        self.client.quotas.reset.assert_called_with("1234")
