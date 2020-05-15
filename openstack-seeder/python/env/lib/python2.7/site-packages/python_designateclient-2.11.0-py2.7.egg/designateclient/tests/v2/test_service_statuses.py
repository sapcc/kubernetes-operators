# Copyright 2016 Hewlett Packard Enterprise Development Company LP
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
from designateclient.tests import v2


class TestServiceStatuses(v2.APIV2TestCase, v2.CrudMixin):
    RESOURCE = 'service_statuses'

    def new_ref(self, **kwargs):
        ref = super(TestServiceStatuses, self).new_ref(**kwargs)
        ref["name"] = "foo"
        return ref

    def test_get(self):
        ref = self.new_ref()

        self.stub_entity("GET", entity=ref, id=ref["id"])

        response = self.client.service_statuses.get(ref["id"])
        self.assertEqual(ref, response)

    def test_list(self):
        items = [
            self.new_ref(),
            self.new_ref()
        ]

        self.stub_url("GET", parts=[self.RESOURCE],
                      json={"service_statuses": items})

        listed = self.client.service_statuses.list()
        self.assertList(items, listed)
        self.assertQueryStringIs("")
