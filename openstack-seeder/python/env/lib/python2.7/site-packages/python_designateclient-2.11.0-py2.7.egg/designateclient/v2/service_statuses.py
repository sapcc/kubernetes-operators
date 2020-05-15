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
from designateclient.v2 import base


class ServiceStatusesController(base.V2Controller):
    def list(self, criterion=None, marker=None, limit=None):
        url = self.build_url('/service_statuses', criterion, marker, limit)

        return self._get(url, response_key="service_statuses")

    def get(self, service_status_id):
        url = '/service_statuses/%s' % service_status_id

        return self._get(url)
