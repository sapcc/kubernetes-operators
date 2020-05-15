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
from osc_lib import exceptions as osc_exc
import six

from designateclient import utils
from designateclient.v2.cli import common
from designateclient.v2.utils import get_all


LOG = logging.getLogger(__name__)


def _format_zone(zone):
    zone.pop('links', None)
    zone['masters'] = ", ".join(zone['masters'])
    attrib = ''
    for attr in zone['attributes']:
        attrib += "%s:%s\n" % (attr, zone['attributes'][attr])
    zone['attributes'] = attrib


def _format_zone_export_record(zone_export_record):
    zone_export_record.pop('links', None)


def _format_zone_import_record(zone_import_record):
    zone_import_record.pop('links', None)


class ListZonesCommand(command.Lister):
    """List zones"""

    columns = ['id', 'name', 'type', 'serial', 'status', 'action']

    def get_parser(self, prog_name):
        parser = super(ListZonesCommand, self).get_parser(prog_name)

        parser.add_argument('--name', help="Zone Name", required=False)
        parser.add_argument('--email', help="Zone Email", required=False)
        parser.add_argument('--type', help="Zone Type", required=False)
        parser.add_argument('--ttl', help="Time To Live (Seconds)",
                            required=False)
        parser.add_argument('--description', help="Description",
                            required=False)
        parser.add_argument('--status', help="Zone Status", required=False)

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

        if parsed_args.ttl is not None:
            criterion["ttl"] = parsed_args.ttl

        if parsed_args.description is not None:
            criterion["description"] = parsed_args.description

        if parsed_args.email is not None:
            criterion["email"] = parsed_args.email

        if parsed_args.status is not None:
            criterion["status"] = parsed_args.status

        data = get_all(client.zones.list, criterion)

        cols = self.columns

        if client.session.all_projects:
            cols.insert(1, 'project_id')

        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowZoneCommand(command.ShowOne):
    """Show zone details"""

    def get_parser(self, prog_name):
        parser = super(ShowZoneCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zones.get(parsed_args.id)

        _format_zone(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class CreateZoneCommand(command.ShowOne):
    """Create new zone"""

    def get_parser(self, prog_name):
        parser = super(CreateZoneCommand, self).get_parser(prog_name)

        parser.add_argument('name', help="Zone Name")
        parser.add_argument('--email', help="Zone Email")
        parser.add_argument('--type', help="Zone Type", default='PRIMARY')
        parser.add_argument('--ttl', type=int, help="Time To Live (Seconds)")
        parser.add_argument('--description', help="Description")
        parser.add_argument('--masters', help="Zone Masters", nargs='+')
        parser.add_argument('--attributes', help="Zone Attributes", nargs='+')

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        payload = {}

        if parsed_args.description:
            payload["description"] = parsed_args.description

        if parsed_args.attributes:
            payload["attributes"] = {}
            for attr in parsed_args.attributes:
                try:
                    k, v = attr.split(':')
                    payload["attributes"][k] = v
                except ValueError:
                    msg = "Attribute '%s' is in an incorrect format. "\
                          "Attributes are <key>:<value> formated"
                    raise osc_exc.CommandError(msg % attr)

        if parsed_args.type == 'PRIMARY':
            # email is just for PRIMARY.
            if not parsed_args.email:
                msg = "Zone type PRIMARY requires --email."
                raise osc_exc.CommandError(msg)

            payload["email"] = parsed_args.email

            # TTL is just valid for PRIMARY
            if parsed_args.ttl is not None:
                payload["ttl"] = parsed_args.ttl
        elif parsed_args.type == 'SECONDARY':
            payload["masters"] = parsed_args.masters
        else:
            msg = "Type %s is not supported. Please choose between " \
                "PRIMARY or SECONDARY"
            raise osc_exc.CommandError(msg % parsed_args.type)

        data = client.zones.create(
            parsed_args.name, parsed_args.type, **payload)

        _format_zone(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class SetZoneCommand(command.ShowOne):
    """Set zone properties"""

    def get_parser(self, prog_name):
        parser = super(SetZoneCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone ID")
        parser.add_argument('--email', help="Zone Email")
        parser.add_argument('--ttl', type=int, help="Time To Live (Seconds)")
        description_group = parser.add_mutually_exclusive_group()
        description_group.add_argument('--description', help="Description")
        description_group.add_argument('--no-description', action='store_true')

        parser.add_argument('--masters', help="Zone Masters", nargs='+')

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = {}

        # TODO(kiall): API needs updating.. this get is silly
        if parsed_args.email:
            data['email'] = parsed_args.email

        if parsed_args.ttl:
            data['ttl'] = parsed_args.ttl

        if parsed_args.no_description:
            data['description'] = None
        elif parsed_args.description:
            data['description'] = parsed_args.description

        if parsed_args.masters:
            data['masters'] = parsed_args.masters

        updated = client.zones.update(parsed_args.id, data)
        _format_zone(updated)
        return six.moves.zip(*sorted(six.iteritems(updated)))


class DeleteZoneCommand(command.ShowOne):
    """Delete zone"""

    def get_parser(self, prog_name):
        parser = super(DeleteZoneCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zones.delete(parsed_args.id)
        LOG.info('Zone %s was deleted', parsed_args.id)

        _format_zone(data)
        return six.moves.zip(*sorted(six.iteritems(data)))


class AbandonZoneCommand(command.Command):
    """Abandon a zone"""
    def get_parser(self, prog_name):
        parser = super(AbandonZoneCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        client.zones.abandon(parsed_args.id)

        LOG.info("Z %(zone_id)s abandoned",
                 {"zone_id": parsed_args.id})


class AXFRZoneCommand(command.Command):
    """AXFR a zone"""
    def get_parser(self, prog_name):
        parser = super(AXFRZoneCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        client.zones.axfr(parsed_args.id)

        LOG.info("Scheduled AXFR for zone %(zone_id)s",
                 {"zone_id": parsed_args.id})


class CreateTransferRequestCommand(command.ShowOne):
    """Create new zone transfer request"""

    def get_parser(self, prog_name):
        parser = super(CreateTransferRequestCommand, self).get_parser(
            prog_name)

        parser.add_argument('zone_id', help="Zone ID to transfer.",)
        parser.add_argument(
            '--target-project-id',
            help="Target Project ID to transfer to.")
        parser.add_argument('--description', help="Description")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_transfers.create_request(
            parsed_args.zone_id, parsed_args.target_project_id,
            parsed_args.description)
        return six.moves.zip(*sorted(six.iteritems(data)))


class ListTransferRequestsCommand(command.Lister):
    """List Zone Transfer Requests"""

    columns = ['id', 'zone_id', 'zone_name', 'project_id',
               'target_project_id', 'status', 'key']

    def get_parser(self, prog_name):
        parser = super(ListTransferRequestsCommand, self).get_parser(
            prog_name)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_transfers.list_requests()

        cols = self.columns
        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowTransferRequestCommand(command.ShowOne):
    """Show Zone Transfer Request Details"""

    def get_parser(self, prog_name):
        parser = super(ShowTransferRequestCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone Tranfer Request ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_transfers.get_request(parsed_args.id)

        return six.moves.zip(*sorted(six.iteritems(data)))


class SetTransferRequestCommand(command.ShowOne):
    """Set a Zone Transfer Request"""

    def get_parser(self, prog_name):
        parser = super(SetTransferRequestCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone Transfer Request ID")
        description_group = parser.add_mutually_exclusive_group()
        description_group.add_argument('--description', help="Description")
        description_group.add_argument('--no-description', action='store_true')

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = {}

        if parsed_args.no_description:
            data['description'] = None
        elif parsed_args.description:
            data['description'] = parsed_args.description

        updated = client.zone_transfers.update_request(parsed_args.id, data)
        return six.moves.zip(*sorted(six.iteritems(updated)))


class DeleteTransferRequestCommand(command.Command):
    """Delete a Zone Transfer Request"""
    def get_parser(self, prog_name):
        parser = super(DeleteTransferRequestCommand, self).get_parser(
            prog_name)

        parser.add_argument('id', help="Zone Transfer Request ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        client.zone_transfers.delete_request(parsed_args.id)

        LOG.info('Zone Transfer %s was deleted', parsed_args.id)


class AcceptTransferRequestCommand(command.ShowOne):
    """Accept a Zone Transfer Request"""

    def get_parser(self, prog_name):
        parser = super(AcceptTransferRequestCommand, self).get_parser(
            prog_name)

        parser.add_argument('--transfer-id', help="Transfer ID", type=str,
                            required=True)
        parser.add_argument('--key', help="Transfer Key", type=str,
                            required=True)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_transfers.accept_request(
            parsed_args.transfer_id, parsed_args.key)
        return six.moves.zip(*sorted(six.iteritems(data)))


class ListTransferAcceptsCommand(command.Lister):
    """List Zone Transfer Accepts"""

    columns = ['id', 'zone_id', 'project_id',
               'zone_transfer_request_id', 'status', 'key']

    def get_parser(self, prog_name):
        parser = super(ListTransferAcceptsCommand, self).get_parser(
            prog_name)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_transfers.list_requests()

        cols = self.columns
        return cols, (utils.get_item_properties(s, cols) for s in data)


class ShowTransferAcceptCommand(command.ShowOne):
    """Show Zone Transfer Accept"""

    def get_parser(self, prog_name):
        parser = super(ShowTransferAcceptCommand, self).get_parser(prog_name)

        parser.add_argument('id', help="Zone Tranfer Accept ID")

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_transfers.get_accept(parsed_args.id)

        return six.moves.zip(*sorted(six.iteritems(data)))


class ExportZoneCommand(command.ShowOne):
    """Export a Zone"""

    def get_parser(self, prog_name):
        parser = super(ExportZoneCommand, self).get_parser(
            prog_name)

        common.add_all_common_options(parser)

        parser.add_argument('zone_id', help="Zone ID", type=str)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_exports.create(parsed_args.zone_id)
        _format_zone_export_record(data)

        LOG.info('Zone Export %s was created', data['id'])

        return six.moves.zip(*sorted(six.iteritems(data)))


class ListZoneExportsCommand(command.Lister):
    """List Zone Exports"""

    columns = [
        'id',
        'zone_id',
        'created_at',
        'status',
    ]

    def get_parser(self, prog_name):
        parser = super(ListZoneExportsCommand, self).get_parser(
            prog_name)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_exports.list()

        cols = self.columns
        return cols, (utils.get_item_properties(s, cols)
                      for s in data['exports'])


class ShowZoneExportCommand(command.ShowOne):
    """Show a Zone Export"""

    def get_parser(self, prog_name):
        parser = super(ShowZoneExportCommand, self).get_parser(
            prog_name)

        parser.add_argument('zone_export_id', help="Zone Export ID", type=str)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_exports.get_export_record(
            parsed_args.zone_export_id)
        _format_zone_export_record(data)

        return six.moves.zip(*sorted(six.iteritems(data)))


class DeleteZoneExportCommand(command.Command):
    """Delete a Zone Export"""

    def get_parser(self, prog_name):
        parser = super(DeleteZoneExportCommand, self).get_parser(
            prog_name)

        parser.add_argument('zone_export_id', help="Zone Export ID", type=str)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        client.zone_exports.delete(parsed_args.zone_export_id)

        LOG.info('Zone Export %s was deleted', parsed_args.zone_export_id)


class ShowZoneExportFileCommand(command.ShowOne):
    """Show the zone file for the Zone Export"""

    def get_parser(self, prog_name):
        parser = super(ShowZoneExportFileCommand, self).get_parser(
            prog_name)

        parser.add_argument('zone_export_id', help="Zone Export ID", type=str)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_exports.get_export(parsed_args.zone_export_id)

        return ['data'], [data]


class ImportZoneCommand(command.ShowOne):
    """Import a Zone from a file on the filesystem"""

    def get_parser(self, prog_name):
        parser = super(ImportZoneCommand, self).get_parser(
            prog_name)

        parser.add_argument('zone_file_path',
                            help="Path to a zone file", type=str)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        with open(parsed_args.zone_file_path, 'r') as f:
            zone_file_contents = f.read()

        data = client.zone_imports.create(zone_file_contents)
        _format_zone_import_record(data)

        LOG.info('Zone Import %s was created', data['id'])

        return six.moves.zip(*sorted(six.iteritems(data)))


class ListZoneImportsCommand(command.Lister):
    """List Zone Imports"""

    columns = [
        'id',
        'zone_id',
        'created_at',
        'status',
        'message',
    ]

    def get_parser(self, prog_name):
        parser = super(ListZoneImportsCommand, self).get_parser(
            prog_name)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_imports.list()

        cols = self.columns
        return cols, (utils.get_item_properties(s, cols)
                      for s in data['imports'])


class ShowZoneImportCommand(command.ShowOne):
    """Show a Zone Import"""

    def get_parser(self, prog_name):
        parser = super(ShowZoneImportCommand, self).get_parser(
            prog_name)

        parser.add_argument('zone_import_id', help="Zone Import ID", type=str)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        data = client.zone_imports.get_import_record(
            parsed_args.zone_import_id)
        _format_zone_import_record(data)

        return six.moves.zip(*sorted(six.iteritems(data)))


class DeleteZoneImportCommand(command.Command):
    """Delete a Zone Import"""

    def get_parser(self, prog_name):
        parser = super(DeleteZoneImportCommand, self).get_parser(
            prog_name)

        parser.add_argument('zone_import_id', help="Zone Import ID", type=str)

        common.add_all_common_options(parser)

        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.dns
        common.set_all_common_headers(client, parsed_args)

        client.zone_imports.delete(parsed_args.zone_import_id)

        LOG.info('Zone Import %s was deleted', parsed_args.zone_import_id)
