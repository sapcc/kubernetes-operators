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
import time
import uuid

from designateclient.tests import v2


class TestZones(v2.APIV2TestCase, v2.CrudMixin):
    RESOURCE = 'zones'

    def new_ref(self, **kwargs):
        ref = super(TestZones, self).new_ref(**kwargs)
        ref.setdefault("name", uuid.uuid4().hex)
        ref.setdefault("type", "PRIMARY")
        return ref

    def test_create_with_description(self):
        ref = self.new_ref(email="root@example.com", description="Foo")
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.zones.create(
            values["name"],
            email=values["email"],
            description=values["description"])
        self.assertRequestBodyIs(json=values)

    def test_create_primary(self):
        ref = self.new_ref(email="root@example.com")
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.zones.create(
            values["name"],
            email=values["email"])
        self.assertRequestBodyIs(json=values)

    def test_create_primary_with_ttl(self):
        ref = self.new_ref(email="root@example.com", ttl=60)
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.zones.create(
            values["name"],
            email=values["email"],
            ttl=values["ttl"])
        self.assertRequestBodyIs(json=values)

    def test_create_secondary(self):
        ref = self.new_ref(type="SECONDARY", masters=["10.0.0.1"])
        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.zones.create(
            values["name"],
            type_=values["type"],
            masters=values["masters"])
        self.assertRequestBodyIs(json=values)

    def test_get(self):
        ref = self.new_ref()

        self.stub_entity("GET", entity=ref, id=ref["id"])

        response = self.client.zones.get(ref["id"])
        self.assertEqual(ref, response)

    def test_list(self):
        items = [
            self.new_ref(),
            self.new_ref()
        ]

        self.stub_url("GET", parts=[self.RESOURCE], json={"zones": items})

        listed = self.client.zones.list()
        self.assertList(items, listed)
        self.assertQueryStringIs("")

    def test_update(self):
        ref = self.new_ref()

        self.stub_entity("PATCH", entity=ref, id=ref["id"])

        values = ref.copy()
        del values["id"]

        self.client.zones.update(ref["id"], values)
        self.assertRequestBodyIs(json=values)

    def test_delete(self):
        ref = self.new_ref()

        self.stub_entity("DELETE", id=ref["id"])

        self.client.zones.delete(ref["id"])
        self.assertRequestBodyIs(None)

    def test_task_abandon(self):
        ref = self.new_ref()

        parts = [self.RESOURCE, ref["id"], "tasks", "abandon"]
        self.stub_url("POST", parts=parts)

        self.client.zones.abandon(ref["id"])
        self.assertRequestBodyIs(None)

    def test_task_axfr(self):
        ref = self.new_ref()

        parts = [self.RESOURCE, ref["id"], "tasks", "xfr"]
        self.stub_url("POST", parts=parts)

        self.client.zones.axfr(ref["id"])
        self.assertRequestBodyIs(None)


class TestZoneTransfers(v2.APIV2TestCase, v2.CrudMixin):
    def test_create_request(self):
        zone = "098bee04-fe30-4a83-8ccd-e0c496755816"
        project = "123"

        ref = {
            "target_project_id": project
        }

        parts = ["zones", zone, "tasks", "transfer_requests"]
        self.stub_url('POST', parts=parts, json=ref)

        self.client.zone_transfers.create_request(zone, project)
        self.assertRequestBodyIs(json=ref)

    def test_create_request_with_description(self):
        zone = "098bee04-fe30-4a83-8ccd-e0c496755816"
        project = "123"

        ref = {
            "target_project_id": project,
            "description": "My Foo"
        }

        parts = ["zones", zone, "tasks", "transfer_requests"]
        self.stub_url('POST', parts=parts, json=ref)

        self.client.zone_transfers.create_request(
            zone, project, ref["description"])
        self.assertRequestBodyIs(json=ref)

    def test_get_request(self):
        transfer = "098bee04-fe30-4a83-8ccd-e0c496755816"
        project = "098bee04-fe30-4a83-8ccd-e0c496755817"

        ref = {
            "target_project_id": project
        }

        parts = ["zones", "tasks", "transfer_requests", transfer]
        self.stub_url('GET', parts=parts, json=ref)

        self.client.zone_transfers.get_request(transfer)
        self.assertRequestBodyIs("")

    def test_list_request(self):
        project = "098bee04-fe30-4a83-8ccd-e0c496755817"

        ref = [{
            "target_project_id": project
        }]

        parts = ["zones", "tasks", "transfer_requests"]
        self.stub_url('GET', parts=parts, json={"transfer_requests": ref})

        self.client.zone_transfers.list_requests()
        self.assertRequestBodyIs("")

    def test_update_request(self):
        transfer = "098bee04-fe30-4a83-8ccd-e0c496755816"
        project = "098bee04-fe30-4a83-8ccd-e0c496755817"

        ref = {
            "target_project_id": project
        }

        parts = ["zones", "tasks", "transfer_requests", transfer]
        self.stub_url('PATCH', parts=parts, json=ref)

        self.client.zone_transfers.update_request(transfer, ref)
        self.assertRequestBodyIs(json=ref)

    def test_delete_request(self):
        transfer = "098bee04-fe30-4a83-8ccd-e0c496755816"

        parts = ["zones", "tasks", "transfer_requests", transfer]
        self.stub_url('DELETE', parts=parts)

        self.client.zone_transfers.delete_request(transfer)
        self.assertRequestBodyIs("")

    def test_accept_request(self):
        transfer = "098bee04-fe30-4a83-8ccd-e0c496755816"
        key = "foo123"

        ref = {
            "status": "COMPLETE"
        }

        parts = ["zones", "tasks", "transfer_accepts"]
        self.stub_url('POST', parts=parts, json=ref)

        request = {
            "key": key,
            "zone_transfer_request_id": transfer
        }
        self.client.zone_transfers.accept_request(transfer, key)
        self.assertRequestBodyIs(json=request)

    def test_get_accept(self):
        accept_id = "098bee04-fe30-4a83-8ccd-e0c496755816"

        ref = {
            "status": "COMPLETE"
        }

        parts = ["zones", "tasks", "transfer_accepts", accept_id]
        self.stub_url('GET', parts=parts, json=ref)

        response = self.client.zone_transfers.get_accept(accept_id)
        self.assertEqual(ref, response)

    def test_list_accepts(self):
        accept_id = "098bee04-fe30-4a83-8ccd-e0c496755816"

        ref = {
            "id": accept_id,
            "status": "COMPLETE"
        }

        parts = ["zones", "tasks", "transfer_accepts"]
        self.stub_url('GET', parts=parts, json={"transfer_accepts": ref})

        self.client.zone_transfers.list_accepts()
        self.assertRequestBodyIs("")


