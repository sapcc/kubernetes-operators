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
from designateclient.v2.base import V2Controller
from designateclient.v2 import utils as v2_utils


class TSIGKeysController(V2Controller):
    def create(self, name, algorithm, secret, scope, resource_id):
        data = {
            'name': name,
            'algorithm': algorithm,
            'secret': secret,
            'scope': scope,
            'resource_id': resource_id
        }

        return self._post('/tsigkeys', data=data)

    def list(self, criterion=None, marker=None, limit=None):
        url = self.build_url('/tsigkeys', criterion, marker, limit)

        return self._get(url, response_key='tsigkeys')

    def get(self, tsigkey):
        tsigkey = v2_utils.resolve_by_name(self.list, tsigkey)

        return self._get('/tsigkeys/%s' % tsigkey)

    def update(self, tsigkey, values):
        tsigkey = v2_utils.resolve_by_name(self.list, tsigkey)

        return self._patch('/tsigkeys/%s' % tsigkey, data=values)

    def delete(self, tsigkey):
        tsigkey = v2_utils.resolve_by_name(self.list, tsigkey)

        return self._delete('/tsigkeys/%s' % tsigkey)
