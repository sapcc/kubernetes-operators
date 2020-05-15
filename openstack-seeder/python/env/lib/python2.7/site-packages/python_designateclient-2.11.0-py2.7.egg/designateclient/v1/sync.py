# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
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
from designateclient import client


class SyncController(client.Controller):
    def sync_all(self):
        """
        Sync Everything
        """
        self.client.post('/domains/sync')

    def sync_domain(self, domain_id):
        """
        Sync Single Domain
        """
        self.client.post('/domains/%s/sync' % domain_id)

    def sync_record(self, domain_id, record_id):
        """
        Sync Single Record
        """
        self.client.post('/domains/%s/records/%s/sync' %
                         (domain_id, record_id))
