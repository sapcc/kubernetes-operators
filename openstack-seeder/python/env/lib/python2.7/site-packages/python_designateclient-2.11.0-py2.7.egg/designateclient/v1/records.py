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
from designateclient.v1.domains import Domain
from designateclient import warlock


Record = warlock.model_factory(utils.load_schema('v1', 'record'))


class RecordsController(client.CrudController):
    def list(self, domain):
        """
        Retrieve a list of records

        :param domain: :class:`Domain` or Domain Identifier
        :returns: A list of :class:`Record`
        """
        domain_id = domain.id if isinstance(domain, Domain) else domain

        response = self.client.get('/domains/%(domain_id)s/records' % {
            'domain_id': domain_id
        })

        return [Record(i) for i in response.json()['records']]

    def get(self, domain, record_id):
        """
        Retrieve a record

        :param domain: :class:`Domain` or Domain Identifier
        :param record_id: Record Identifier
        :returns: :class:`Record`
        """
        domain_id = domain.id if isinstance(domain, Domain) else domain

        uri = '/domains/%(domain_id)s/records/%(record_id)s' % {
            'domain_id': domain_id,
            'record_id': record_id
        }

        response = self.client.get(uri)

        return Record(response.json())

    def create(self, domain, record):
        """
        Create a record

        :param domain: :class:`Domain` or Domain Identifier
        :param record: A :class:`Record` to create
        :returns: :class:`Record`
        """
        domain_id = domain.id if isinstance(domain, Domain) else domain

        uri = '/domains/%(domain_id)s/records' % {
            'domain_id': domain_id
        }

        response = self.client.post(uri, data=json.dumps(record))

        return Record(response.json())

    def update(self, domain, record):
        """
        Update a record

        :param domain: :class:`Domain` or Domain Identifier
        :param record: A :class:`Record` to update
        :returns: :class:`Record`
        """
        domain_id = domain.id if isinstance(domain, Domain) else domain

        uri = '/domains/%(domain_id)s/records/%(record_id)s' % {
            'domain_id': domain_id,
            'record_id': record.id
        }

        response = self.client.put(uri, data=json.dumps(record.changes))

        return Record(response.json())

    def delete(self, domain, record):
        """
        Delete a record

        :param domain: :class:`Domain` or Domain Identifier
        :param record: A :class:`Record`, or Record Identifier to delete
        """
        domain_id = domain.id if isinstance(domain, Domain) else domain
        record_id = record.id if isinstance(record, Record) else record

        uri = '/domains/%(domain_id)s/records/%(record_id)s' % {
            'domain_id': domain_id,
            'record_id': record_id
        }

        self.client.delete(uri)
