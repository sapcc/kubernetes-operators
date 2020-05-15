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
from mock import patch

from designateclient.tests import v2
from designateclient.v2 import zones


class TestLimits(v2.APIV2TestCase, v2.CrudMixin):
    @patch.object(zones.ZoneController, "list")
    def test_get(self, zones_get):
        zones_get.return_value = [{"id": "foo"}]

        ref = [{
            "hostname": "ns1.example.com.",
            "priority": 1
        }]
        parts = ["zones", "foo", "nameservers"]
        self.stub_url("GET", parts=parts, json={"nameservers": ref})

        response = self.client.nameservers.list("foo")
        self.assertEqual(ref, response)
