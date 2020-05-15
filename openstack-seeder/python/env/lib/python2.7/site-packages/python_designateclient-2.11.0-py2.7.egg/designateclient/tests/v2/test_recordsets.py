# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Author: Endre Karlson <endre.karlson@hp.com>
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

from mock import patch
import testtools

from designateclient import exceptions
from designateclient.tests import v2
from designateclient.v2 import zones

ZONE = {
    "id": str(uuid.uuid4()),
    "name": "example.com."
}


class TestRecordSets(v2.APIV2TestCase, v2.CrudMixin):
    RESOURCE = 'recordsets'

    def new_ref(self, **kwargs):
        ref = super(TestRecordSets, self).new_ref(**kwargs)
        ref.setdefault("name", uuid.uuid4().hex)
        ref.setdefault("type", "A")
        ref.setdefault("records", ["10.0.0.1"])
        return ref

    def test_create_absolute_with_zone_dict(self):
        ref = self.new_ref()

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.create(
            ZONE,
            "%s.%s" % (values["name"], ZONE["name"]),
            values["type"],
            values["records"])

        values["name"] = "%s.%s" % (ref["name"], ZONE["name"])
        self.assertRequestBodyIs(json=values)

    @patch.object(zones.ZoneController, "get")
    def test_create_absolute_with_zone_name(self, zone_get):
        ref = self.new_ref()

        zone_get.return_value = ZONE

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.create(
            ZONE["name"],
            "%s.%s" % (values["name"], ZONE["name"]),
            values["type"],
            values["records"])

        values["name"] = "%s.%s" % (ref["name"], ZONE["name"])
        self.assertRequestBodyIs(json=values)

    @patch.object(zones.ZoneController, "get")
    def test_create_non_absolute_with_zone_name(self, zone_get):
        ref = self.new_ref()

        zone_get.return_value = ZONE

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.create(
            ZONE["name"],
            values["name"],
            values["type"],
            values["records"])

        values["name"] = "%s.%s" % (ref["name"], ZONE["name"])
        self.assertRequestBodyIs(json=values)

    @patch.object(zones.ZoneController, "list")
    def test_create_non_absolute_with_zone_name_non_unique(self, zone_list):
        zone_list.return_value = [
            1,
            2
        ]

        ref = self.new_ref()
        values = ref.copy()
        del values["id"]

        with testtools.ExpectedException(exceptions.NoUniqueMatch):
            self.client.recordsets.create(
                ZONE["name"],
                "%s.%s" % (values["name"], ZONE["name"]),
                values["type"],
                values["records"])

    def test_create_absolute_with_zone_id(self):
        ref = self.new_ref()

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.create(
            ZONE["id"],
            "%s.%s" % (values["name"], ZONE["name"]),
            values["type"],
            values["records"])

        values["name"] = "%s.%s" % (ref["name"], ZONE["name"])
        self.assertRequestBodyIs(json=values)

    @patch.object(zones.ZoneController, "get")
    def test_create_non_absolute_with_zone_id(self, zone_get):
        ref = self.new_ref()

        zone_get.return_value = ZONE

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.create(
            ZONE["id"],
            values["name"],
            values["type"],
            values["records"])

        values["name"] = "%s.%s" % (ref["name"], ZONE["name"])
        self.assertRequestBodyIs(json=values)

    def test_create_with_description(self):
        ref = self.new_ref(description="Foo")

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.create(
            ZONE["id"],
            "%s.%s" % (values["name"], ZONE["name"]),
            values["type"],
            values["records"],
            description=values["description"])

        values["name"] = "%s.%s" % (ref["name"], ZONE["name"])
        self.assertRequestBodyIs(json=values)

    def test_create_with_ttl(self):
        ref = self.new_ref(ttl=60)

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("POST", parts=parts, json=ref)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.create(
            ZONE["id"],
            "%s.%s" % (values["name"], ZONE["name"]),
            values["type"],
            values["records"],
            ttl=values["ttl"])

        values["name"] = "%s.%s" % (ref["name"], ZONE["name"])
        self.assertRequestBodyIs(json=values)

    def test_get(self):
        ref = self.new_ref()

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_entity("GET", entity=ref, id=ref["id"], parts=parts)

        response = self.client.recordsets.get(ZONE["id"], ref["id"])
        self.assertEqual(ref, response)

    def test_list(self):
        items = [
            self.new_ref(),
            self.new_ref()
        ]

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_url("GET", parts=parts, json={"recordsets": items})

        listed = self.client.recordsets.list(ZONE["id"])
        self.assertList(items, listed)
        self.assertQueryStringIs("")

    def test_update(self):
        ref = self.new_ref()

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_entity("PUT", entity=ref, id=ref["id"], parts=parts)

        values = ref.copy()
        del values["id"]

        self.client.recordsets.update(ZONE["id"], ref["id"], values)
        self.assertRequestBodyIs(json=values)

    def test_delete(self):
        ref = self.new_ref()

        parts = ["zones", ZONE["id"], self.RESOURCE]
        self.stub_entity("DELETE", id=ref["id"], parts=parts)

        self.client.recordsets.delete(ZONE["id"], ref["id"])
        self.assertRequestBodyIs(None)
