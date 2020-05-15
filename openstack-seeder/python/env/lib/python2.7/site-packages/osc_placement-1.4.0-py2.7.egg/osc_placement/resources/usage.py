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
from osc_lib import utils

from osc_placement import version


BASE_URL = '/resource_providers/{uuid}/usages'
USAGES_URL = '/usages'
FIELDS = ('resource_class', 'usage')


class ResourceShowUsage(command.Lister, version.CheckerMixin):
    """Show resource usages for a project (and optionally user) per class.

    Gives a report of usage information for resources associated with the
    project identified by the ``project_id`` argument and user identified by
    the ``--user-id`` option.

    This command requires at least ``--os-placement-api-version 1.9``.

    """

    def get_parser(self, prog_name):
        parser = super(ResourceShowUsage, self).get_parser(prog_name)

        parser.add_argument(
            'project_id',
            metavar='<project-uuid>',
            help='ID of the project.'
        )
        parser.add_argument(
            '--user-id',
            metavar='<user-uuid>',
            help='ID of the user.'
        )

        return parser

    @version.check(version.ge('1.9'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = USAGES_URL
        params = {'project_id': parsed_args.project_id}
        if parsed_args.user_id:
            params['user_id'] = parsed_args.user_id
        per_class = http.request(
            'GET', url, params=params).json()['usages']

        usages = [{'resource_class': k, 'usage': v}
                  for k, v in per_class.items()]
        rows = (utils.get_dict_properties(u, FIELDS) for u in usages)
        return FIELDS, rows


class ShowUsage(command.Lister):
    """Show resource usages per class for a given resource provider."""

    def get_parser(self, prog_name):
        parser = super(ShowUsage, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider'
        )

        return parser

    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL.format(uuid=parsed_args.uuid)
        per_class = http.request('GET', url).json()['usages']

        usages = [{'resource_class': k, 'usage': v}
                  for k, v in per_class.items()]
        rows = (utils.get_dict_properties(u, FIELDS) for u in usages)
        return FIELDS, rows
