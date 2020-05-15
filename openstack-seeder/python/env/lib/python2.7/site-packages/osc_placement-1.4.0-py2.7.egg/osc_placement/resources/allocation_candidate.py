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

from osc_placement import version


BASE_URL = '/allocation_candidates'


class ListAllocationCandidate(command.Lister, version.CheckerMixin):

    """List allocation candidates.

    Returns a representation of a collection of allocation requests and
    resource provider summaries. Each allocation request has information
    to issue an "openstack resource provider allocation set" request to claim
    resources against a related set of resource providers.

    As several allocation requests are available its necessary to select one.
    To make a decision, resource provider summaries are provided with the
    inventory/capacity information.

    For example::

      $ export OS_PLACEMENT_API_VERSION=1.10
      $ openstack allocation candidate list --resource VCPU=1
      +---+------------+-------------------------+-------------------------+
      | # | allocation | resource provider       | inventory used/capacity |
      +---+------------+-------------------------+-------------------------+
      | 1 | VCPU=1     | 66bcaca9-9263-45b1-a569 | VCPU=0/128              |
      |   |            | -ea708ff7a968           |                         |
      +---+------------+-------------------------+-------------------------+

    In this case, the user is looking for resource providers that can have
    capacity to allocate 1 VCPU resource class. There is one resource provider
    that can serve that allocation request and that resource providers current
    VCPU inventory used is 0 and available capacity is 128.

    This command requires at least ``--os-placement-api-version 1.10``.
    """

    def get_parser(self, prog_name):
        parser = super(ListAllocationCandidate, self).get_parser(prog_name)

        parser.add_argument(
            '--resource',
            metavar='<resource_class>=<value>',
            dest='resources',
            action='append',
            default=[],
            help='String indicating an amount of resource of a specified '
                 'class that providers in each allocation request must '
                 'collectively have the capacity and availability to serve. '
                 'Can be specified multiple times per resource class. '
                 'For example: '
                 '``--resource VCP=4 --resource DISK_GB=64 '
                 '--resource MEMORY_MB=2048``'
        )
        parser.add_argument(
            '--limit',
            metavar='<limit>',
            help='A positive integer to limit '
                 'the maximum number of allocation candidates. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.16``.'
        )
        parser.add_argument(
            '--required',
            metavar='<required>',
            action='append',
            default=[],
            help='A required trait. May be repeated. Allocation candidates '
                 'must collectively contain all of the required traits. '
                 'This option requires at least '
                 '``--os-placement-api-version 1.17``.'
        )

        return parser

    @version.check(version.ge('1.10'))
    def take_action(self, parsed_args):
        if not parsed_args.resources:
            raise exceptions.CommandError(
                'At least one --resource must be specified.')

        for resource in parsed_args.resources:
            if not len(resource.split('=')) == 2:
                raise exceptions.CommandError(
                    'Arguments to --resource must be of form '
                    '<resource_class>=<value>')

        http = self.app.client_manager.placement

        params = {'resources': ','.join(
            resource.replace('=', ':') for resource in parsed_args.resources)}
        if 'limit' in parsed_args and parsed_args.limit:
            # Fail if --limit but not high enough microversion.
            self.check_version(version.ge('1.16'))
            params['limit'] = int(parsed_args.limit)
        if 'required' in parsed_args and parsed_args.required:
            # Fail if --required but not high enough microversion.
            self.check_version(version.ge('1.17'))
            params['required'] = ','.join(parsed_args.required)
        resp = http.request('GET', BASE_URL, params=params).json()

        rp_resources = {}
        include_traits = self.compare_version(version.ge('1.17'))
        if include_traits:
            rp_traits = {}
        for rp_uuid, resources in resp['provider_summaries'].items():
            rp_resources[rp_uuid] = ','.join(
                '%s=%s/%s' % (rc, value['used'], value['capacity'])
                for rc, value in resources['resources'].items())
            if include_traits:
                rp_traits[rp_uuid] = ','.join(resources['traits'])

        rows = []
        if self.compare_version(version.ge('1.12')):
            for i, allocation_req in enumerate(resp['allocation_requests']):
                for rp, resources in allocation_req['allocations'].items():
                    req = ','.join(
                        '%s=%s' % (rc, value)
                        for rc, value in resources['resources'].items())
                    if include_traits:
                        row = [i + 1, req, rp, rp_resources[rp], rp_traits[rp]]
                    else:
                        row = [i + 1, req, rp, rp_resources[rp]]
                    rows.append(row)
        else:
            for i, allocation_req in enumerate(resp['allocation_requests']):
                for allocation in allocation_req['allocations']:
                    rp = allocation['resource_provider']['uuid']
                    req = ','.join(
                        '%s=%s' % (rc, value)
                        for rc, value in allocation['resources'].items())
                    rows.append([i + 1, req, rp, rp_resources[rp]])

        fields = ('#', 'allocation', 'resource provider',
                  'inventory used/capacity')
        if include_traits:
            fields += ('traits',)

        return fields, rows
