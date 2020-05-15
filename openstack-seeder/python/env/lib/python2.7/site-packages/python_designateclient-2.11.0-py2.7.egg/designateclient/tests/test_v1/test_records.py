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

from designateclient.tests import test_v1
from designateclient import utils
from designateclient import warlock


Record = warlock.model_factory(utils.load_schema('v1', 'record'))

DOMAIN = {
    "id": str(uuid.uuid4()),
    "name": "example.com."
}


class TestRecords(test_v1.APIV1TestCase, test_v1.CrudMixin):
    RESOURCE = 'records'

    def new_ref(self, **kwargs):
        ref = super(TestRecords, self).new_ref(**kwargs)
        ref.setdefault("name", uuid.uuid4().hex)
        ref.setdefault("type", "A")
        ref.setdefault("data", "10.0.0.1")
        return ref

    def test_create_record(self):
        ref = self.new_ref(id="2e32e609-3a4f-45ba-bdef-e50eacd345ad")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_AAAA_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778888",
                           type="AAAA",
                           data="2001:db8:0:1234:0:5678:9:12")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_MX_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778989",
                           type="MX",
                           data="mail.example.com.",
                           priority=10)

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_CNAME_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778890",
                           type="CNAME",
                           data="example.com.")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_TXT_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778889",
                           type="TXT",
                           data="This is a TXT record")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_SRV_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778888",
                           type="SRV",
                           data="0 5060 sip.example.com.",
                           priority=30)

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_NS_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677779999",
                           type="NS",
                           data="ns1.example.com.")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_PTR_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778891",
                           type="PTR",
                           data="www.example.com.")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_SPF_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778899",
                           type="SPF",
                           data="v=spf1 +mx a:colo.example.com/28 -all")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_create_SSHFP_record(self):
        ref = self.new_ref(id="11112222-3333-4444-5555-666677778888",
                           type="SSHFP",
                           data="2 1 6c3c958af43d953f91f40e0d84157f4fe7b4a898")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.records.create(DOMAIN['id'], Record(values))
        self.assertRequestBodyIs(json=values)

    def test_get(self):
        ref = self.new_ref(id="2e32e609-3a4f-45ba-bdef-e50eacd345ad")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_entity("GET", entity=ref, id=ref["id"], parts=parts)

        response = self.client.records.get(DOMAIN["id"], ref["id"])
        self.assertEqual(ref, response)

    def test_list(self):
        items = [
            self.new_ref(id="2e32e609-3a4f-45ba-bdef-e50eacd345ad"),
            self.new_ref(id="11112222-3333-4444-5555-666677778888")
        ]

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_url("GET", parts=parts, json={"records": items})

        listed = self.client.records.list(DOMAIN["id"])
        self.assertList(items, listed)
        self.assertQueryStringIs("")

    def test_update(self):
        ref = self.new_ref(id="2e32e609-3a4f-45ba-bdef-e50eacd345ad",
                           type="A",
                           data="192.0.2.5")

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_entity("PUT", entity=ref, id=ref["id"], parts=parts)

        values = ref.copy()
        del values["id"]

        self.client.records.update(DOMAIN["id"], Record(ref))

    def test_delete(self):
        ref = self.new_ref()

        parts = ["domains", DOMAIN["id"], self.RESOURCE]
        self.stub_entity("DELETE", id=ref["id"], parts=parts)

        self.client.records.delete(DOMAIN["id"], ref["id"])
        self.assertRequestBodyIs(None)
