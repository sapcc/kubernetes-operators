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

from designateclient.tests import v2


class TestBlacklists(v2.APIV2TestCase, v2.CrudMixin):
    RESOURCE = 'blacklists'

    def new_ref(self, **kwargs):
        ref = super(TestBlacklists, self).new_ref(**kwargs)
        ref.setdefault("pattern", uuid.uuid4().hex)
        return ref

    def test_create(self):
        ref = self.new_ref()

        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.blacklists.create(**values)
        self.assertRequestBodyIs(json=values)

    def test_create_with_description(self):
        ref = self.new_ref(description="My Blacklist")

        self.stub_url("POST", parts=[self.RESOURCE], json=ref)

        values = ref.copy()
        del values["id"]

        self.client.blacklists.create(**values)
        self.assertRequestBodyIs(json=values)

    def test_get(self):
        ref = self.new_ref()

        self.stub_entity("GET", entity=ref, id=ref["id"])

        response = self.client.blacklists.get(ref["id"])
        self.assertEqual(ref, response)

    def test_list(self):
        items = [
            self.new_ref(),
            self.new_ref()
        ]

        self.stub_url("GET", parts=[self.RESOURCE], json={"blacklists": items})

        listed = self.client.blacklists.list()
        self.assertList(items, listed)
        self.assertQueryStringIs("")

    def test_update(self):
        ref = self.new_ref()

        self.stub_entity("PATCH", entity=ref, id=ref["id"])

        values = ref.copy()
        del values["id"]

        self.client.blacklists.update(ref["id"], values)
        self.assertRequestBodyIs(json=values)

    def test_delete(self):
        ref = self.new_ref()

        self.stub_entity("DELETE", id=ref["id"])

        self.client.blacklists.delete(ref["id"])
        self.assertRequestBodyIs(None)
