# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re
import sys

import ddt
import fixtures
import mock
from six import moves
from tempest.lib.cli import output_parser
from testtools import matchers

import manilaclient
from manilaclient.common import cliutils
from manilaclient.common import constants
from manilaclient import exceptions
from manilaclient import shell
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes


@ddt.ddt
class OpenstackManilaShellTest(utils.TestCase):

    FAKE_ENV = {
        'OS_USERNAME': 'username',
        'OS_PASSWORD': 'password',
        'OS_TENANT_NAME': 'tenant_name',
        'OS_AUTH_URL': 'http://no.where',
    }

    # Patch os.environ to avoid required auth info.
    def set_env_vars(self, env_vars):
        for k, v in env_vars.items():
            self.useFixture(fixtures.EnvironmentVariable(k, v))

    def shell_discover_client(self,
                              current_client,
                              os_api_version,
                              os_endpoint_type,
                              os_service_type,
                              client_args):
        return current_client, manilaclient.API_MAX_VERSION

    def shell(self, argstr):
        orig = sys.stdout
        try:
            sys.stdout = moves.StringIO()
            _shell = shell.OpenStackManilaShell()
            _shell._discover_client = self.shell_discover_client
            _shell.main(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(exc_value.code, 0)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out

    @ddt.data(
        {},
        {'OS_AUTH_URL': 'http://foo.bar'},
        {'OS_AUTH_URL': 'http://foo.bar', 'OS_USERNAME': 'foo'},
        {'OS_AUTH_URL': 'http://foo.bar', 'OS_USERNAME': 'foo_user',
         'OS_PASSWORD': 'foo_password'},
        {'OS_TENANT_NAME': 'foo_tenant', 'OS_USERNAME': 'foo_user',
         'OS_PASSWORD': 'foo_password'},
        {'OS_TOKEN': 'foo_token'},
        {'OS_MANILA_BYPASS_URL': 'http://foo.foo'},
    )
    def test_main_failure(self, env_vars):
        self.set_env_vars(env_vars)
        with mock.patch.object(shell, 'client') as mock_client:
            self.assertRaises(exceptions.CommandError, self.shell, 'list')
            self.assertFalse(mock_client.Client.called)

    def test_main_success(self):
        env_vars = {
            'OS_AUTH_URL': 'http://foo.bar',
            'OS_USERNAME': 'foo_username',
            'OS_USER_ID': 'foo_user_id',
            'OS_PASSWORD': 'foo_password',
            'OS_TENANT_NAME': 'foo_tenant',
            'OS_TENANT_ID': 'foo_tenant_id',
            'OS_PROJECT_NAME': 'foo_project',
            'OS_PROJECT_ID': 'foo_project_id',
            'OS_PROJECT_DOMAIN_ID': 'foo_project_domain_id',
            'OS_PROJECT_DOMAIN_NAME': 'foo_project_domain_name',
            'OS_PROJECT_DOMAIN_ID': 'foo_project_domain_id',
            'OS_USER_DOMAIN_NAME': 'foo_user_domain_name',
            'OS_USER_DOMAIN_ID': 'foo_user_domain_id',
            'OS_CERT': 'foo_cert',
        }
        self.set_env_vars(env_vars)
        with mock.patch.object(shell, 'client') as mock_client:

            self.shell('list')

            mock_client.Client.assert_called_with(
                manilaclient.API_MAX_VERSION,
                username=env_vars['OS_USERNAME'],
                password=env_vars['OS_PASSWORD'],
                project_name=env_vars['OS_PROJECT_NAME'],
                auth_url=env_vars['OS_AUTH_URL'],
                insecure=False,
                region_name='',
                tenant_id=env_vars['OS_PROJECT_ID'],
                endpoint_type='publicURL',
                extensions=mock.ANY,
                service_type=constants.V2_SERVICE_TYPE,
                service_name='',
                retries=0,
                http_log_debug=False,
                cacert=None,
                use_keyring=False,
                force_new_token=False,
                user_id=env_vars['OS_USER_ID'],
                user_domain_id=env_vars['OS_USER_DOMAIN_ID'],
                user_domain_name=env_vars['OS_USER_DOMAIN_NAME'],
                project_domain_id=env_vars['OS_PROJECT_DOMAIN_ID'],
                project_domain_name=env_vars['OS_PROJECT_DOMAIN_NAME'],
                cert=env_vars['OS_CERT'],
                input_auth_token='',
                service_catalog_url='',
            )

    @ddt.data(
        {"env_vars": {"OS_MANILA_BYPASS_URL": "http://foo.url",
                      "OS_TOKEN": "foo_token"},
         "kwargs": {"--os-token": "bar_token",
                    "--bypass-url": "http://bar.url"},
         "expected": {"input_auth_token": "bar_token",
                      "service_catalog_url": "http://bar.url"}},
        {"env_vars": {"OS_MANILA_BYPASS_URL": "http://foo.url",
                      "OS_TOKEN": "foo_token"},
         "kwargs": {},
         "expected": {"input_auth_token": "foo_token",
                      "service_catalog_url": "http://foo.url"}},
        {"env_vars": {},
         "kwargs": {"--os-token": "bar_token",
                    "--bypass-url": "http://bar.url"},
         "expected": {"input_auth_token": "bar_token",
                      "service_catalog_url": "http://bar.url"}},
        {"env_vars": {"MANILACLIENT_BYPASS_URL": "http://foo.url",
                      "OS_TOKEN": "foo_token"},
         "kwargs": {},
         "expected": {"input_auth_token": "foo_token",
                      "service_catalog_url": "http://foo.url"}},
        {"env_vars": {"OS_TOKEN": "foo_token"},
         "kwargs": {"--bypass-url": "http://bar.url"},
         "expected": {"input_auth_token": "foo_token",
                      "service_catalog_url": "http://bar.url"}},
        {"env_vars": {"MANILACLIENT_BYPASS_URL": "http://foo.url",
                      "OS_MANILA_BYPASS_URL": "http://bar.url",
                      "OS_TOKEN": "foo_token"},
         "kwargs": {"--os-token": "bar_token"},
         "expected": {"input_auth_token": "bar_token",
                      "service_catalog_url": "http://bar.url"}},
    )
    @ddt.unpack
    def test_main_success_with_token(self, env_vars, kwargs, expected):
        self.set_env_vars(env_vars)
        with mock.patch.object(shell, "client") as mock_client:
            cmd = ""
            for k, v in kwargs.items():
                cmd += "%s=%s " % (k, v)
            cmd += "list"

            self.shell(cmd)

            mock_client.Client.assert_called_with(
                manilaclient.API_MAX_VERSION,
                username="",
                password="",
                project_name="",
                auth_url="",
                insecure=False,
                region_name="",
                tenant_id="",
                endpoint_type="publicURL",
                extensions=mock.ANY,
                service_type=constants.V2_SERVICE_TYPE,
                service_name="",
                retries=0,
                http_log_debug=False,
                cacert=None,
                use_keyring=False,
                force_new_token=False,
                user_id="",
                user_domain_id="",
                user_domain_name="",
                project_domain_id="",
                project_domain_name="",
                cert="",
                input_auth_token=expected["input_auth_token"],
                service_catalog_url=expected["service_catalog_url"],
            )

    @ddt.data(
        # default without any env var or kwargs
        {
            "env_vars": {"OS_TOKEN": "foo_token",
                         "OS_MANILA_BYPASS_URL": "http://bar.url"},
            "kwargs": {},
            "expected": {"input_auth_token": "foo_token",
                         "service_catalog_url": "http://bar.url",
                         "os_endpoint_type": "publicURL"}
        },
        # only env var
        {
            "env_vars": {"OS_TOKEN": "foo_token",
                         "OS_MANILA_BYPASS_URL": "http://bar.url",
                         "OS_MANILA_ENDPOINT_TYPE": "custom-endpoint-type"},
            "kwargs": {},
            "expected": {"input_auth_token": "foo_token",
                         "service_catalog_url": "http://bar.url",
                         "os_endpoint_type": "custom-endpoint-type"},
        },
        # only kwargs
        {
            "env_vars": {"OS_TOKEN": "foo_token",
                         "OS_MANILA_BYPASS_URL": "http://bar.url"},
            "kwargs": {"--endpoint-type": "custom-kwargs-endpoint-type"},
            "expected": {"input_auth_token": "foo_token",
                         "service_catalog_url": "http://bar.url",
                         "os_endpoint_type": "custom-kwargs-endpoint-type"},
        },
        # env var *and* kwargs (kwargs should win)
        {
            "env_vars": {"OS_TOKEN": "foo_token",
                         "OS_MANILA_BYPASS_URL": "http://bar.url",
                         "os_endpoint_type": "custom-env-endpoint-type"},
            "kwargs": {"--endpoint-type": "custom-kwargs-endpoint-type"},
            "expected": {"input_auth_token": "foo_token",
                         "service_catalog_url": "http://bar.url",
                         "os_endpoint_type": "custom-kwargs-endpoint-type"},
        }
    )
    @ddt.unpack
    def test_main_success_with_os_endpoint(self, env_vars, kwargs, expected):
        self.set_env_vars(env_vars)
        with mock.patch.object(shell, "client") as mock_client:
            cmd = ""
            for k, v in kwargs.items():
                cmd += "%s=%s " % (k, v)
            cmd += "list"

            self.shell(cmd)

            mock_client.Client.assert_called_with(
                manilaclient.API_MAX_VERSION,
                username="",
                password="",
                project_name="",
                auth_url="",
                insecure=False,
                region_name="",
                tenant_id="",
                endpoint_type=expected["os_endpoint_type"],
                extensions=mock.ANY,
                service_type=constants.V2_SERVICE_TYPE,
                service_name="",
                retries=0,
                http_log_debug=False,
                cacert=None,
                use_keyring=False,
                force_new_token=False,
                user_id="",
                user_domain_id="",
                user_domain_name="",
                project_domain_id="",
                project_domain_name="",
                cert="",
                input_auth_token=expected["input_auth_token"],
                service_catalog_url=expected["service_catalog_url"],
            )

    def test_help_unknown_command(self):
        self.assertRaises(exceptions.CommandError, self.shell, 'help foofoo')

    @ddt.data('list --help', '--help list', 'help list')
    def test_help_on_subcommand(self, cmd):
        required = [
            '.*?^usage: manila list',
            '.*?(?m)^List NAS shares with filters.',
        ]
        help_text = self.shell(cmd)
        for r in required:
            self.assertThat(help_text,
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_common_args_in_help_message(self):
        expected_args = (
            '--version', '', '--debug', '--os-cache', '--os-reset-cache',
            '--os-user-id', '--os-username', '--os-password',
            '--os-tenant-name', '--os-project-name', '--os-tenant-id',
            '--os-project-id', '--os-user-domain-id', '--os-user-domain-name',
            '--os-project-domain-id', '--os-project-domain-name',
            '--os-auth-url', '--os-region-name', '--service-type',
            '--service-name', '--share-service-name', '--endpoint-type',
            '--os-share-api-version', '--os-cacert', '--retries', '--os-cert',
        )

        help_text = self.shell('help')

        for expected_arg in expected_args:
            self.assertIn(expected_arg, help_text)


class CustomOpenStackManilaShell(shell.OpenStackManilaShell):

    @staticmethod
    @cliutils.arg(
        '--default-is-none',
        '--default_is_none',
        type=str,
        metavar='<redefined_metavar>',
        action='single_alias',
        help='Default value is None and metavar set.',
        default=None)
    def do_foo(cs, args):
        cliutils.print_dict({'key': args.default_is_none})

    @staticmethod
    @cliutils.arg(
        '--default-is-not-none',
        '--default_is_not_none',
        type=str,
        action='single_alias',
        help='Default value is not None and metavar not set.',
        default='bar')
    def do_bar(cs, args):
        cliutils.print_dict({'key': args.default_is_not_none})

    @staticmethod
    @cliutils.arg(
        '--list-like',
        '--list_like',
        nargs='*',
        action='single_alias',
        help='Default value is None, metavar not set and result is list.',
        default=None)
    def do_quuz(cs, args):
        cliutils.print_dict({'key': args.list_like})


@ddt.ddt
class AllowOnlyOneAliasAtATimeActionTest(utils.TestCase):
    FAKE_ENV = {
        'OS_USERNAME': 'username',
        'OS_PASSWORD': 'password',
        'OS_TENANT_NAME': 'tenant_name',
        'OS_AUTH_URL': 'http://no.where',
    }

    def setUp(self):
        super(self.__class__, self).setUp()
        for k, v in self.FAKE_ENV.items():
            self.useFixture(fixtures.EnvironmentVariable(k, v))
        self.mock_object(
            shell.client, 'get_client_class',
            mock.Mock(return_value=fakes.FakeClient))

    def shell_discover_client(self,
                              current_client,
                              os_api_version,
                              os_endpoint_type,
                              os_service_type,
                              client_args):
        return current_client, manilaclient.API_MAX_VERSION

    def shell(self, argstr):
        orig = sys.stdout
        try:
            sys.stdout = moves.StringIO()
            _shell = CustomOpenStackManilaShell()
            _shell._discover_client = self.shell_discover_client
            _shell.main(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(exc_value.code, 0)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out

    @ddt.data(
        ('--default-is-none foo', 'foo'),
        ('--default-is-none foo --default-is-none foo', 'foo'),
        ('--default-is-none foo --default_is_none foo', 'foo'),
        ('--default_is_none None', 'None'),
    )
    @ddt.unpack
    def test_foo_success(self, options_str, expected_result):
        output = self.shell('foo %s' % options_str)
        parsed_output = output_parser.details(output)
        self.assertEqual({'key': expected_result}, parsed_output)

    @ddt.data(
        '--default-is-none foo --default-is-none bar',
        '--default-is-none foo --default_is_none bar',
        '--default-is-none foo --default_is_none FOO',
    )
    def test_foo_error(self, options_str):
        self.assertRaises(
            matchers.MismatchError, self.shell, 'foo %s' % options_str)

    @ddt.data(
        ('--default-is-not-none bar', 'bar'),
        ('--default_is_not_none bar --default-is-not-none bar', 'bar'),
        ('--default_is_not_none bar --default_is_not_none bar', 'bar'),
        ('--default-is-not-none not_bar', 'not_bar'),
        ('--default_is_not_none None', 'None'),
    )
    @ddt.unpack
    def test_bar_success(self, options_str, expected_result):
        output = self.shell('bar %s' % options_str)
        parsed_output = output_parser.details(output)
        self.assertEqual({'key': expected_result}, parsed_output)

    @ddt.data(
        '--default-is-not-none foo --default-is-not-none bar',
        '--default-is-not-none foo --default_is_not_none bar',
        '--default-is-not-none bar --default_is_not_none BAR',
    )
    def test_bar_error(self, options_str):
        self.assertRaises(
            matchers.MismatchError, self.shell, 'bar %s' % options_str)

    @ddt.data(
        ('--list-like q=w', "['q=w']"),
        ('--list-like q=w --list_like q=w', "['q=w']"),
        ('--list-like q=w e=r t=y --list_like e=r t=y q=w',
         "['e=r', 'q=w', 't=y']"),
        ('--list_like q=w e=r t=y', "['e=r', 'q=w', 't=y']"),
    )
    @ddt.unpack
    def test_quuz_success(self, options_str, expected_result):
        output = self.shell('quuz %s' % options_str)
        parsed_output = output_parser.details(output)
        self.assertEqual({'key': expected_result}, parsed_output)

    @ddt.data(
        '--list-like q=w --list_like e=r t=y',
    )
    def test_quuz_error(self, options_str):
        self.assertRaises(
            matchers.MismatchError, self.shell, 'quuz %s' % options_str)
