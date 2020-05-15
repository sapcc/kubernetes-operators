# Copyright 2017 SAP SE
#
# Author: Rudolf Vriend <rudolf.vriend@sap.com>
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


def _format_tsigkey(tsigkey):
    # Remove unneeded fields for display output formatting
    tsigkey.pop('links', None)


class ListTSIGKeysCommand(command.Lister):
    """List tsigkeys"""

    columns = ['id', 'name', 'algorithm', 'secret', 'scope', 'resource_id']

    def get_parser(self, prog_name):
        parser = super(ListTSIGKeysCommand, self).get_parser(prog_name)

        parser.add_argument('--name', help="TSIGKey NAME", required=False)
        parser.add_argument('--algorithm', help="TSIGKey algorithm",
                            required=False)
        parser.add_argument('--scope', help="TSIGKey scope", required=False)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        criterion = {}
        if parsed_args.name is not None:
            criterion["name"] = parsed_args.name
        if parsed_args.algorithm is not None:
            criterion["algorithm"] = parsed_args.algorithm
        if parsed_args.scope is not None:
            criterion["scope"] = parsed_args.scope

        data = get_all(client.tsigkeys.list, criterion)

        cols = self.columns
        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowTSIGKeyCommand(command.ShowOne):
    """Show tsigkey details"""

    def get_parser(self, prog_name):
        parser = super(ShowTSIGKeyCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="TSIGKey ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.tsigkeys.get(parsed_args.id)
        _format_tsigkey(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class CreateTSIGKeyCommand(command.ShowOne):
    """Create new tsigkey"""

    def get_parser(self, prog_name):
        parser = super(CreateTSIGKeyCommand, self).get_parser(prog_name)

        parser.add_argument('--name', help="TSIGKey Name", required=True)
        parser.add_argument('--algorithm', help="TSIGKey algorithm",
                            required=True)
        parser.add_argument('--secret', help="TSIGKey secret", required=True)
        parser.add_argument('--scope', help="TSIGKey scope", required=True)
        parser.add_argument('--resource-id', help="TSIGKey resource_id",
                            required=True)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.tsigkeys.create(parsed_args.name, parsed_args.algorithm,
                                      parsed_args.secret, parsed_args.scope,
                                      parsed_args.resource_id)
        _format_tsigkey(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class SetTSIGKeyCommand(command.ShowOne):
    """Set tsigkey properties"""

    def get_parser(self, prog_name):
        parser = super(SetTSIGKeyCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="TSIGKey ID")
        parser.add_argument('--name', help="TSIGKey Name")
        parser.add_argument('--algorithm', help="TSIGKey algorithm")
        parser.add_argument('--secret', help="TSIGKey secret")
        parser.add_argument('--scope', help="TSIGKey scope")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        data = {}

        if parsed_args.name:
            data['name'] = parsed_args.name
        if parsed_args.algorithm:
            data['algorithm'] = parsed_args.algorithm
        if parsed_args.secret:
            data['secret'] = parsed_args.secret
        if parsed_args.scope:
            data['scope'] = parsed_args.scope

        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.tsigkeys.update(parsed_args.id, data)
        _format_tsigkey(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class DeleteTSIGKeyCommand(command.Command):
    """Delete tsigkey"""

    def get_parser(self, prog_name):
        parser = super(DeleteTSIGKeyCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="TSIGKey ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        client.tsigkeys.delete(parsed_args.id)

        LOG.info('TSIGKey %s was deleted', parsed_args.id)
