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

FIP_ID = '%s:%s' % (str(uuid.uuid4()), "RegionOne")


class TestFloatingIP(v2.APIV2TestCase, v2.CrudMixin):
    def test_set(self):
        name = "foo.com."

        ref = {
            "ptrdname": name,
            "description": "foo"
        }

        parts = ["reverse", "floatingips", FIP_ID]
        self.stub_url("PATCH", parts=parts, json=ref)

        self.client.floatingips.set(FIP_ID, name, "foo")

    def test_list(self):
        ref = [
            {"ptrdname": "foo.com."}
        ]

        self.stub_url("GET", parts=["reverse", "floatingips"],
                      json={"floatingips": ref})

        self.client.floatingips.list()

    def test_get(self):
        ref = {
            "ptrdname": "foo.com."
        }

        parts = ["reverse", "floatingips", FIP_ID]
        self.stub_url("GET", parts=parts, json=ref)

        self.client.floatingips.get(FIP_ID)

    def test_unset(self):
        parts = ["reverse", "floatingips", FIP_ID]
        self.stub_url("PATCH", parts=parts, json={"ptdrname": None})

        self.client.floatingips.unset(FIP_ID)
        self.assertRequestBodyIs(None)
