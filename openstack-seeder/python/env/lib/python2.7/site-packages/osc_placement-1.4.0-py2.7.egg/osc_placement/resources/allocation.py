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

from osc_lib.command import command
from osc_lib import exceptions
from osc_lib import utils

from osc_placement import version


BASE_URL = '/allocations'


def parse_allocations(allocation_strings):
    allocations = {}
    for allocation_string in allocation_strings:
        if '=' not in allocation_string or ',' not in allocation_string:
            raise ValueError('Incorrect allocation string format')
        parsed = dict(kv.split('=') for kv in allocation_string.split(','))
        if 'rp' not in parsed:
            raise ValueError('Resource provider parameter is required '
                             'for allocation string')
        resources = {k: int(v) for k, v in parsed.items() if k != 'rp'}
        if parsed['rp'] not in allocations:
            allocations[parsed['rp']] = resources
        else:
            prev_rp = allocations[parsed['rp']]
            for resource, value in resources.items():
                if resource in prev_rp and prev_rp[resource] != value:
                    raise exceptions.CommandError(
                        'Conflict detected for '
                        'resource provider {} resource class {}'.format(
                            parsed['rp'], resource))
            allocations[parsed['rp']].update(resources)
    return allocations


class SetAllocation(command.Lister, version.CheckerMixin):
    """Replaces the set of resource allocation(s) for a given consumer.

    Note that this is a full replacement of the existing allocations. If you
    want to retain the existing allocations and add a new resource class
    allocation, you must specify all resource class allocations, old and new.

    From ``--os-placement-api-version 1.8`` it is required to specify
    ``--project-id`` and ``--user-id`` to set allocations. It is highly
    recommended to provide a ``--project-id`` and ``--user-id`` when setting
    allocations for accounting and data consistency reasons.

    Starting with ``--os-placement-api-version 1.12`` the API response
    contains the project_id and user_id of allocations which also
    appears in the CLI output.

    """

    def get_parser(self, prog_name):
        parser = super(SetAllocation, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the consumer'
        )
        parser.add_argument(
            '--allocation',
            metavar='<rp=resource-provider-id,'
                    'resource-class-name=amount-of-resource-used>',
            action='append',
            default=[],
            help='Create (or update) an allocation of a resource class. '
                 'Specify option multiple times to set multiple allocations.'
        )
        parser.add_argument(
            '--project-id',
            metavar='project_id',
            help='ID of the consuming project. '
                 'This option is required starting from '
                 '``--os-placement-api-version 1.8``.',
            required=self.compare_version(version.ge('1.8'))
        )
        parser.add_argument(
            '--user-id',
            metavar='user_id',
            help='ID of the consuming user. '
                 'This option is required starting from '
                 '``--os-placement-api-version 1.8``.',
            required=self.compare_version(version.ge('1.8'))
        )
        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        allocations = parse_allocations(parsed_args.allocation)
        if not allocations:
            raise exceptions.CommandError(
                'At least one resource allocation must be specified')

        if self.compare_version(version.ge('1.12')):
            allocations = {
                rp: {'resources': resources}
                for rp, resources in allocations.items()}
        else:
            allocations = [
                {'resource_provider': {'uuid': rp}, 'resources': resources}
                for rp, resources in allocations.items()]

        url = BASE_URL + '/' + parsed_args.uuid
        payload = {'allocations': allocations}
        if self.compare_version(version.ge('1.8')):
            payload['project_id'] = parsed_args.project_id
            payload['user_id'] = parsed_args.user_id
        elif parsed_args.project_id or parsed_args.user_id:
            self.log.warning('--project-id and --user-id options do not '
                             'affect allocation for '
                             '--os-placement-api-version less than 1.8')
        http.request('PUT', url, json=payload)
        resp = http.request('GET', url).json()
        per_provider = resp['allocations'].items()

        fields = ('resource_provider', 'generation', 'resources')
        allocs = [dict(resource_provider=k, **v) for k, v in per_provider]
        if self.compare_version(version.ge('1.12')):
            fields += ('project_id', 'user_id')
            [alloc.update(project_id=resp['project_id'],
                          user_id=resp['user_id'])
             for alloc in allocs]

        rows = (utils.get_dict_properties(a, fields) for a in allocs)
        return fields, rows


class ShowAllocation(command.Lister, version.CheckerMixin):
    """Show resource allocations for a given consumer.

    Starting with ``--os-placement-api-version 1.12`` the API response contains
    the project_id and user_id of allocations which also appears in the CLI
    output.

    """

    def get_parser(self, prog_name):
        parser = super(ShowAllocation, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the consumer'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        resp = http.request('GET', url).json()
        per_provider = resp['allocations'].items()
        if self.compare_version(version.ge('1.12')):
            allocs = [dict(
                resource_provider=k,
                project_id=resp['project_id'],
                user_id=resp['user_id'],
                **v) for k, v in per_provider]
        else:
            allocs = [dict(resource_provider=k, **v) for k, v in per_provider]

        fields = ('resource_provider', 'generation', 'resources')
        if self.compare_version(version.ge('1.12')):
            fields += ('project_id', 'user_id')

        rows = (utils.get_dict_properties(a, fields) for a in allocs)
        return fields, rows


class DeleteAllocation(command.Command):
    """Delete all resource allocations for a given consumer."""

    def get_parser(self, prog_name):
        parser = super(DeleteAllocation, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the consumer'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.uuid
        http.request('DELETE', url)
