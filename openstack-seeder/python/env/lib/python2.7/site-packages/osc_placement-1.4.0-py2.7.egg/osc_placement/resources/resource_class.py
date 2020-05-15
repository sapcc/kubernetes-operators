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


BASE_URL = '/resource_classes'
PER_CLASS_URL = BASE_URL + '/{name}'
FIELDS = ('name',)


class ListResourceClass(command.Lister):

    """Return a list of all resource classes.

    This command requires at least --os-placement-api-version 1.2.
    """

    def get_parser(self, prog_name):
        parser = super(ListResourceClass, self).get_parser(prog_name)

        return parser

    @version.check(version.ge('1.2'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        resource_classes = http.request(
            'GET', BASE_URL).json()['resource_classes']
        rows = (utils.get_dict_properties(i, FIELDS) for i in resource_classes)
        return FIELDS, rows


class CreateResourceClass(command.Command):

    """Create a new resource class.

    This command requires at least --os-placement-api-version 1.2.
    """

    def get_parser(self, prog_name):
        parser = super(CreateResourceClass, self).get_parser(prog_name)

        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the resource class'
        )
        return parser

    @version.check(version.ge('1.2'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        http.request('POST', BASE_URL, json={'name': parsed_args.name})


class SetResourceClass(command.Command):

    """Create or validate the existence of single resource class.

    Unlike "resource class create" also succeed if the resource class
    already exists, which makes this an idempotent check or create command.

    This command requires at least ``--os-placement-api-version 1.7``.
    """

    def get_parser(self, prog_name):
        parser = super(SetResourceClass, self).get_parser(prog_name)

        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the resource class'
        )
        return parser

    @version.check(version.ge('1.7'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL + '/' + parsed_args.name

        http.request('PUT', url)


class ShowResourceClass(command.ShowOne):

    """Return a representation of the resource class identified by {name}.

    This command requires at least --os-placement-api-version 1.2.
    """

    def get_parser(self, prog_name):
        parser = super(ShowResourceClass, self).get_parser(prog_name)

        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the resource class'
        )

        return parser

    @version.check(version.ge('1.2'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = PER_CLASS_URL.format(name=parsed_args.name)

        resource = http.request('GET', url).json()
        return FIELDS, utils.get_dict_properties(resource, FIELDS)


class DeleteResourceClass(command.Command):

    """Delete the resource class identified by {name}.

    Only custom resource classes can be deleted.

    This command requires at least --os-placement-api-version 1.2.
    """

    def get_parser(self, prog_name):
        parser = super(DeleteResourceClass, self).get_parser(prog_name)

        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the resource class'
        )

        return parser

    @version.check(version.ge('1.2'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = PER_CLASS_URL.format(name=parsed_args.name)

        http.request('DELETE', url)
