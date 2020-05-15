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

from mock import patch

from designateclient.tests import test_v1
from designateclient import utils
from designateclient.v1 import domains
from designateclient import warlock

Domain = warlock.model_factory(utils.load_schema('v1', 'domain'))


class TestDomain(test_v1.APIV1TestCase, test_v1.CrudMixin):
    RESOURCE = 'domains'

    def new_ref(self, **kwargs):
        ref = super(TestDomain, self).new_ref(**kwargs)
        ref.setdefault("name", uuid.uuid4().hex)
        ref.setdefault("email", "abc@example.com.")
        ref.setdefault("ttl", 3600)
        return ref

    def test_create(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "domain1.com.",
               "email": "nsadmin@example.org",
               "ttl": 60}
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        response = self.client.domains.create(values["name"])
        self.assertEqual(ref['id'], response['id'])

    def test_create_with_description(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "domain1.com.",
               "email": "nsadmin@example.org",
               "ttl": 60,
               "description": "fully qualified domain"}

        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        response = self.client.domains.create(values["name"])
        self.assertEqual(ref['id'], response['id'])

    def test_create_with_description_too_long(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "domain1.com.",
               "email": "nsadmin@example.org",
               "ttl": 60,
               "description": "d" * 161}
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.assertRaises(ValueError, self.client.domains.create,
                          values["name"])

    def test_create_with_zero_ttl(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "domain1.com.",
               "email": "nsadmin@example.org",
               "ttl": 0}
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.assertRaises(ValueError, self.client.domains.create,
                          values["name"])

    def test_create_with_negative_ttl(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "domain1.com.",
               "email": "nsadmin@example.org",
               "ttl": -1}
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.assertRaises(ValueError, self.client.domains.create,
                          values["name"])

    def test_create_with_no_ttl(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "domain1.com.",
               "email": "nsadmin@example.org",
               "ttl": ""}
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.assertRaises(ValueError, self.client.domains.create,
                          values["name"])

    def test_create_with_name_too_long(self):
        ref = {"id": "89acac79-38e7-497d-807c-a011e1310438",
               "name": "domain" + "a" * 255 + ".com.",
               "email": "nsadmin@example.org",
               "ttl": 60}
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.assertRaises(ValueError, self.client.domains.create,
                          values["name"])

    def test_list(self):
        items = [
            self.new_ref(email="abc@example.org",
                         id="89acac79-38e7-497d-807c-a011e1310438"),
            self.new_ref(email="root@example.org",
                         id="89acac79-38e7-497d-807c-a011e1310435")
        ]

        self.stub_url("GET", parts=[self.RESOURCE], json={"domains": items})

        listed = self.client.domains.list()
        self.assertList(items, listed)
        self.assertQueryStringIs("")

    def test_get(self):
        ref = self.new_ref(email="abc@example.org",
                           id="89acac79-38e7-497d-807c-a011e1310438")

        self.stub_entity("GET", entity=ref, id=ref["id"])

        response = self.client.domains.get(ref["id"])
        self.assertEqual(ref, response)

    def test_delete(self):
        ref = self.new_ref(email="abc@example.org",
                           id="89acac79-38e7-497d-807c-a011e1310438")

        self.stub_entity("DELETE", entity=ref, id=ref["id"])

        self.client.domains.delete(ref["id"])
        self.assertRequestBodyIs(None)

    def test_update(self):
        ref = self.new_ref(id="89acac79-38e7-497d-807c-a011e1310438")

        self.stub_entity("PUT", entity=ref, id=ref["id"])

        values = ref.copy()

        self.client.domains.update(Domain(values))

    @patch.object(domains.DomainsController, "list_domain_servers")
    def test_list_domain_servers(self, domains_get):
        domains_get.return_value = [{"id": "foo", "name": "ns1.example.com."}]

        ref = [{
            "id": "foo",
            "name": "ns1.example.com.",
        }]
        parts = ["domains", "foo", "servers"]
        self.stub_url("GET", parts=parts, json={"servers": ref})

        response = self.client.domains.list_domain_servers("foo")
        self.assertEqual(ref, response)
