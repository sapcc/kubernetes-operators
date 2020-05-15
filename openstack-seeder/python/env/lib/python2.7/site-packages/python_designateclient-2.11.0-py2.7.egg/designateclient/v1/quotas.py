# Copyright 2014 Hewlett-Packard Development Company, L.P.
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
import json

from designateclient import client


class QuotasController(client.Controller):
    def get(self, tenant_id):
        """
        Ping a service on a given host
        """
        response = self.client.get('/quotas/%s' % tenant_id)

        return response.json()

    def update(self, tenant_id, values):
        response = self.client.put('/quotas/%s' % tenant_id,
                                   data=json.dumps(values))
        return response.json()

    def reset(self, tenant_id):
        response = self.client.delete('/quotas/%s' % tenant_id)

        return response
