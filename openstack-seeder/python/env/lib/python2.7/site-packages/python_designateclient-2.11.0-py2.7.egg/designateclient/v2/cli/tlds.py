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

import logging

from osc_lib.command import command
import six

from designateclient import utils
from designateclient.v2.cli import common
from designateclient.v2.utils import get_all


LOG = logging.getLogger(__name__)


def _format_tld(tld):
    # Remove unneeded fields for display output formatting
    tld.pop('links', None)


class ListTLDsCommand(command.Lister):
    """List tlds"""

    columns = ['id', 'name', 'description']

    def get_parser(self, prog_name):
        parser = super(ListTLDsCommand, self).get_parser(prog_name)

        parser.add_argument('--name', help="TLD NAME")

        parser.add_argument('--description', help="TLD Description")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = get_all(client.tlds.list)

        cols = self.columns
        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowTLDCommand(command.ShowOne):
    """Show tld details"""

    def get_parser(self, prog_name):
        parser = super(ShowTLDCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="TLD ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.tlds.get(parsed_args.id)
        _format_tld(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class CreateTLDCommand(command.ShowOne):
    """Create new tld"""

    def get_parser(self, prog_name):
        parser = super(CreateTLDCommand, self).get_parser(prog_name)

        parser.add_argument('--name', help="TLD Name", required=True)
        parser.add_argument('--description', help="Description")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.tlds.create(parsed_args.name, parsed_args.description)
        _format_tld(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class SetTLDCommand(command.ShowOne):
    """Set tld properties"""

    def get_parser(self, prog_name):
        parser = super(SetTLDCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="TLD ID")
        parser.add_argument('--name', help="TLD Name")
        description_group = parser.add_mutually_exclusive_group()
        description_group.add_argument('--description', help="Description")
        description_group.add_argument('--no-description', action='store_true')

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        data = {}

        if parsed_args.name:
            data['name'] = parsed_args.name

        if parsed_args.no_description:
            data['description'] = None
        elif parsed_args.description:
            data['description'] = parsed_args.description

        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.tlds.update(parsed_args.id, data)
        _format_tld(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class DeleteTLDCommand(command.Command):
    """Delete tld"""

    def get_parser(self, prog_name):
        parser = super(DeleteTLDCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="TLD ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        client.tlds.delete(parsed_args.id)

        LOG.info('TLD %s was deleted', parsed_args.id)
