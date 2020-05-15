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

import uuid

import mock
from mock import patch

from designateclient.tests import test_v1
from designateclient.v1 import servers


class TestServers(test_v1.APIV1TestCase, test_v1.CrudMixin):
    RESOURCE = 'servers'

    def new_ref(self, **kwargs):
        ref = super(TestServers, self).new_ref(**kwargs)
        ref.setdefault("name", uuid.uuid4().hex)
        return ref

    def test_list(self):
        items = [
            self.new_ref(name="ns1.example.org.",
                         id="89acac79-38e7-497d-807c-a011e1310438"),
            self.new_ref(name="ns2.example.org.",
                         id="89acac79-38e7-497d-807c-a011e1310435")
        ]

        self.stub_url("GET", parts=[self.RESOURCE], json={"servers": items})

        listed = self.client.servers.list()
        self.assertList(items, listed)
        self.assertQueryStringIs("")

    def test_get(self):
        ref = self.new_ref(name="ns1.example.org.",
                           id="89acac79-38e7-497d-807c-a011e1310438")

        self.stub_entity("GET", entity=ref, id=ref["id"])

        response = self.client.servers.get(ref["id"])
        self.assertEqual(ref, response)

    def test_create(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "ns1.example.org."}

        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.servers.create({"name": "ns1.example.org."})
        self.assertRequestBodyIs(json=values)

    def test_create_with_name_too_long(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "ns1." + "foo" * 85 + ".org."}

        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.assertRaises(ValueError, self.client.servers.create,
                          {"name": "ns1.example.org."})

    @patch.object(servers.ServersController, "update")
    def test_update(self, server_update):
        ref = self.new_ref()

        self.stub_entity("PUT", entity=ref, id=ref["id"])

        mock_server = mock.MagicMock()
        self.client.servers.update(mock_server)
        self.client.servers.update.assert_called_with(mock_server)

    def test_delete(self):
        ref = self.new_ref()

        self.stub_entity("DELETE", id=ref["id"])

        self.client.servers.delete(ref["id"])
        self.assertRequestBodyIs(None)
