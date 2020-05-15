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


def _format_blacklist(blacklist):
    # Remove unneeded fields for display output formatting
    blacklist.pop('links', None)


class ListBlacklistsCommand(command.Lister):
    """List blacklists"""

    columns = ['id', 'pattern', 'description']

    def get_parser(self, prog_name):
        parser = super(ListBlacklistsCommand, self).get_parser(prog_name)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        cols = self.columns
        data = get_all(client.blacklists.list)
        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowBlacklistCommand(command.ShowOne):
    """Show blacklist details"""

    def get_parser(self, prog_name):
        parser = super(ShowBlacklistCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Blacklist ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.blacklists.get(parsed_args.id)
        _format_blacklist(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class CreateBlacklistCommand(command.ShowOne):
    """Create new blacklist"""

    def get_parser(self, prog_name):
        parser = super(CreateBlacklistCommand, self).get_parser(prog_name)

        parser.add_argument('--pattern', help="Blacklist pattern",
                            required=True)
        parser.add_argument('--description', help="Description")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.blacklists.create(
            parsed_args.pattern, parsed_args.description)

        _format_blacklist(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class SetBlacklistCommand(command.ShowOne):
    """Set blacklist properties"""

    def get_parser(self, prog_name):
        parser = super(SetBlacklistCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Blacklist ID")
        parser.add_argument('--pattern', help="Blacklist pattern")

        description_group = parser.add_mutually_exclusive_group()
        description_group.add_argument('--description', help="Description")
        description_group.add_argument('--no-description', action='store_true')

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        data = {}

        if parsed_args.pattern:
            data['pattern'] = parsed_args.pattern

        if parsed_args.no_description:
            data['description'] = None
        elif parsed_args.description:
            data['description'] = parsed_args.description

        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        updated = client.blacklists.update(parsed_args.id, data)

        _format_blacklist(updated)
        return six.moves.zip(*sorted(six.iteritems(updated)))


class DeleteBlacklistCommand(command.Command):
    """Delete blacklist"""

    def get_parser(self, prog_name):
        parser = super(DeleteBlacklistCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Blacklist ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        client.blacklists.delete(parsed_args.id)

        LOG.info('Blacklist %s was deleted', parsed_args.id)