class TestZoneExports(v2.APIV2TestCase, v2.CrudMixin):
    def new_ref(self, **kwargs):
        ref = super(TestZoneExports, self).new_ref(**kwargs)
        ref.setdefault("zone_id", uuid.uuid4().hex)
        ref.setdefault("created_at", time.strftime("%c"))
        ref.setdefault("updated_at", time.strftime("%c"))
        ref.setdefault("status", 'PENDING')
        ref.setdefault("version", '1')
        return ref

    def test_create_export(self):
        zone = uuid.uuid4().hex
        ref = {}

        parts = ["zones", zone, "tasks", "export"]
        self.stub_url('POST', parts=parts, json=ref)

        self.client.zone_exports.create(zone)
        self.assertRequestBodyIs(json=ref)

    def test_get_export(self):
        ref = self.new_ref()

        parts = ["zones", "tasks", "exports", ref["id"]]
        self.stub_url('GET', parts=parts, json=ref)
        self.stub_entity("GET", parts=parts, entity=ref, id=ref["id"])

        response = self.client.zone_exports.get_export_record(ref["id"])
        self.assertEqual(ref, response)

    def test_list_exports(self):
        items = [
            self.new_ref(),
            self.new_ref()
        ]

        parts = ["zones", "tasks", "exports"]
        self.stub_url('GET', parts=parts, json={"exports": items})

        listed = self.client.zone_exports.list()
        self.assertList(items, listed["exports"])
        self.assertQueryStringIs("")

    def test_delete_export(self):
        ref = self.new_ref()

        parts = ["zones", "tasks", "exports", ref["id"]]
        self.stub_url('DELETE', parts=parts, json=ref)
        self.stub_entity("DELETE", parts=parts, id=ref["id"])

        self.client.zone_exports.delete(ref["id"])
        self.assertRequestBodyIs(None)

    def test_get_export_file(self):
        ref = self.new_ref()

        parts = ["zones", "tasks", "exports", ref["id"], "export"]
        self.stub_url('GET', parts=parts, json=ref)
        self.stub_entity("GET", parts=parts, entity=ref, id=ref["id"])

        response = self.client.zone_exports.get_export(ref["id"])
        self.assertEqual(ref, response)


class TestZoneImports(v2.APIV2TestCase, v2.CrudMixin):
    def new_ref(self, **kwargs):
        ref = super(TestZoneImports, self).new_ref(**kwargs)
        ref.setdefault("zone_id", uuid.uuid4().hex)
        ref.setdefault("created_at", time.strftime("%c"))
        ref.setdefault("updated_at", time.strftime("%c"))
        ref.setdefault("status", 'PENDING')
        ref.setdefault("message", 'Importing...')
        ref.setdefault("version", '1')
        return ref

    def test_create_import(self):
        zonefile = '$ORIGIN example.com'

        parts = ["zones", "tasks", "imports"]
        self.stub_url('POST', parts=parts, json=zonefile)

        self.client.zone_imports.create(zonefile)
        self.assertRequestBodyIs(body=zonefile)

    def test_get_import(self):
        ref = self.new_ref()

        parts = ["zones", "tasks", "imports", ref["id"]]
        self.stub_url('GET', parts=parts, json=ref)
        self.stub_entity("GET", parts=parts, entity=ref, id=ref["id"])

        response = self.client.zone_imports.get_import_record(ref["id"])
        self.assertEqual(ref, response)

    def test_list_imports(self):
        items = [
            self.new_ref(),
            self.new_ref()
        ]

        parts = ["zones", "tasks", "imports"]
        self.stub_url('GET', parts=parts, json={"imports": items})

        listed = self.client.zone_imports.list()
        self.assertList(items, listed["imports"])
        self.assertQueryStringIs("")

    def test_delete_import(self):
        ref = self.new_ref()

        parts = ["zones", "tasks", "imports", ref["id"]]
        self.stub_url('DELETE', parts=parts, json=ref)
        self.stub_entity("DELETE", parts=parts, id=ref["id"])

        self.client.zone_imports.delete(ref["id"])
        self.assertRequestBodyIs(None)
