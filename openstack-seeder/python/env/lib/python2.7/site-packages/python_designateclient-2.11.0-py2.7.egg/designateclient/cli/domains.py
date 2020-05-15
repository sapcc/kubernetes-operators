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
from designateclient.v1.domains import Domain

LOG = logging.getLogger(__name__)


class ListDomainsCommand(base.ListCommand):
    """List Domains"""

    columns = ['id', 'name', 'serial']

    def execute(self, parsed_args):
        return self.client.domains.list()


class GetDomainCommand(base.GetCommand):
    """Get Domain"""

    def get_parser(self, prog_name):
        parser = super(GetDomainCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Domain ID or name.")

        return parser

    def execute(self, parsed_args):
        id = self.find_resourceid_by_name_or_id('domains', parsed_args.id)
        return self.client.domains.get(id)


class CreateDomainCommand(base.CreateCommand):
    """Create Domain"""

    def get_parser(self, prog_name):
        parser = super(CreateDomainCommand, self).get_parser(prog_name)

        parser.add_argument('--name', help="Domain name.", required=True)
        parser.add_argument('--email', help="Domain email.", required=True)
        parser.add_argument('--ttl', type=int, help="Time to live (seconds).")
        parser.add_argument('--description', help="Description.")

        return parser

    def execute(self, parsed_args):
        domain = Domain(
            name=parsed_args.name,
            email=parsed_args.email,
        )

        if parsed_args.description:
            domain.description = parsed_args.description

        if parsed_args.ttl is not None:
            domain.ttl = parsed_args.ttl

        return self.client.domains.create(domain)


class UpdateDomainCommand(base.UpdateCommand):
    """Update Domain"""

    def get_parser(self, prog_name):
        parser = super(UpdateDomainCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Domain ID or name.")
        parser.add_argument('--name', help="Domain name.")
        parser.add_argument('--email', help="Domain email.")
        parser.add_argument('--ttl', type=int, help="Time to live (seconds).")
        description_group = parser.add_mutually_exclusive_group()
        description_group.add_argument('--description', help="Description.")
        description_group.add_argument('--no-description', action='store_true')

        return parser

    def execute(self, parsed_args):
        # TODO(kiall): API needs updating.. this get is silly
        id = self.find_resourceid_by_name_or_id('domains', parsed_args.id)
        domain = self.client.domains.get(id)

        if parsed_args.name:
            domain.name = parsed_args.name

        if parsed_args.email:
            domain.email = parsed_args.email

        if parsed_args.ttl is not None:
            domain.ttl = parsed_args.ttl

        if parsed_args.no_description:
            domain.description = None
        elif parsed_args.description:
            domain.description = parsed_args.description

        return self.client.domains.update(domain)


class DeleteDomainCommand(base.DeleteCommand):
    """Delete Domain"""

    def get_parser(self, prog_name):
        parser = super(DeleteDomainCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Domain ID or name.")

        return parser

    def execute(self, parsed_args):
        id = self.find_resourceid_by_name_or_id('domains', parsed_args.id)
        return self.client.domains.delete(id)


class ListDomainServersCommand(base.ListCommand):
    """List Domain Servers"""

    columns = ['name']

    def get_parser(self, prog_name):
        parser = super(ListDomainServersCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Domain ID or name.")

        return parser

    def execute(self, parsed_args):
        id = self.find_resourceid_by_name_or_id('domains', parsed_args.id)
        return self.client.domains.list_domain_servers(id)
