# Copyright 2016 Hewlett Packard Enterprise Development Company LP
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
from designateclient.v2 import utils as v2_utils


LOG = logging.getLogger(__name__)


def _format_status(status):
    status.pop("links", None)
    # Remove unneeded fields for display output formatting
    for k in ("capabilities", "stats"):
        status[k] = "\n".join(status[k]) if status[k] else "-"
    return status


class ListServiceStatusesCommand(command.Lister):
    """List service statuses"""

    columns = ['id', 'hostname', 'service_name', 'status', 'stats',
               'capabilities']

    def get_parser(self, prog_name):
        parser = super(ListServiceStatusesCommand, self).get_parser(prog_name)

        parser.add_argument("--hostname", help="Hostname", required=False)
        parser.add_argument("--service_name", help="Service Name",
                            required=False)
        parser.add_argument("--status", help="Status", required=False)
        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        cols = self.columns

        criterion = {}
        for i in ["hostname", "service_name", "status"]:
            v = getattr(parsed_args, i)
            if v is not None:
                criterion[i] = v

        data = v2_utils.get_all(client.service_statuses.list,
                                criterion=criterion)

        for i, s in enumerate(data):
            data[i] = _format_status(s)

        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowServiceStatusCommand(command.ShowOne):
    """Show service status details"""

    def get_parser(self, prog_name):
        parser = super(ShowServiceStatusCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Service Status ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.service_statuses.get(parsed_args.id)

        _format_status(data)
        return six.moves.zip(*sorted(six.iteritems(data)))
