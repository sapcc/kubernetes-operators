# Copyright 2014 Hewlett-Packard Development Company, L.P.
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
import itertools
import logging

from cliff import command
from cliff import show
import six

from designateclient.v2.cli import common

LOG = logging.getLogger(__name__)


DNS_QUOTAS = {
    "api_export_size": "api-export-size",
    "recordset_records": "recordset-records",
    "zone_records": "zone-records",
    "zone_recordsets": "zone-recordsets",
    "zones": "zones"
}


class ListQuotasCommand(show.ShowOne):
    """List quotas"""

    # columns = ['resource', 'hard_limit']

    def get_parser(self, prog_name):
        parser = super(ListQuotasCommand, self).get_parser(prog_name)

        common.add_all_common_options(parser)

        parser.add_argument(
            '--project-id',
            help="Project ID Default: current project")

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        proj_id = parsed_args.project_id or client.session.get_project_id()

        if parsed_args.project_id != client.session.get_project_id():
            common.set_all_projects(client, True)

        data = client.quotas.list(proj_id)
        return six.moves.zip(*sorted(six.iteritems(data)))


class SetQuotasCommand(show.ShowOne):
    """Set quotas"""

    def _build_options_list(self):
            return itertools.chain(DNS_QUOTAS.items())

    def get_parser(self, prog_name):
        parser = super(SetQuotasCommand, self).get_parser(prog_name)

        common.add_all_common_options(parser)

        parser.add_argument('--project-id', help="Project ID")
        for k, v in self._build_options_list():
            parser.add_argument(
                '--%s' % v,
                metavar='<%s>' % v,
                dest=k,
                type=int,
                help='New value for the %s quota' % v,
            )

        return parser

    def take_action(self, parsed_args):

        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        quotas = {}
        for k, v in DNS_QUOTAS.items():
            value = getattr(parsed_args, k, None)
            if value is not None:
                quotas[k] = value

        proj_id = parsed_args.project_id or client.session.get_project_id()

        if parsed_args.project_id != client.session.get_project_id():
            common.set_all_projects(client, True)

        updated = client.quotas.update(proj_id, quotas)

        return six.moves.zip(*sorted(six.iteritems(updated)))


class ResetQuotasCommand(command.Command):
    """Reset quotas"""

    def get_parser(self, prog_name):
        parser = super(ResetQuotasCommand, self).get_parser(prog_name)

        common.add_all_common_options(parser)

        parser.add_argument('--project-id', help="Project ID")

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        proj_id = parsed_args.project_id or client.session.get_project_id()

        if parsed_args.project_id != client.session.get_project_id():
            common.set_all_projects(client, True)

        client.quotas.reset(proj_id)

        LOG.info('Quota for project %s was reset', parsed_args.project_id)
