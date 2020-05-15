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
from designateclient.v2.base import V2Controller


class BlacklistController(V2Controller):
    def create(self, pattern, description=None):
        data = {
            'pattern': pattern,
        }

        if description is not None:
            data['description'] = description

        return self._post('/blacklists', data=data)

    def list(self, criterion=None, marker=None, limit=None):
        url = self.build_url('/blacklists', criterion, marker, limit)

        return self._get(url, response_key="blacklists")

    def get(self, blacklist_id):
        url = '/blacklists/%s' % blacklist_id

        return self._get(url)

    def update(self, blacklist_id, values):
        url = '/blacklists/%s' % blacklist_id

        return self._patch(url, data=values)

    def delete(self, blacklist_id):
        url = '/blacklists/%s' % blacklist_id

        return self._delete(url)
