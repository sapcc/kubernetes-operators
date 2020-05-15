# Copyright 2013 Hewlett-Packard Development Company, L.P. All Rights Reserved.
#
# Author: Patrick Galbraith <patg@patg.net>
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


class ReportsController(client.Controller):
    def count_all(self):
        """
        Domain, Records and tenant total count
        """
        response = self.client.get('/reports/counts')

        return response.json()

    def count_domains(self):
        """
        Domain total count
        """
        response = self.client.get('/reports/counts/domains')

        return response.json()

    def count_tenants(self):
        """
        Tenant total count
        """
        response = self.client.get('/reports/counts/tenants')

        return response.json()

    def count_records(self):
        """
        Record total count
        """
        response = self.client.get('/reports/counts/records')

        return response.json()

    def tenants_all(self):
        """
        Per tenant count
        """
        response = self.client.get('/reports/tenants')

        return response.json()['tenants']

    def tenant_domains(self, other_tenant_id):
        """
        Tenant's domain count
        """
        response = self.client.get('/reports/tenants/%s' %
                                   other_tenant_id)

        return [{'domain': d} for d in response.json()['domains']]
