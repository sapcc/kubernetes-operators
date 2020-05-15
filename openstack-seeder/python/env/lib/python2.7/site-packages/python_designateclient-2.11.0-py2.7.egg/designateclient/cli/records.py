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

import logging

from designateclient.cli import base
from designateclient.v1.records import Record

LOG = logging.getLogger(__name__)


class ListRecordsCommand(base.ListCommand):
    """List Records"""

    columns = ['id', 'type', 'name', 'data']

    def get_parser(self, prog_name):
        parser = super(ListRecordsCommand, self).get_parser(prog_name)

        parser.add_argument('domain_id', help="Domain ID or name.")

        return parser

    def execute(self, parsed_args):
        domain_id = self.find_resourceid_by_name_or_id(
            'domains', parsed_args.domain_id)
        return self.client.records.list(domain_id)


class GetRecordCommand(base.GetCommand):
    """Get Record"""

    def get_parser(self, prog_name):
        parser = super(GetRecordCommand, self).get_parser(prog_name)

        parser.add_argument('domain_id', help="Domain ID or name.")
        parser.add_argument('id', help="Record ID.")

        return parser

    def execute(self, parsed_args):
        domain_id = self.find_resourceid_by_name_or_id(
            'domains', parsed_args.domain_id)
        return self.client.records.get(domain_id, parsed_args.id)


class CreateRecordCommand(base.CreateCommand):
    """Create Record"""

    def get_parser(self, prog_name):
        parser = super(CreateRecordCommand, self).get_parser(prog_name)

        parser.add_argument('domain_id', help="Domain ID or name.")
        parser.add_argument(
            '--name', help="Record (relative|absolute) name.", required=True)
        parser.add_argument('--type', help="Record type.", required=True)
        parser.add_argument('--data', help="Record data.", required=True)
        parser.add_argument('--ttl', type=int, help="Record TTL.")
        parser.add_argument('--priority', type=int, help="Record priority.")
        parser.add_argument('--description', help="Description.")

        return parser

    def execute(self, parsed_args):
        domain_id = self.find_resourceid_by_name_or_id(
            'domains', parsed_args.domain_id)

        if not parsed_args.name.endswith('.'):
            # Relative name?
            domain_name = self.client.domains.get(domain_id)['name']
            absolute = parsed_args.name + '.'
            relative = absolute + domain_name
            if absolute.endswith('.' + domain_name):
                # Relative name or absolute name missing final period?
                msg = ('"%s" is a relative name but looks like an absolute '
                       'name, use --name "%s" or "%s"'
                       % (parsed_args.name, absolute, relative))
                raise ValueError(msg)
            parsed_args.name = relative

        record = Record(
            name=parsed_args.name,
            type=parsed_args.type,
            data=parsed_args.data,
        )

        if parsed_args.ttl is not None:
            record.ttl = parsed_args.ttl

        if parsed_args.priority is not None:
            record.priority = parsed_args.priority

        if parsed_args.description:
            record.description = parsed_args.description

        return self.client.records.create(domain_id, record)


class UpdateRecordCommand(base.UpdateCommand):
    """Update Record"""

    def get_parser(self, prog_name):
        parser = super(UpdateRecordCommand, self).get_parser(prog_name)

        parser.add_argument('domain_id', help="Domain ID or name.")
        parser.add_argument('id', help="Record ID.")
        parser.add_argument('--name', help="Record name.")
        parser.add_argument('--type', help="Record type.")
        parser.add_argument('--data', help="Record data.")

        description_group = parser.add_mutually_exclusive_group()
        description_group.add_argument('--description', help="Description.")
        description_group.add_argument('--no-description', action='store_true')

        ttl_group = parser.add_mutually_exclusive_group()
        ttl_group.add_argument('--ttl', type=int,
                               help="Record time to live (seconds).")
        ttl_group.add_argument('--no-ttl', action='store_true')

        priotity_group = parser.add_mutually_exclusive_group()
        priotity_group.add_argument('--priority', type=int,
                                    help="Record priority.")
        priotity_group.add_argument('--no-priority', action='store_true')

        return parser

    def execute(self, parsed_args):
        # TODO(kiall): API needs updating.. this get is silly
        record = self.client.records.get(parsed_args.domain_id, parsed_args.id)

        if parsed_args.name:
            record.name = parsed_args.name

        if parsed_args.type:
            record.type = parsed_args.type

        if parsed_args.data:
            record.data = parsed_args.data

        if parsed_args.no_ttl:
            record.ttl = None
        elif parsed_args.ttl is not None:
            record.ttl = parsed_args.ttl

        if parsed_args.no_priority:
            record.priority = None
        elif parsed_args.priority is not None:
            record.priority = parsed_args.priority

        if parsed_args.no_description:
            record.description = None
        elif parsed_args.description:
            record.description = parsed_args.description

        domain_id = self.find_resourceid_by_name_or_id(
            'domains', parsed_args.domain_id)
        return self.client.records.update(domain_id, record)


class DeleteRecordCommand(base.DeleteCommand):
    """Delete Record"""

    def get_parser(self, prog_name):
        parser = super(DeleteRecordCommand, self).get_parser(prog_name)

        parser.add_argument('domain_id', help="Domain ID or name.")
        parser.add_argument('id', help="Record ID.")

        return parser

    def execute(self, parsed_args):
        domain_id = self.find_resourceid_by_name_or_id(
            'domains', parsed_args.domain_id)
        return self.client.records.delete(domain_id, parsed_args.id)
