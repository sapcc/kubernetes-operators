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
from designateclient.v1 import sync


class TestSync(test_v1.APIV1TestCase, test_v1.CrudMixin):

    @patch.object(sync.SyncController, "sync_all")
    def test_sync_all(self, sync_all):
        self.client.sync.sync_all()
        self.client.sync.sync_all.assert_called_with()

    @patch.object(sync.SyncController, "sync_domain")
    def test_sync_domain(self, sync_domain):
        args = mock.MagicMock()
        args.tenant_id = "1234"
        self.client.sync.sync_domain(args.tenant_id)
        self.client.sync.sync_domain.assert_called_with("1234")

    @patch.object(sync.SyncController, "sync_record")
    def test_sync_record(self, sync_record):
        args = mock.MagicMock()
        args.tenant_id = "1234"
        args.record_id = "uuid"
        self.client.sync.sync_record(args.tenant_id, args.record_id)
        self.client.sync.sync_record.assert_called_with("1234", "uuid")
