# Copyright 2011 OpenStack Foundation
# Copyright 2014 Mirantis, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Command-line interface to the OpenStack Manila API.
"""

from __future__ import print_function

import argparse
import glob
import imp
import itertools
import logging
import os
import pkgutil
import sys

from oslo_utils import encodeutils
import six

from manilaclient import api_versions
from manilaclient import client
from manilaclient.common import cliutils
from manilaclient.common import constants
from manilaclient import exceptions as exc
import manilaclient.extension
from manilaclient.v2 import shell as shell_v2

DEFAULT_OS_SHARE_API_VERSION = api_versions.MAX_VERSION
DEFAULT_MANILA_ENDPOINT_TYPE = 'publicURL'
DEFAULT_MAJOR_OS_SHARE_API_VERSION = "2"
V1_MAJOR_VERSION = '1'
V2_MAJOR_VERSION = '2'


logger = logging.getLogger(__name__)


class AllowOnlyOneAliasAtATimeAction(argparse.Action):
    """Allows only one alias of argument to be used at a time."""

    def __call__(self, parser, namespace, values, option_string=None):
        # NOTE(vponomaryov): this method is redefinition of
        # argparse.Action.__call__ interface

        if not hasattr(self, 'calls'):
            self.calls = {}

        if self.dest not in self.calls:
            self.calls[self.dest] = set()

        local_values = sorted(values) if isinstance(values, list) else values
        self.calls[self.dest].add(six.text_type(local_values))

        if len(self.calls[self.dest]) == 1:
            setattr(namespace, self.dest, local_values)
        else:
            msg = "Only one alias is allowed at a time."
            raise argparse.ArgumentError(self, msg)


class ManilaClientArgumentParser(argparse.ArgumentParser):

    def __init__(self, *args, **kwargs):
        super(ManilaClientArgumentParser, self).__init__(*args, **kwargs)
        # NOTE(vponomaryov): Register additional action to be used by arguments
        # with multiple aliases.
        self.register('action', 'single_alias', AllowOnlyOneAliasAtATimeAction)

    def error(self, message):
        """error(message: string)

        Prints a usage message incorporating the message to stderr and
        exits.
        """
        self.print_usage(sys.stderr)
        # FIXME(lzyeval): if changes occur in argparse.ArgParser._check_value
        choose_from = ' (choose from'
        progparts = self.prog.partition(' ')
        self.exit(2, "error: %(errmsg)s\nTry '%(mainp)s help %(subp)s'"
                     " for more information.\n" %
                     {'errmsg': message.split(choose_from)[0],
                      'mainp': progparts[0],
                      'subp': progparts[2]})

    def _get_option_tuples(self, option_string):
        """Avoid ambiguity in argument abbreviation.

        Manilaclient uses aliases for command parameters and this method
        is used for avoiding parameter ambiguity alert.
        """
        option_tuples = super(
            ManilaClientArgumentParser, self)._get_option_tuples(option_string)
        if len(option_tuples) > 1:
            opt_strings_list = []
            opts = []
            for opt in option_tuples:
                if opt[0].option_strings not in opt_strings_list:
                    opt_strings_list.append(opt[0].option_strings)
                    opts.append(opt)
            return opts
        return option_tuples


class OpenStackManilaShell(object):

    def get_base_parser(self):
        parser = ManilaClientArgumentParser(
            prog='manila',
            description=__doc__.strip(),
            epilog='See "manila help COMMAND" '
                   'for help on a specific command.',
            add_help=False,
            formatter_class=OpenStackHelpFormatter,
        )

        # Global arguments
        parser.add_argument('-h', '--help',
                            action='store_true',
                            help=argparse.SUPPRESS)

        parser.add_argument('--version',
                            action='version',
                            version=manilaclient.__version__)

        parser.add_argument('-d', '--debug',
                            action='store_true',
                            default=cliutils.env('manilaclient_DEBUG',
                                                 'MANILACLIENT_DEBUG',
                                                 default=False),
                            help="Print debugging output.")

        parser.add_argument('--os-cache',
                            default=cliutils.env('OS_CACHE', default=False),
                            action='store_true',
                            help='Use the auth token cache. '
                                 'Defaults to env[OS_CACHE].')

        parser.add_argument('--os-reset-cache',
                            default=False,
                            action='store_true',
                            help='Delete cached password and auth token.')

        parser.add_argument('--os-user-id',
                            metavar='<auth-user-id>',
                            default=cliutils.env('OS_USER_ID'),
                            help=('Defaults to env [OS_USER_ID].'))
        parser.add_argument('--os_user_id',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-username',
                            metavar='<auth-user-name>',
                            default=cliutils.env('OS_USERNAME',
                                                 'MANILA_USERNAME'),
                            help='Defaults to env[OS_USERNAME].')
        parser.add_argument('--os_username',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-password',
                            metavar='<auth-password>',
                            default=cliutils.env('OS_PASSWORD',
                                                 'MANILA_PASSWORD'),
                            help='Defaults to env[OS_PASSWORD].')
        parser.add_argument('--os_password',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-tenant-name',
                            metavar='<auth-tenant-name>',
                            default=cliutils.env('OS_TENANT_NAME',
                                                 'MANILA_PROJECT_ID'),
                            help='Defaults to env[OS_TENANT_NAME].')
        parser.add_argument('--os_tenant_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-project-name',
                            metavar='<auth-project-name>',
                            default=cliutils.env('OS_PROJECT_NAME'),
                            help=('Another way to specify tenant name. '
                                  'This option is mutually exclusive with '
                                  '--os-tenant-name. '
                                  'Defaults to env[OS_PROJECT_NAME].'))
        parser.add_argument('--os_project_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-tenant-id',
                            metavar='<auth-tenant-id>',
                            default=cliutils.env('OS_TENANT_ID',
                                                 'MANILA_TENANT_ID'),
                            help='Defaults to env[OS_TENANT_ID].')
        parser.add_argument('--os_tenant_id',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-project-id',
                            metavar='<auth-project-id>',
                            default=cliutils.env('OS_PROJECT_ID'),
                            help=('Another way to specify tenant ID. '
                                  'This option is mutually exclusive with '
                                  '--os-tenant-id. '
                                  'Defaults to env[OS_PROJECT_ID].'))
        parser.add_argument('--os_project_id',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-user-domain-id',
                            metavar='<auth-user-domain-id>',
                            default=cliutils.env('OS_USER_DOMAIN_ID'),
                            help=('OpenStack user domain ID. '
                                  'Defaults to env[OS_USER_DOMAIN_ID].'))
        parser.add_argument('--os_user_domain_id',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-user-domain-name',
                            metavar='<auth-user-domain-name>',
                            default=cliutils.env('OS_USER_DOMAIN_NAME'),
                            help=('OpenStack user domain name. '
                                  'Defaults to env[OS_USER_DOMAIN_NAME].'))
        parser.add_argument('--os_user_domain_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-project-domain-id',
                            metavar='<auth-project-domain-id>',
                            default=cliutils.env('OS_PROJECT_DOMAIN_ID'),
                            help='Defaults to env[OS_PROJECT_DOMAIN_ID].')
        parser.add_argument('--os_project_domain_id',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-project-domain-name',
                            metavar='<auth-project-domain-name>',
                            default=cliutils.env('OS_PROJECT_DOMAIN_NAME'),
                            help='Defaults to env[OS_PROJECT_DOMAIN_NAME].')
        parser.add_argument('--os_project_domain_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-auth-url',
                            metavar='<auth-url>',
                            default=cliutils.env('OS_AUTH_URL',
                                                 'MANILA_URL'),
                            help='Defaults to env[OS_AUTH_URL].')
        parser.add_argument('--os_auth_url',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-region-name',
                            metavar='<region-name>',
                            default=cliutils.env('OS_REGION_NAME',
                                                 'MANILA_REGION_NAME'),
                            help='Defaults to env[OS_REGION_NAME].')
        parser.add_argument('--os_region_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-token',
                            metavar='<token>',
                            default=cliutils.env('OS_TOKEN'),
                            help='Defaults to env[OS_TOKEN].')
        parser.add_argument('--os_token',
                            help=argparse.SUPPRESS)

        parser.add_argument('--bypass-url',
                            metavar='<bypass-url>',
                            default=cliutils.env('OS_MANILA_BYPASS_URL',
                                                 'MANILACLIENT_BYPASS_URL'),
                            help=("Use this API endpoint instead of the "
                                  "Service Catalog. Defaults to "
                                  "env[OS_MANILA_BYPASS_URL]."))
        parser.add_argument('--bypass_url',
                            help=argparse.SUPPRESS)

        parser.add_argument('--service-type',
                            metavar='<service-type>',
                            help='Defaults to compute for most actions.')
        parser.add_argument('--service_type',
                            help=argparse.SUPPRESS)

        parser.add_argument('--service-name',
                            metavar='<service-name>',
                            default=cliutils.env('OS_MANILA_SERVICE_NAME',
                                                 'MANILA_SERVICE_NAME'),
                            help='Defaults to env[OS_MANILA_SERVICE_NAME].')
        parser.add_argument('--service_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--share-service-name',
                            metavar='<share-service-name>',
                            default=cliutils.env(
                                    'OS_MANILA_SHARE_SERVICE_NAME',
                                    'MANILA_share_service_name'),
                            help='Defaults to env'
                                 '[OS_MANILA_SHARE_SERVICE_NAME].')
        parser.add_argument('--share_service_name',
                            help=argparse.SUPPRESS)

        parser.add_argument('--endpoint-type',
                            metavar='<endpoint-type>',
                            default=cliutils.env(
                                'OS_MANILA_ENDPOINT_TYPE',
                                'MANILA_ENDPOINT_TYPE',
                                default=DEFAULT_MANILA_ENDPOINT_TYPE),
                            help='Defaults to env[OS_MANILA_ENDPOINT_TYPE] or '
                            + DEFAULT_MANILA_ENDPOINT_TYPE + '.')
        parser.add_argument('--endpoint_type',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-share-api-version',
                            metavar='<share-api-ver>',
                            default=cliutils.env(
                                'OS_SHARE_API_VERSION',
                                default=DEFAULT_OS_SHARE_API_VERSION),
                            help='Accepts 1.x to override default '
                                 'to env[OS_SHARE_API_VERSION].')
        parser.add_argument('--os_share_api_version',
                            help=argparse.SUPPRESS)

        parser.add_argument('--os-cacert',
                            metavar='<ca-certificate>',
                            default=cliutils.env('OS_CACERT', default=None),
                            help='Specify a CA bundle file to use in '
                            'verifying a TLS (https) server certificate. '
                            'Defaults to env[OS_CACERT].')

        parser.add_argument('--insecure',
                            default=cliutils.env('manilaclient_INSECURE',
                                                 'MANILACLIENT_INSECURE',
                                                 default=False),
                            action='store_true',
                            help=argparse.SUPPRESS)

        parser.add_argument('--retries',
                            metavar='<retries>',
                            type=int,
                            default=0,
                            help='Number of retries.')

        parser.add_argument('--os-cert',
                            metavar='<certificate>',
                            default=cliutils.env('OS_CERT'),
                            help='Defaults to env[OS_CERT].')
        parser.add_argument('--os_cert',
                            help=argparse.SUPPRESS)

        return parser

    def get_subcommand_parser(self, version):
        parser = self.get_base_parser()

        self.subcommands = {}
        subparsers = parser.add_subparsers(metavar='<subcommand>')

        try:
            actions_module = {
                V2_MAJOR_VERSION: shell_v2,
            }[version]
        except KeyError:
            actions_module = shell_v2

        self._find_actions(subparsers, actions_module)
        self._find_actions(subparsers, self)

        for extension in self.extensions:
            self._find_actions(subparsers, extension.module)

        self._add_bash_completion_subparser(subparsers)

        return parser

    def _discover_extensions(self, api_version):
        extensions = []
        for name, module in itertools.chain(
                self._discover_via_python_path(),
                self._discover_via_contrib_path(api_version)):

            extension = manilaclient.extension.Extension(name, module)
            extensions.append(extension)

        return extensions

    def _discover_via_python_path(self):
        for (module_loader, name, ispkg) in pkgutil.iter_modules():
            if name.endswith('python_manilaclient_ext'):
                if not hasattr(module_loader, 'load_module'):
                    # Python 2.6 compat: actually get an ImpImporter obj
                    module_loader = module_loader.find_module(name)

                module = module_loader.load_module(name)
                yield name, module

    def _discover_via_contrib_path(self, api_version):
        module_path = os.path.dirname(os.path.abspath(__file__))
        version_str = 'v' + api_version.get_major_version()
        ext_path = os.path.join(module_path, version_str, 'contrib')
        ext_glob = os.path.join(ext_path, "*.py")

        for ext_path in glob.iglob(ext_glob):
            name = os.path.basename(ext_path)[:-3]

            if name == "__init__":
                continue

            module = imp.load_source(name, ext_path)
            yield name, module

    def _add_bash_completion_subparser(self, subparsers):
        subparser = subparsers.add_parser(
            'bash_completion',
            add_help=False,
            formatter_class=OpenStackHelpFormatter)

        self.subcommands['bash_completion'] = subparser
        subparser.set_defaults(func=self.do_bash_completion)

    def _find_actions(self, subparsers, actions_module):
        for attr in (a for a in dir(actions_module) if a.startswith('do_')):
            # I prefer to be hypen-separated instead of underscores.
            command = attr[3:].replace('_', '-')
            callback = getattr(actions_module, attr)
            desc = callback.__doc__ or ''
            help = desc.strip()
            arguments = getattr(callback, 'arguments', [])

            subparser = subparsers.add_parser(
                command,
                help=help,
                description=desc,
                add_help=False,
                formatter_class=OpenStackHelpFormatter)

            subparser.add_argument('-h', '--help',
                                   action='help',
                                   help=argparse.SUPPRESS,)

            self.subcommands[command] = subparser
            for (args, kwargs) in arguments:
                subparser.add_argument(*args, **kwargs)
            subparser.set_defaults(func=callback)

    def setup_debugging(self, debug):
        if not debug:
            return

        streamformat = "%(levelname)s (%(module)s:%(lineno)d) %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=streamformat)
        logging.getLogger('requests.packages.urllib3.connectionpool'
                          ).setLevel(logging.WARNING)
        logging.getLogger('keystoneauth1.session').setLevel(logging.WARNING)

    def _build_subcommands_and_extensions(self,
                                          os_api_version,
                                          argv,
                                          options):

        self.extensions = self._discover_extensions(os_api_version)
        self._run_extension_hooks('__pre_parse_args__')

        self.parser = self.get_subcommand_parser(
            os_api_version.get_major_version())

        if argv and len(argv) > 1 and '--help' in argv:
            argv = [x for x in argv if x != '--help']
            if argv[0] in self.subcommands:
                self.subcommands[argv[0]].print_help()
                return False

        if options.help or not argv:
            self.parser.print_help()
            return False

        args = self.parser.parse_args(argv)
        self._run_extension_hooks('__post_parse_args__', args)

        return args

    def main(self, argv):
        # Parse args once to find version and debug settings
        parser = self.get_base_parser()
        (options, args) = parser.parse_known_args(argv)
        self.setup_debugging(options.debug)

        os_api_version = self._validate_input_api_version(options)

        # build available subcommands based on version
        args = self._build_subcommands_and_extensions(os_api_version,
                                                      argv,
                                                      options)
        if not args:
            return 0

        # Short-circuit and deal with help right away.
        if args.func == self.do_help:
            self.do_help(args)
            return 0
        elif args.func == self.do_bash_completion:
            self.do_bash_completion(args)
            return 0

        if not options.os_share_api_version:
            api_version = api_versions.get_api_version(
                DEFAULT_MAJOR_OS_SHARE_API_VERSION)
        else:
            api_version = api_versions.get_api_version(
                options.os_share_api_version)

        major_version_string = six.text_type(api_version.ver_major)
        os_service_type = args.service_type
        if not os_service_type:
            os_service_type = constants.SERVICE_TYPES[major_version_string]

        os_endpoint_type = args.endpoint_type or DEFAULT_MANILA_ENDPOINT_TYPE

        client_args = dict(
            username=args.os_username,
            password=args.os_password,
            project_name=args.os_project_name or args.os_tenant_name,
            auth_url=args.os_auth_url,
            insecure=args.insecure,
            region_name=args.os_region_name,
            tenant_id=args.os_project_id or args.os_tenant_id,
            endpoint_type=os_endpoint_type,
            extensions=self.extensions,
            service_type=os_service_type,
            service_name=args.service_name,
            retries=options.retries,
            http_log_debug=args.debug,
            cacert=args.os_cacert,
            use_keyring=args.os_cache,
            force_new_token=args.os_reset_cache,
            user_id=args.os_user_id,
            user_domain_id=args.os_user_domain_id,
            user_domain_name=args.os_user_domain_name,
            project_domain_id=args.os_project_domain_id,
            project_domain_name=args.os_project_domain_name,
            cert=args.os_cert,
            input_auth_token=args.os_token,
            service_catalog_url=args.bypass_url,
        )

        # Handle deprecated parameters
        if args.share_service_name:
            client_args['share_service_name'] = args.share_service_name

        self._validate_required_options(
            args.os_tenant_name, args.os_tenant_id,
            args.os_project_name, args.os_project_id,
            args.os_token, args.bypass_url,
            client_args['auth_url'])

        # This client is needed to discover the server api version.
        temp_client = client.Client(manilaclient.API_MAX_VERSION,
                                    **client_args)

        self.cs, discovered_version = self._discover_client(temp_client,
                                                            os_api_version,
                                                            os_endpoint_type,
                                                            os_service_type,
                                                            client_args)

        args = self._build_subcommands_and_extensions(discovered_version,
                                                      argv,
                                                      options)

        args.func(self.cs, args)

    def _discover_client(self,
                         current_client,
                         os_api_version,
                         os_endpoint_type,
                         os_service_type,
                         client_args):

        if os_api_version == manilaclient.API_DEPRECATED_VERSION:
            discovered_version = manilaclient.API_DEPRECATED_VERSION
            os_service_type = constants.V1_SERVICE_TYPE
        else:
            discovered_version = api_versions.discover_version(
                current_client,
                os_api_version
            )

        if not os_endpoint_type:
            os_endpoint_type = DEFAULT_MANILA_ENDPOINT_TYPE

        if not os_service_type:
            os_service_type = self._discover_service_type(discovered_version)

        if (discovered_version != manilaclient.API_MAX_VERSION or
                os_service_type != constants.V1_SERVICE_TYPE or
                os_endpoint_type != DEFAULT_MANILA_ENDPOINT_TYPE):
            client_args['version'] = discovered_version
            client_args['service_type'] = os_service_type
            client_args['endpoint_type'] = os_endpoint_type

            return (client.Client(discovered_version, **client_args),
                    discovered_version)
        else:
            return current_client, discovered_version

    def _discover_service_type(self, discovered_version):
        major_version = discovered_version.get_major_version()
        service_type = constants.SERVICE_TYPES[major_version]
        return service_type

    def _validate_input_api_version(self, options):
        if not options.os_share_api_version:
            api_version = manilaclient.API_MAX_VERSION
        else:
            api_version = api_versions.get_api_version(
                options.os_share_api_version)
        return api_version

    def _validate_required_options(self, tenant_name, tenant_id,
                                   project_name, project_id,
                                   token, service_catalog_url, auth_url):
        if token and not service_catalog_url:
            raise exc.CommandError(
                "bypass_url missing: When specifying a token the bypass_url "
                "must be set via --bypass-url or env[OS_MANILA_BYPASS_URL]")
        if service_catalog_url and not token:
            raise exc.CommandError(
                "Token missing: When specifying a bypass_url a token must be "
                "set via --os-token or env[OS_TOKEN]")
        if token and service_catalog_url:
            return

        if not (tenant_name or tenant_id or project_name or project_id):
            raise exc.CommandError(
                "You must provide a tenant_name, tenant_id, "
                "project_id or project_name (with "
                "project_domain_name or project_domain_id) via "
                "--os-tenant-name or env[OS_TENANT_NAME], "
                "--os-tenant-id or env[OS_TENANT_ID], "
                "--os-project-id or env[OS_PROJECT_ID], "
                "--os-project-name or env[OS_PROJECT_NAME], "
                "--os-project-domain-id or env[OS_PROJECT_DOMAIN_ID] and "
                "--os-project-domain-name or env[OS_PROJECT_DOMAIN_NAME]."
            )

        if not auth_url:
            raise exc.CommandError(
                "You must provide an auth url "
                "via either --os-auth-url or env[OS_AUTH_URL]")

    def _run_extension_hooks(self, hook_type, *args, **kwargs):
        """Run hooks for all registered extensions."""
        for extension in self.extensions:
            extension.run_hooks(hook_type, *args, **kwargs)

    def do_bash_completion(self, args):
        """Print arguments for bash_completion.

        Prints all of the commands and options to stdout so that the
        manila.bash_completion script doesn't have to hard code them.
        """
        commands = set()
        options = set()
        for sc_str, sc in list(self.subcommands.items()):
            commands.add(sc_str)
            for option in sc._optionals._option_string_actions:
                options.add(option)

        commands.remove('bash-completion')
        commands.remove('bash_completion')
        print(' '.join(commands | options))

    @cliutils.arg('command', metavar='<subcommand>', nargs='?',
                  help='Display help for <subcommand>')
    def do_help(self, args):
        """Display help about this program or one of its subcommands."""
        if args.command:
            if args.command in self.subcommands:
                self.subcommands[args.command].print_help()
            else:
                raise exc.CommandError("'%s' is not a valid subcommand" %
                                       args.command)
        else:
            self.parser.print_help()


# I'm picky about my shell help.
class OpenStackHelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        # Title-case the headings
        heading = '%s%s' % (heading[0].upper(), heading[1:])
        super(OpenStackHelpFormatter, self).start_section(heading)


def main():
    try:
        if sys.version_info >= (3, 0):
            OpenStackManilaShell().main(sys.argv[1:])
        else:
            OpenStackManilaShell().main(
                map(encodeutils.safe_decode, sys.argv[1:]))
    except KeyboardInterrupt:
        print("... terminating manila client", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logger.debug(e, exc_info=1)
        print("ERROR: %s" % six.text_type(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
