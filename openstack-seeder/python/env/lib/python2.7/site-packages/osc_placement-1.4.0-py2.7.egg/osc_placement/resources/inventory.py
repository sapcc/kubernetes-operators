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

from collections import defaultdict

from osc_lib.command import command
from osc_lib import utils

from osc_placement import version


BASE_URL = '/resource_providers/{uuid}/inventories'
PER_CLASS_URL = BASE_URL + '/{resource_class}'
RP_BASE_URL = '/resource_providers'
INVENTORY_FIELDS = {
    'allocation_ratio': {
        'type': float,
        'required': False,
        'help': ('It is used in determining whether consumption '
                 'of the resource of the provider can exceed '
                 'physical constraints. For example, for a vCPU resource '
                 'with: allocation_ratio = 16.0, total = 8. '
                 'Overall capacity is equal to 128 vCPUs.')
    },
    'min_unit': {
        'type': int,
        'required': False,
        'help': ('A minimum amount any single allocation against '
                 'an inventory can have.')
    },
    'max_unit': {
        'type': int,
        'required': False,
        'help': ('A maximum amount any single allocation against '
                 'an inventory can have.')
    },
    'reserved': {
        'type': int,
        'required': False,
        'help': ('The amount of the resource a provider has reserved '
                 'for its own use.')
    },
    'step_size': {
        'type': int,
        'required': False,
        'help': ('A representation of the divisible amount of the resource '
                 'that may be requested. For example, step_size = 5 means '
                 'that only values divisible by 5 (5, 10, 15, etc.) '
                 'can be requested.')
    },
    'total': {
        'type': int,
        'required': True,
        'help': ('The actual amount of the resource that the provider '
                 'can accommodate.')
    }
}
FIELDS = tuple(INVENTORY_FIELDS.keys())
RC_HELP = ('<resource_class> is an entity that indicates standard or '
           'deployer-specific resources that can be provided by a resource '
           'provider. For example, VCPU, MEMORY_MB, DISK_GB.')


def parse_resource_argument(resource):
    parts = resource.split('=')
    if len(parts) != 2:
        raise ValueError(
            'Resource argument must have "name=value" format')
    name, value = parts
    parts = name.split(':')
    if len(parts) == 2:
        name, field = parts
    elif len(parts) == 1:
        name = parts[0]
        field = 'total'
    else:
        raise ValueError('Resource argument can contain only one colon')
    if not all([name, field, value]):
        raise ValueError('Name, field and value must be not empty')
    if field not in INVENTORY_FIELDS:
        raise ValueError('Unknown inventory field %s' % field)
    value = INVENTORY_FIELDS[field]['type'](value)
    return name, field, value


class SetInventory(command.Lister):

    """Replaces the set of inventory records for the resource provider.

    Note that this is a full replacement of the existing inventory. If you
    want to retain the existing inventory and add a new resource class
    inventory, you must specify all resource class inventory, old and new.

    If a specific inventory field is not specified for a given resource class,
    it is assumed to be the total, i.e. --resource VCPU=16 is equivalent to
    --resource VCPU:total=16.

    Example: openstack resource provider inventory set <uuid> \
                 --resource VCPU=16 \
                 --resource MEMORY_MB=2048 \
                 --resource MEMORY_MB:step_size=128

    """

    def get_parser(self, prog_name):
        parser = super(SetInventory, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )
        fields_help = '\n'.join(
            '{} - {}'.format(f, INVENTORY_FIELDS[f]['help'].lower())
            for f in INVENTORY_FIELDS)
        parser.add_argument(
            '--resource',
            metavar='<resource_class>:<inventory_field>=<value>',
            help='String describing resource.\n' + RC_HELP + '\n'
                 '<inventory_field> (optional) can be:\n' + fields_help,
            default=[],
            action='append'
        )

        return parser

    def take_action(self, parsed_args):

        inventories = defaultdict(dict)
        for r in parsed_args.resource:
            name, field, value = parse_resource_argument(r)
            inventories[name][field] = value

        http = self.app.client_manager.placement

        url = RP_BASE_URL + '/' + parsed_args.uuid
        rp = http.request('GET', url).json()

        payload = {'inventories': inventories,
                   'resource_provider_generation': rp['generation']}
        url = BASE_URL.format(uuid=parsed_args.uuid)
        resources = http.request('PUT', url, json=payload).json()

        inventories = [
            dict(resource_class=k, **v)
            for k, v in resources['inventories'].items()
        ]

        fields = ('resource_class', ) + FIELDS
        rows = (utils.get_dict_properties(i, fields) for i in inventories)
        return fields, rows


