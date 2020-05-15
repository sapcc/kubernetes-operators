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
import json

from designateclient import client
from designateclient import utils
from designateclient import warlock


Domain = warlock.model_factory(utils.load_schema('v1', 'domain'))
Server = warlock.model_factory(utils.load_schema('v1', 'server'))


class DomainsController(client.CrudController):
    def list(self):
        """
        Retrieve a list of domains

        :returns: A list of :class:`Domain`
        """
        response = self.client.get('/domains')

        return [Domain(i) for i in response.json()['domains']]

    def get(self, domain_id):
        """
        Retrieve a domain

        :param domain_id: Domain Identifier
        :returns: :class:`Domain`
        """
        response = self.client.get('/domains/%s' % domain_id)

        return Domain(response.json())

    def create(self, domain):
        """
        Create a domain

        :param domain: A :class:`Domain` to create
        :returns: :class:`Domain`
        """
        response = self.client.post('/domains', data=json.dumps(domain))

        return Domain(response.json())

    def update(self, domain):
        """
        Update a domain

        :param domain: A :class:`Domain` to update
        :returns: :class:`Domain`
        """
        response = self.client.put('/domains/%s' % domain.id,
                                   data=json.dumps(domain.changes))

        return Domain(response.json())

    def delete(self, domain):
        """
        Delete a domain

        :param domain: A :class:`Domain`, or Domain Identifier to delete
        """
        if isinstance(domain, Domain):
            self.client.delete('/domains/%s' % domain.id)
        else:
            self.client.delete('/domains/%s' % domain)

    def list_domain_servers(self, domain_id):
        """
        Retrieve the list of nameservers for a domain

        :param domain_id: Domain Identifier
        :returns: A list of :class:`Server`
        """
        response = self.client.get('/domains/%s/servers' % domain_id)

        return [Server(i) for i in response.json()['servers']]
