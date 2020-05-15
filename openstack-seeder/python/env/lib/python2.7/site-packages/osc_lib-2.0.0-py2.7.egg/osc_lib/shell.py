#   Copyright 2012-2013 OpenStack Foundation
#   Copyright 2015 Dean Troyer
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

"""Command-line interface to the OpenStack APIs"""

import getpass
import locale
import logging
import sys
import traceback

from cliff import app
from cliff import command
from cliff import complete
from cliff import help
from oslo_utils import importutils
from oslo_utils import strutils
import six

from osc_lib.cli import client_config as cloud_config
from osc_lib import clientmanager
from osc_lib.command import commandmanager
from osc_lib.command import timing
from osc_lib import exceptions as exc
from osc_lib.i18n import _
from osc_lib import logs
from osc_lib import utils
from osc_lib import version

osprofiler_profiler = importutils.try_import("osprofiler.profiler")


DEFAULT_DOMAIN = 'default'
DEFAULT_INTERFACE = 'public'


def prompt_for_password(prompt=None):
    """Prompt user for a password

    Prompt for a password if stdin is a tty.
    """

    if not prompt:
        prompt = 'Password: '
    pw = None
    # If stdin is a tty, try prompting for the password
    if hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
        # Check for Ctl-D
        try:
            pw = getpass.getpass(prompt)
        except EOFError:
            pass
    # No password because we did't have a tty or nothing was entered
    if not pw:
        raise exc.CommandError(_("No password entered, or found via"
                                 " --os-password or OS_PASSWORD"),)

    return pw


