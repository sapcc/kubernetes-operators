# Copyright 2017 SAP SE
#
# Author: Rudolf Vriend <rudolf.vriend@sap.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import uuid

from designateclient.tests import v2


class TestTSIGKeys(v2.APIV2TestCase, v2.CrudMixin):
    RESOURCE = 'tsigkeys'

    def new_ref(self, **kwargs):
        ref = super(TestTSIGKeys, self).new_ref(**kwargs)
        ref.setdefault("name", uuid.uuid4().hex)
        ref.setdefault("algorithm", "hmac-sha256")
        ref.setdefault("secret", uuid.uuid4().hex)
        ref.setdefault("scope", "POOL")
        ref.setdefault("resource_id", uuid.uuid4().hex)
        return ref

    def test_create(self):
        ref = self.new_ref()

        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.tsigkeys.create(**values)
        self.assertRequestBodyIs(json=values)

    def test_get(self):
        ref = self.new_ref()

        self.stub_entity("GET", entity=ref, id=ref["id"])

        response = self.client.tsigkeys.get(ref["id"])
        self.assertEqual(ref, response)

    def test_get_by_name(self):
        ref = self.new_ref(name="www")

        self.stub_entity("GET", entity=ref, id=ref["id"])
        self.stub_url("GET", parts=[self.RESOURCE], json={"tsigkeys": [ref]})

        response = self.client.tsigkeys.get(ref['name'])

        self.assertEqual("GET", self.requests.request_history[0].method)
        self.assertEqual(
            "http://127.0.0.1:9001/v2/tsigkeys?name=www",
            self.requests.request_history[0].url)

        self.assertEqual(ref, response)

    def test_list(self):
        items = [
            self.new_ref(),
            self.new_ref()
        ]

        self.stub_url("GET", parts=[self.RESOURCE], json={"tsigkeys": items})

        listed = self.client.tsigkeys.list()
        self.assertList(items, listed)
        self.assertQueryStringIs("")

    def test_update(self):
        ref = self.new_ref()

        self.stub_entity("PATCH", entity=ref, id=ref["id"])

        values = ref.copy()
        del values["id"]

        self.client.tsigkeys.update(ref["id"], values)
        self.assertRequestBodyIs(json=values)

    def test_delete(self):
        ref = self.new_ref()

        self.stub_entity("DELETE", id=ref["id"])

        self.client.tsigkeys.delete(ref["id"])
        self.assertRequestBodyIs(None)
