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


class FloatingIPController(V2Controller):
    def set(self, floatingip_id, ptrdname, description=None, ttl=None):
        data = {
            'ptrdname': ptrdname
        }

        if description is not None:
            data["description"] = description

        if ttl is not None:
            data["ttl"] = ttl

        url = '/reverse/floatingips/%s' % floatingip_id
        return self._patch(url, data=data)

    def list(self, criterion=None):
        url = self.build_url('/reverse/floatingips', criterion)

        return self._get(url, response_key='floatingips')

    def get(self, floatingip_id):
        url = '/reverse/floatingips/%s' % floatingip_id

        return self._get(url)

    def unset(self, floatingip_id):
        data = {"ptrdname": None}

        url = '/reverse/floatingips/%s' % floatingip_id

        return self._patch(url, data=data)
