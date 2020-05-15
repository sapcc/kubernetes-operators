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

import argparse
import logging

from osc_lib.command import command
import six

from designateclient import utils
from designateclient.v2.cli import common
from designateclient.v2.utils import get_all


LOG = logging.getLogger(__name__)


def _format_recordset(recordset):
    # Remove unneeded fields for display output formatting
    recordset['records'] = "\n".join(recordset['records'])
    recordset.pop('links', None)
    return recordset


def _has_project_id(data):
    if len(data) < 1:
        return False
    if 'project_id' in data[0]:
        return True
    return False


class ListRecordSetsCommand(command.Lister):
    """List recordsets"""

    columns = ['id', 'name', 'type', 'records', 'status', 'action']

    def get_parser(self, prog_name):
        parser = super(ListRecordSetsCommand, self).get_parser(prog_name)

        parser.add_argument('--name', help="RecordSet Name", required=False)
        parser.add_argument('--type', help="RecordSet Type", required=False)
        parser.add_argument('--data', help="RecordSet Record Data",
                            required=False)
        parser.add_argument('--ttl', help="Time To Live (Seconds)",
                            required=False)
        parser.add_argument('--description', help="Description",
                            required=False)
        parser.add_argument('--status', help="RecordSet Status",
                            required=False)
        parser.add_argument('--action', help="RecordSet Action",
                            required=False)

        parser.add_argument('zone_id', help="Zone ID. To list all"
                            " recordsets specify 'all'")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        criterion = {}
        if parsed_args.type is not None:
            criterion["type"] = parsed_args.type

        if parsed_args.name is not None:
            criterion["name"] = parsed_args.name

        if parsed_args.data is not None:
            criterion["data"] = parsed_args.data

        if parsed_args.ttl is not None:
            criterion["ttl"] = parsed_args.ttl

        if parsed_args.description is not None:
            criterion["description"] = parsed_args.description

        if parsed_args.status is not None:
            criterion["status"] = parsed_args.status

        if parsed_args.action is not None:
            criterion["action"] = parsed_args.action

        cols = self.columns

        if parsed_args.zone_id == 'all':
            data = get_all(client.recordsets.list_all_zones,
                           criterion=criterion)
            cols.insert(2, 'zone_name')
        else:
            data = get_all(client.recordsets.list, args=[parsed_args.zone_id],
                           criterion=criterion)

        if client.session.all_projects and _has_project_id(data):
            cols.insert(1, 'project_id')

        for i, rs in enumerate(data):
            data[i] = _format_recordset(rs)

        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowRecordSetCommand(command.ShowOne):
    """Show recordset details"""

    def get_parser(self, prog_name):
        parser = super(ShowRecordSetCommand, self).get_parser(prog_name)

        parser.add_argument('zone_id', help="Zone ID")
        parser.add_argument('id', help="RecordSet ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.recordsets.get(parsed_args.zone_id, parsed_args.id)

        _format_recordset(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class CreateRecordSetCommand(command.ShowOne):
    """Create new recordset"""

    log = logging.getLogger('deprecated')

    def get_parser(self, prog_name):
        parser = super(CreateRecordSetCommand, self).get_parser(prog_name)

        parser.add_argument('zone_id', help="Zone ID")
        parser.add_argument('name', help="RecordSet Name")
        req_group = parser.add_mutually_exclusive_group(required=True)
        req_group.add_argument(
            '--records',
            help=argparse.SUPPRESS,
            nargs='+')
        req_group.add_argument(
            '--record',
            help="RecordSet Record, repeat if necessary",
            action='append')
        parser.add_argument('--type', help="RecordSet Type", required=True)
        parser.add_argument('--ttl', type=int, help="Time To Live (Seconds)")
        parser.add_argument('--description', help="Description")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        all_records = parsed_args.record or parsed_args.records
        if parsed_args.records:
            self.log.warning(
                "Option --records is deprecated, use --record instead.")
        data = client.recordsets.create(
            parsed_args.zone_id,
            parsed_args.name,
            parsed_args.type,
            all_records,
            description=parsed_args.description,
            ttl=parsed_args.ttl)

        _format_recordset(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class SetRecordSetCommand(command.ShowOne):
    """Set recordset properties"""

    def get_parser(self, prog_name):
        parser = super(SetRecordSetCommand, self).get_parser(prog_name)

        parser.add_argument('zone_id', help="Zone ID")
        parser.add_argument('id', help="RecordSet ID")
        req_group = parser.add_mutually_exclusive_group()
        req_group.add_argument(
            '--records',
            help=argparse.SUPPRESS,
            nargs='+')
        req_group.add_argument(
            '--record',
            help="RecordSet Record, repeat if necessary",
            action='append')

        description_group = parser.add_mutually_exclusive_group()
        description_group.add_argument('--description', help="Description")
        description_group.add_argument('--no-description', action='store_true')

        ttl_group = parser.add_mutually_exclusive_group()
        ttl_group.add_argument('--ttl', type=int, help="TTL")
        ttl_group.add_argument('--no-ttl', action='store_true')

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        data = {}

        if parsed_args.no_description:
            data['description'] = None
        elif parsed_args.description:
            data['description'] = parsed_args.description

        if parsed_args.no_ttl:
            data['ttl'] = None
        elif parsed_args.ttl:
            data['ttl'] = parsed_args.ttl

        all_records = parsed_args.record or parsed_args.records
        if parsed_args.records:
            self.log.warning(
                "Option --records is deprecated, use --record instead.")

        if all_records:
            data['records'] = all_records

        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        updated = client.recordsets.update(
            parsed_args.zone_id,
            parsed_args.id,
            data)

        _format_recordset(updated)

        return six.moves.zip(*sorted(six.iteritems(updated)))


class DeleteRecordSetCommand(command.ShowOne):
    """Delete recordset"""

    def get_parser(self, prog_name):
        parser = super(DeleteRecordSetCommand, self).get_parser(prog_name)

        parser.add_argument('zone_id', help="Zone ID")
        parser.add_argument('id', help="RecordSet ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)
        data = client.recordsets.delete(parsed_args.zone_id, parsed_args.id)

        LOG.info('RecordSet %s was deleted', parsed_args.id)

        _format_recordset(data)
        return six.moves.zip(*sorted(six.iteritems(data)))