class SetClassInventory(command.ShowOne):

    """Replace the inventory record of the class for the resource provider.

    Example: openstack resource provider inventory class set <uuid> VCPU \
                 --total 16 \
                 --max_unit 4 \
                 --reserved 1

    """

    def get_parser(self, prog_name):
        parser = super(SetClassInventory, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )
        parser.add_argument(
            'resource_class',
            metavar='<class>',
            help=RC_HELP
        )
        for name, props in INVENTORY_FIELDS.items():
            parser.add_argument(
                '--' + name,
                metavar='<{}>'.format(name),
                required=props['required'],
                type=props['type'],
                help=props['help'])

        return parser

    def take_action(self, parsed_args):

        http = self.app.client_manager.placement

        url = RP_BASE_URL + '/' + parsed_args.uuid
        rp = http.request('GET', url).json()

        payload = {'resource_provider_generation': rp['generation']}
        for field in FIELDS:
            value = getattr(parsed_args, field, None)
            if value is not None:
                payload[field] = value

        url = PER_CLASS_URL.format(uuid=parsed_args.uuid,
                                   resource_class=parsed_args.resource_class)
        resource = http.request('PUT', url, json=payload).json()
        return FIELDS, utils.get_dict_properties(resource, FIELDS)


class DeleteInventory(command.Command, version.CheckerMixin):

    """Delete the inventory.

    Depending on the resource class argument presence, it can
    delete all inventory for a given resource provider or for a resource
    provider/class pair.

    Delete all inventories for given resource provider
    requires at least ``--os-placement-api-version 1.5``.
    """

    def get_parser(self, prog_name):
        parser = super(DeleteInventory, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )
        parser.add_argument(
            '--resource-class',
            metavar='<resource_class>',
            required=self.compare_version(version.lt('1.5')),
            help=(RC_HELP +
                  '\nThis argument can be omitted starting with '
                  '``--os-placement-api-version 1.5``. If it is omitted all '
                  'inventories of the specified resource provider '
                  'will be deleted.')
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement
        url = BASE_URL
        params = {'uuid': parsed_args.uuid}
        if parsed_args.resource_class is not None:
            url = PER_CLASS_URL
            params = {'uuid': parsed_args.uuid,
                      'resource_class': parsed_args.resource_class}

        http.request('DELETE', url.format(**params))


class ShowInventory(command.ShowOne):

    """Show the inventory for a given resource provider/class pair."""

    def get_parser(self, prog_name):
        parser = super(ShowInventory, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )
        parser.add_argument(
            'resource_class',
            metavar='<resource_class>',
            help=RC_HELP
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = PER_CLASS_URL.format(uuid=parsed_args.uuid,
                                   resource_class=parsed_args.resource_class)
        resource = http.request('GET', url).json()
        return FIELDS, utils.get_dict_properties(resource, FIELDS)


class ListInventory(command.Lister):

    """List inventories for a given resource provider."""

    def get_parser(self, prog_name):
        parser = super(ListInventory, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL.format(uuid=parsed_args.uuid)
        resources = http.request('GET', url).json()

        inventories = [
            dict(resource_class=k, **v)
            for k, v in resources['inventories'].items()
        ]

        fields = ('resource_class', ) + FIELDS
        rows = (utils.get_dict_properties(i, fields) for i in inventories)
        return fields, rows