class OpenStackShell(app.App):

    CONSOLE_MESSAGE_FORMAT = '%(levelname)s: %(name)s %(message)s'

    log = logging.getLogger(__name__)
    timing_data = []

    def __init__(
            self,
            description=None,
            version=None,
            command_manager=None,
            stdin=None,
            stdout=None,
            stderr=None,
            interactive_app_factory=None,
            deferred_help=False,
    ):
        # Patch command.Command to add a default auth_required = True
        command.Command.auth_required = True

        # Some commands do not need authentication
        help.HelpCommand.auth_required = False
        complete.CompleteCommand.auth_required = False

        # Slight change to the meaning of --debug
        self.DEFAULT_DEBUG_VALUE = None
        self.DEFAULT_DEBUG_HELP = 'Set debug logging and traceback on errors.'

        # Do default for positionals
        if not command_manager:
            cm = commandmanager.CommandManager('openstack.cli')
        else:
            cm = command_manager

        super(OpenStackShell, self).__init__(
            description=__doc__.strip(),
            version=version,
            command_manager=cm,
            deferred_help=True,
        )

        # Until we have command line arguments parsed, dump any stack traces
        self.dump_stack_trace = True

        # Set in subclasses
        self.api_version = None

        self.client_manager = None
        self.command_options = None

        self.do_profile = False

    def configure_logging(self):
        """Configure logging for the app."""
        self.log_configurator = logs.LogConfigurator(self.options)
        self.dump_stack_trace = self.log_configurator.dump_trace

    def run(self, argv):
        ret_val = 1
        self.command_options = argv
        try:
            ret_val = super(OpenStackShell, self).run(argv)
            return ret_val
        except Exception as e:
            if not logging.getLogger('').handlers:
                logging.basicConfig()
            if self.dump_stack_trace:
                self.log.error(traceback.format_exc())
            else:
                self.log.error('Exception raised: ' + str(e))

            return ret_val

        finally:
            self.log.info("END return value: %s", ret_val)

    def init_profile(self):
        self.do_profile = osprofiler_profiler and self.options.profile
        if self.do_profile:
            osprofiler_profiler.init(self.options.profile)

    def close_profile(self):
        if self.do_profile:
            profiler = osprofiler_profiler.get()
            trace_id = profiler.get_base_id()
            # Short ID for OpenTracing-based driver (64-bit id)
            short_id = profiler.get_shorten_id(trace_id)

            # NOTE(dbelova): let's use warning log level to see these messages
            # printed. In fact we can define custom log level here with value
            # bigger than most big default one (CRITICAL) or something like
            # that (PROFILE = 60 for instance), but not sure we need it here.
            self.log.warning("Trace ID: %s" % trace_id)
            self.log.warning("Short trace ID "
                             "for OpenTracing-based drivers: %s" % short_id)
            self.log.warning("Display trace data with command:\n"
                             "osprofiler trace show --html %s " % trace_id)

    def run_subcommand(self, argv):
        self.init_profile()
        try:
            ret_value = super(OpenStackShell, self).run_subcommand(argv)
        finally:
            self.close_profile()
        return ret_value

    def interact(self):
        self.init_profile()
        try:
            ret_value = super(OpenStackShell, self).interact()
        finally:
            self.close_profile()
        return ret_value

    def build_option_parser(self, description, version):
        parser = super(OpenStackShell, self).build_option_parser(
            description,
            version)

        # service token auth argument
        parser.add_argument(
            '--os-cloud',
            metavar='<cloud-config-name>',
            dest='cloud',
            default=utils.env('OS_CLOUD'),
            help=_('Cloud name in clouds.yaml (Env: OS_CLOUD)'),
        )
        # Global arguments
        parser.add_argument(
            '--os-region-name',
            metavar='<auth-region-name>',
            dest='region_name',
            default=utils.env('OS_REGION_NAME'),
            help=_('Authentication region name (Env: OS_REGION_NAME)'),
        )
        parser.add_argument(
            '--os-cacert',
            metavar='<ca-bundle-file>',
            dest='cacert',
            default=utils.env('OS_CACERT', default=None),
            help=_('CA certificate bundle file (Env: OS_CACERT)'),
        )
        parser.add_argument(
            '--os-cert',
            metavar='<certificate-file>',
            dest='cert',
            default=utils.env('OS_CERT'),
            help=_('Client certificate bundle file (Env: OS_CERT)'),
        )
        parser.add_argument(
            '--os-key',
            metavar='<key-file>',
            dest='key',
            default=utils.env('OS_KEY'),
            help=_('Client certificate key file (Env: OS_KEY)'),
        )
        verify_group = parser.add_mutually_exclusive_group()
        verify_group.add_argument(
            '--verify',
            action='store_true',
            default=None,
            help=_('Verify server certificate (default)'),
        )
        verify_group.add_argument(
            '--insecure',
            action='store_true',
            default=None,
            help=_('Disable server certificate verification'),
        )
        parser.add_argument(
            '--os-default-domain',
            metavar='<auth-domain>',
            dest='default_domain',
            default=utils.env(
                'OS_DEFAULT_DOMAIN',
                default=DEFAULT_DOMAIN),
            help=_('Default domain ID, default=%s. '
                   '(Env: OS_DEFAULT_DOMAIN)') % DEFAULT_DOMAIN,
        )
        parser.add_argument(
            '--os-interface',
            metavar='<interface>',
            dest='interface',
            choices=['admin', 'public', 'internal'],
            default=utils.env(
                'OS_INTERFACE',
                default=DEFAULT_INTERFACE),
            help=_('Select an interface type.'
                   ' Valid interface types: [admin, public, internal].'
                   ' default=%s, (Env: OS_INTERFACE)') % DEFAULT_INTERFACE,
        )
        parser.add_argument(
            '--os-service-provider',
            metavar='<service_provider>',
            dest='service_provider',
            default=utils.env('OS_SERVICE_PROVIDER'),
            help=_('Authenticate with and perform the command on a service'
                   ' provider using Keystone-to-keystone federation. Must'
                   ' also specify the remote project option.')
        )
        remote_project_group = parser.add_mutually_exclusive_group()
        remote_project_group.add_argument(
            '--os-remote-project-name',
            metavar='<remote_project_name>',
            dest='remote_project_name',
            default=utils.env('OS_REMOTE_PROJECT_NAME'),
            help=_('Project name when authenticating to a service provider'
                   ' if using Keystone-to-Keystone federation.')
        )
        remote_project_group.add_argument(
            '--os-remote-project-id',
            metavar='<remote_project_id>',
            dest='remote_project_id',
            default=utils.env('OS_REMOTE_PROJECT_ID'),
            help=_('Project ID when authenticating to a service provider'
                   ' if using Keystone-to-Keystone federation.')
        )
        remote_project_domain_group = parser.add_mutually_exclusive_group()
        remote_project_domain_group.add_argument(
            '--os-remote-project-domain-name',
            metavar='<remote_project_domain_name>',
            dest='remote_project_domain_name',
            default=utils.env('OS_REMOTE_PROJECT_DOMAIN_NAME'),
            help=_('Domain name of the project when authenticating to a'
                   ' service provider if using Keystone-to-Keystone'
                   ' federation.')
        )
        remote_project_domain_group.add_argument(
            '--os-remote-project-domain-id',
            metavar='<remote_project_domain_id>',
            dest='remote_project_domain_id',
            default=utils.env('OS_REMOTE_PROJECT_DOMAIN_ID'),
            help=_('Domain ID of the project when authenticating to a'
                   ' service provider if using Keystone-to-Keystone'
                   ' federation.')
        )
        parser.add_argument(
            '--timing',
            default=False,
            action='store_true',
            help=_("Print API call timing info"),
        )
        parser.add_argument(
            '--os-beta-command',
            action='store_true',
            help=_("Enable beta commands which are subject to change"),
        )

        # osprofiler HMAC key argument
        if osprofiler_profiler:
            parser.add_argument(
                '--os-profile',
                metavar='hmac-key',
                dest='profile',
                default=utils.env('OS_PROFILE'),
                help=_('HMAC key for encrypting profiling context data'),
            )

        return parser
        # return clientmanager.build_plugin_option_parser(parser)

    """
    Break up initialize_app() so that overriding it in a subclass does not
    require duplicating a lot of the method

    * super()
    * _final_defaults()
    * OpenStackConfig
    * get_one
    * _load_plugins()
    * _load_commands()
    * ClientManager

    """
    def _final_defaults(self):
        # Set the default plugin to None
        # NOTE(dtroyer): This is here to set up for setting it to a default
        #                in the calling CLI
        self._auth_type = None

        # Converge project/tenant options
        project_id = getattr(self.options, 'project_id', None)
        project_name = getattr(self.options, 'project_name', None)
        tenant_id = getattr(self.options, 'tenant_id', None)
        tenant_name = getattr(self.options, 'tenant_name', None)

        # handle some v2/v3 authentication inconsistencies by just acting like
        # both the project and tenant information are both present. This can
        # go away if we stop registering all the argparse options together.
        if project_id and not tenant_id:
            self.options.tenant_id = project_id
        if project_name and not tenant_name:
            self.options.tenant_name = project_name
        if tenant_id and not project_id:
            self.options.project_id = tenant_id
        if tenant_name and not project_name:
            self.options.project_name = tenant_name

        # Save default domain
        self.default_domain = self.options.default_domain

    def _load_plugins(self):
        """Load plugins via stevedore

        osc-lib has no opinion on what plugins should be loaded
        """
        pass

    def _load_commands(self):
        """Load commands via cliff/stevedore

        osc-lib has no opinion on what commands should be loaded
        """
        pass

    def initialize_app(self, argv):
        """Global app init bits:

        * set up API versions
        * validate authentication info
        * authenticate against Identity if requested
        """

        # Parent __init__ parses argv into self.options
        super(OpenStackShell, self).initialize_app(argv)
        self.log.info("START with options: %s",
                      strutils.mask_password(" ".join(self.command_options)))
        self.log.debug("options: %s",
                       strutils.mask_password(self.options))

        # Callout for stuff between superclass init and o-c-c
        self._final_defaults()

        # Do configuration file handling
        try:
            self.cloud_config = cloud_config.OSC_Config(
                pw_func=prompt_for_password,
                override_defaults={
                    'interface': None,
                    'auth_type': self._auth_type,
                },
            )
        except (IOError, OSError) as e:
            self.log.critical("Could not read clouds.yaml configuration file")
            self.print_help_if_requested()
            raise e

        # TODO(thowe): Change cliff so the default value for debug
        # can be set to None.
        if not self.options.debug:
            self.options.debug = None

        # NOTE(dtroyer): Need to do this with validate=False to defer the
        #                auth plugin handling to ClientManager.setup_auth()
        self.cloud = self.cloud_config.get_one(
            cloud=self.options.cloud,
            argparse=self.options,
            validate=False,
        )

        self.log_configurator.configure(self.cloud)
        self.dump_stack_trace = self.log_configurator.dump_trace
        self.log.debug("defaults: %s", self.cloud_config.defaults)
        self.log.debug("cloud cfg: %s",
                       strutils.mask_password(self.cloud.config))

        # Callout for stuff between o-c-c and ClientManager
        # self._initialize_app_2(self.options)

        self._load_plugins()

        self._load_commands()

        # Handle deferred help and exit
        self.print_help_if_requested()

        self.client_manager = clientmanager.ClientManager(
            cli_options=self.cloud,
            api_version=self.api_version,
            pw_func=prompt_for_password,
        )

    def prepare_to_run_command(self, cmd):
        """Set up auth and API versions"""
        self.log.info(
            'command: %s -> %s.%s (auth=%s)',
            getattr(cmd, 'cmd_name', '<none>'),
            cmd.__class__.__module__,
            cmd.__class__.__name__,
            cmd.auth_required,
        )

        # NOTE(dtroyer): If auth is not required for a command, skip
        #                get_one()'s validation to avoid loading plugins
        validate = cmd.auth_required

        # NOTE(dtroyer): Save the auth required state of the _current_ command
        #                in the ClientManager
        self.client_manager._auth_required = cmd.auth_required

        # Validate auth options
        self.cloud = self.cloud_config.get_one(
            cloud=self.options.cloud,
            argparse=self.options,
            validate=validate,
            app_name=self.client_manager._app_name,
            app_version=self.client_manager._app_version,
            additional_user_agent=[('osc-lib', version.version_string)],
        )
        # Push the updated args into ClientManager
        self.client_manager._cli_options = self.cloud

        if cmd.auth_required:
            self.client_manager.setup_auth()
            if hasattr(cmd, 'required_scope') and cmd.required_scope:
                # let the command decide whether we need a scoped token
                self.client_manager.validate_scope()
            # Trigger the Identity client to initialize
            self.client_manager.auth_ref
        return

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s: %s', cmd.__class__.__name__, err or '')

        # Process collected timing data
        if self.options.timing:
            # Get session data
            self.timing_data.extend(
                self.client_manager.session.get_timings(),
            )

            # Use the Timing pseudo-command to generate the output
            tcmd = timing.Timing(self, self.options)
            tparser = tcmd.get_parser('Timing')

            # If anything other than prettytable is specified, force csv
            format = 'table'
            # Check the formatter used in the actual command
            if hasattr(cmd, 'formatter') \
                    and cmd.formatter != cmd._formatter_plugins['table'].obj:
                format = 'csv'

            sys.stdout.write('\n')
            targs = tparser.parse_args(['-f', format])
            tcmd.run(targs)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
        if six.PY2:
            # Emulate Py3, decode argv into Unicode based on locale so that
            # commands always see arguments as text instead of binary data
            encoding = locale.getpreferredencoding()
            if encoding:
                argv = map(lambda arg: arg.decode(encoding), argv)
    return OpenStackShell().run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
