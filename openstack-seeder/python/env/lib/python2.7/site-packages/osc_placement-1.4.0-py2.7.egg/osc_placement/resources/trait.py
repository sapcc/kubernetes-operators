# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may obtain
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

from osc_placement import version


BASE_URL = '/traits'
RP_BASE_URL = '/resource_providers/{uuid}'
RP_TRAITS_URL = '/resource_providers/{uuid}/traits'
FIELDS = ('name',)


class ListTrait(command.Lister):

    """Return a list of valid trait strings.

    This command requires at least ``--os-placement-api-version 1.6``.
    """

    def get_parser(self, prog_name):
        parser = super(ListTrait, self).get_parser(prog_name)

        parser.add_argument(
            '--name',
            metavar='<name>',
            help=('A string to filter traits. The following options '
                  'are available: startswith operator filters the '
                  'traits whose name begins with a specific prefix, '
                  'e.g. name=startswith:CUSTOM, in operator filters '
                  'the traits whose name is in the specified list, '
                  'e.g. name=in:HW_CPU_X86_AVX,HW_CPU_X86_SSE, '
                  'HW_CPU_X86_INVALID_FEATURE.')
        )

        parser.add_argument(
            '--associated',
            action='store_true',
            help=('If this parameter is presented, the returned '
                  'traits will be those that are associated with at '
                  'least one resource provider.')
        )

        return parser

    @version.check(version.ge('1.6'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = BASE_URL
        params = {}
        if parsed_args.name:
            params['name'] = parsed_args.name
        if parsed_args.associated:
            params['associated'] = parsed_args.associated
        traits = http.request('GET', url, params=params).json()['traits']
        return FIELDS, [[t] for t in traits]


class ShowTrait(command.ShowOne):

    """Check if a trait name exists in this cloud.

    This command requires at least ``--os-placement-api-version 1.6``.
    """

    def get_parser(self, prog_name):
        parser = super(ShowTrait, self).get_parser(prog_name)

        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the trait.'
        )

        return parser

    @version.check(version.ge('1.6'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = '/'.join([BASE_URL, parsed_args.name])

        http.request('GET', url)
        return FIELDS, [parsed_args.name]


class CreateTrait(command.Command):

    """Create a new custom trait.

    Custom traits must begin with the prefix "CUSTOM_" and contain only the
    letters A through Z, the numbers 0 through 9 and the underscore "_"
    character.

    This command requires at least ``--os-placement-api-version 1.6``.
    """

    def get_parser(self, prog_name):
        parser = super(CreateTrait, self).get_parser(prog_name)

        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the trait.'
        )

        return parser

    @version.check(version.ge('1.6'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = '/'.join([BASE_URL, parsed_args.name])
        http.request('PUT', url)


class DeleteTrait(command.Command):

    """Delete the trait specified by {name}.

    This command requires at least ``--os-placement-api-version 1.6``.
    """

    def get_parser(self, prog_name):
        parser = super(DeleteTrait, self).get_parser(prog_name)

        parser.add_argument(
            'name',
            metavar='<name>',
            help='Name of the trait.'
        )

        return parser

    @version.check(version.ge('1.6'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = '/'.join([BASE_URL, parsed_args.name])

        http.request('DELETE', url)


class ListResourceProviderTrait(command.Lister):

    """List traits associated with the resource provider identified by {uuid}.

    This command requires at least ``--os-placement-api-version 1.6``.
    """

    def get_parser(self, prog_name):
        parser = super(ListResourceProviderTrait, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider.'
        )

        return parser

    @version.check(version.ge('1.6'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = RP_TRAITS_URL.format(uuid=parsed_args.uuid)
        traits = http.request('GET', url).json()['traits']
        return FIELDS, [[t] for t in traits]


class SetResourceProviderTrait(command.Lister):

    """Associate traits with the resource provider identified by {uuid}.

    All the associated traits will be replaced by the traits specified.

    This command requires at least ``--os-placement-api-version 1.6``.
    """

    def get_parser(self, prog_name):
        parser = super(SetResourceProviderTrait, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider.'
        )

        parser.add_argument(
            '--trait',
            metavar='<trait>',
            help='Name of the trait. May be repeated.',
            default=[],
            action='append'
        )

        return parser

    @version.check(version.ge('1.6'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = RP_BASE_URL.format(uuid=parsed_args.uuid)
        rp = http.request('GET', url).json()
        url = RP_TRAITS_URL.format(uuid=parsed_args.uuid)
        payload = {
            'resource_provider_generation': rp['generation'],
            'traits': parsed_args.trait
        }
        traits = http.request('PUT', url, json=payload).json()['traits']
        return FIELDS, [[t] for t in traits]


class DeleteResourceProviderTrait(command.Command):

    """Dissociate all the traits from the resource provider.

    Note that this command is not atomic if multiple processes are managing
    traits for the same provider.

    This command requires at least ``--os-placement-api-version 1.6``.
    """

    def get_parser(self, prog_name):
        parser = super(DeleteResourceProviderTrait, self).get_parser(prog_name)

        parser.add_argument(
            'uuid',
            metavar='<uuid>',
            help='UUID of the resource provider.'
        )

        return parser

    @version.check(version.ge('1.6'))
    def take_action(self, parsed_args):
        http = self.app.client_manager.placement

        url = RP_TRAITS_URL.format(uuid=parsed_args.uuid)
        http.request('DELETE', url)
