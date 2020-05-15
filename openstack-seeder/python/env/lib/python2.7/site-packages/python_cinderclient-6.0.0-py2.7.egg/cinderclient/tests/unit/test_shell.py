# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import re
import sys
import unittest

import ddt
import fixtures
import keystoneauth1.exceptions as ks_exc
from keystoneauth1.exceptions import DiscoveryFailure
from keystoneauth1.identity.generic.password import Password as ks_password
from keystoneauth1 import session
import mock
import requests_mock
from six import moves
from testtools import matchers

import cinderclient
from cinderclient import api_versions
from cinderclient.contrib import noauth
from cinderclient import exceptions
from cinderclient import shell
from cinderclient.tests.unit import fake_actions_module
from cinderclient.tests.unit.fixture_data import keystone_client
from cinderclient.tests.unit import utils


@ddt.ddt
class ShellTest(utils.TestCase):

    FAKE_ENV = {
        'OS_USERNAME': 'username',
        'OS_PASSWORD': 'password',
        'OS_PROJECT_NAME': 'tenant_name',
        'OS_AUTH_URL': 'http://no.where/v2.0',
    }

    # Patch os.environ to avoid required auth info.
    def make_env(self, exclude=None, include=None):
        env = dict((k, v) for k, v in self.FAKE_ENV.items() if k != exclude)
        env.update(include or {})
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))

    def setUp(self):
        super(ShellTest, self).setUp()
        for var in self.FAKE_ENV:
            self.useFixture(fixtures.EnvironmentVariable(var,
                                                         self.FAKE_ENV[var]))

        self.mock_completion()

    def shell(self, argstr):
        orig = sys.stdout
        try:
            sys.stdout = moves.StringIO()
            _shell = shell.OpenStackCinderShell()
            _shell.main(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertEqual(0, exc_value.code)
        finally:
            out = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig

        return out

    def test_default_auth_env(self):
        _shell = shell.OpenStackCinderShell()
        args, __ = _shell.get_base_parser().parse_known_args([])
        self.assertEqual('', args.os_auth_type)

    def test_auth_type_env(self):
        self.make_env(exclude='OS_PASSWORD',
                      include={'OS_AUTH_SYSTEM': 'non existent auth',
                               'OS_AUTH_TYPE': 'noauth'})
        _shell = shell.OpenStackCinderShell()
        args, __ = _shell.get_base_parser().parse_known_args([])
        self.assertEqual('noauth', args.os_auth_type)

    def test_auth_system_env(self):
        self.make_env(exclude='OS_PASSWORD',
                      include={'OS_AUTH_SYSTEM': 'noauth'})
        _shell = shell.OpenStackCinderShell()
        args, __ = _shell.get_base_parser().parse_known_args([])
        self.assertEqual('noauth', args.os_auth_type)

    @mock.patch.object(cinderclient.shell.OpenStackCinderShell,
                       '_get_keystone_session')
    @mock.patch.object(cinderclient.client.SessionClient, 'authenticate',
                       side_effect=RuntimeError())
    def test_password_auth_type(self, mock_authenticate,
                                mock_get_session):
        self.make_env(include={'OS_AUTH_TYPE': 'password'})
        _shell = shell.OpenStackCinderShell()

        # We crash the command after Client instantiation because this test
        # focuses only keystoneauth1 indentity cli opts parsing.
        self.assertRaises(RuntimeError, _shell.main, ['list'])
        self.assertIsInstance(_shell.cs.client.session.auth,
                              ks_password)

    def test_help_unknown_command(self):
        self.assertRaises(exceptions.CommandError, self.shell, 'help foofoo')

    def test_help(self):
        # Some expected help output, including microversioned commands
        required = [
            r'.*?^usage: ',
            r'.*?(?m)^\s+create\s+Creates a volume.',
            r'.*?(?m)^\s+summary\s+Get volumes summary.',
            r'.*?(?m)^Run "cinder help SUBCOMMAND" for help on a subcommand.',
        ]
        help_text = self.shell('help')
        for r in required:
            self.assertThat(help_text,
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_on_subcommand(self):
        required = [
            r'.*?^usage: cinder list',
            r'.*?(?m)^Lists all volumes.',
        ]
        help_text = self.shell('help list')
        for r in required:
            self.assertThat(help_text,
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_on_subcommand_mv(self):
        required = [
            r'.*?^usage: cinder summary',
            r'.*?(?m)^Get volumes summary.',
        ]
        help_text = self.shell('help summary')
        for r in required:
            self.assertThat(help_text,
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    @ddt.data('backup-create --help', '--help backup-create')
    def test_dash_dash_help_on_subcommand(self, cmd):
        required = ['.*?^Creates a volume backup.']
        help_text = self.shell(cmd)

        for r in required:
            self.assertThat(help_text,
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def register_keystone_auth_fixture(self, mocker, url):
        mocker.register_uri('GET', url,
                            text=keystone_client.keystone_request_callback)

    @requests_mock.Mocker()
    def test_version_discovery(self, mocker):
        _shell = shell.OpenStackCinderShell()
        sess = session.Session()

        os_auth_url = "https://wrongdiscoveryresponse.discovery.com:35357/v2.0"
        self.register_keystone_auth_fixture(mocker, os_auth_url)

        self.assertRaises(DiscoveryFailure,
                          _shell._discover_auth_versions,
                          sess,
                          auth_url=os_auth_url)

        os_auth_url = "https://DiscoveryNotSupported.discovery.com:35357/v2.0"
        self.register_keystone_auth_fixture(mocker, os_auth_url)
        v2_url, v3_url = _shell._discover_auth_versions(sess,
                                                        auth_url=os_auth_url)
        self.assertEqual(os_auth_url, v2_url, "Expected v2 url")
        self.assertIsNone(v3_url, "Expected no v3 url")

        os_auth_url = "https://DiscoveryNotSupported.discovery.com:35357/v3.0"
        self.register_keystone_auth_fixture(mocker, os_auth_url)
        v2_url, v3_url = _shell._discover_auth_versions(sess,
                                                        auth_url=os_auth_url)
        self.assertEqual(os_auth_url, v3_url, "Expected v3 url")
        self.assertIsNone(v2_url, "Expected no v2 url")

    @requests_mock.Mocker()
    def list_volumes_on_service(self, count, mocker):
        os_auth_url = "http://multiple.service.names/v2.0"
        mocker.register_uri('POST', os_auth_url + "/tokens",
                            text=keystone_client.keystone_request_callback)
        mocker.register_uri('GET',
                            "http://cinder%i.api.com/v2/volumes/detail"
                            % count, text='{"volumes": []}')
        self.make_env(include={'OS_AUTH_URL': os_auth_url,
                               'CINDER_SERVICE_NAME': 'cinder%i' % count})
        _shell = shell.OpenStackCinderShell()
        _shell.main(['list'])

    def test_duplicate_filters(self):
        _shell = shell.OpenStackCinderShell()
        self.assertRaises(exceptions.CommandError,
                          _shell.main,
                          ['list', '--name', 'abc', '--filters', 'name=xyz'])

    @unittest.skip("Skip cuz I broke it")
    def test_cinder_service_name(self):
        # Failing with 'No mock address' means we are not
        # choosing the correct endpoint
        for count in range(1, 4):
            self.list_volumes_on_service(count)

    @mock.patch('keystoneauth1.identity.v2.Password')
    @mock.patch('keystoneauth1.adapter.Adapter.get_token',
                side_effect=ks_exc.ConnectFailure())
    @mock.patch('keystoneauth1.discover.Discover',
                side_effect=ks_exc.ConnectFailure())
    @mock.patch('sys.stdin', side_effect=mock.Mock)
    @mock.patch('getpass.getpass', return_value='password')
    def test_password_prompted(self, mock_getpass, mock_stdin, mock_discover,
                               mock_token, mock_password):
        self.make_env(exclude='OS_PASSWORD')
        _shell = shell.OpenStackCinderShell()
        self.assertRaises(ks_exc.ConnectFailure, _shell.main, ['list'])
        mock_getpass.assert_called_with('OS Password: ')
        # Verify that Password() is called with value of param 'password'
        # equal to mock_getpass.return_value.
        mock_password.assert_called_with(
            self.FAKE_ENV['OS_AUTH_URL'],
            password=mock_getpass.return_value,
            tenant_id='',
            tenant_name=self.FAKE_ENV['OS_PROJECT_NAME'],
            username=self.FAKE_ENV['OS_USERNAME'])

    @requests_mock.Mocker()
    def test_noauth_plugin(self, mocker):
        os_auth_url = "http://example.com/v2"
        mocker.register_uri('GET',
                            "%s/admin/volumes/detail"
                            % os_auth_url, text='{"volumes": []}')
        _shell = shell.OpenStackCinderShell()
        args = ['--os-endpoint', os_auth_url,
                '--os-auth-type', 'noauth', '--os-user-id',
                'admin', '--os-project-id', 'admin', 'list']
        _shell.main(args)
        self.assertIsInstance(_shell.cs.client.session.auth,
                              noauth.CinderNoAuthPlugin)

    @mock.patch.object(cinderclient.client.HTTPClient, 'authenticate',
                       side_effect=exceptions.Unauthorized('No'))
    # Easiest way to make cinderclient use httpclient is a None session
    @mock.patch.object(cinderclient.shell.OpenStackCinderShell,
                       '_get_keystone_session', return_value=None)
    def test_http_client_insecure(self, mock_authenticate, mock_session):
        self.make_env(include={'CINDERCLIENT_INSECURE': True})

        _shell = shell.OpenStackCinderShell()

        # This "fails" but instantiates the client.
        self.assertRaises(exceptions.CommandError, _shell.main, ['list'])

        self.assertEqual(False, _shell.cs.client.verify_cert)

    @mock.patch.object(cinderclient.client.SessionClient, 'authenticate',
                       side_effect=exceptions.Unauthorized('No'))
    def test_session_client_debug_logger(self, mock_session):
        _shell = shell.OpenStackCinderShell()
        # This "fails" but instantiates the client.
        self.assertRaises(exceptions.CommandError, _shell.main,
                          ['--debug', 'list'])
        # In case of SessionClient when --debug switch is specified
        # 'keystoneauth' logger should be initialized.
        self.assertEqual('keystoneauth', _shell.cs.client.logger.name)

    @mock.patch('keystoneauth1.session.Session.__init__',
                side_effect=RuntimeError())
    def test_http_client_with_cert(self, mock_session):
        _shell = shell.OpenStackCinderShell()

        # We crash the command after Session instantiation because this test
        # focuses only on arguments provided to Session.__init__
        args = '--os-cert', 'minnie', 'list'
        self.assertRaises(RuntimeError, _shell.main, args)
        mock_session.assert_called_once_with(cert='minnie', verify=mock.ANY)

    @mock.patch('keystoneauth1.session.Session.__init__',
                side_effect=RuntimeError())
    def test_http_client_with_cert_and_key(self, mock_session):
        _shell = shell.OpenStackCinderShell()

        # We crash the command after Session instantiation because this test
        # focuses only on arguments provided to Session.__init__
        args = '--os-cert', 'minnie', '--os-key', 'mickey', 'list'
        self.assertRaises(RuntimeError, _shell.main, args)
        mock_session.assert_called_once_with(cert=('minnie', 'mickey'),
                                             verify=mock.ANY)


class CinderClientArgumentParserTest(utils.TestCase):

    def setUp(self):
        super(CinderClientArgumentParserTest, self).setUp()

        self.mock_completion()

    def test_ambiguity_solved_for_one_visible_argument(self):
        parser = shell.CinderClientArgumentParser(add_help=False)
        parser.add_argument('--test-parameter',
                            dest='visible_param',
                            action='store_true')
        parser.add_argument('--test_parameter',
                            dest='hidden_param',
                            action='store_true',
                            help=argparse.SUPPRESS)

        opts = parser.parse_args(['--test'])

        # visible argument must be set
        self.assertTrue(opts.visible_param)
        self.assertFalse(opts.hidden_param)

    def test_raise_ambiguity_error_two_visible_argument(self):
        parser = shell.CinderClientArgumentParser(add_help=False)
        parser.add_argument('--test-parameter',
                            dest="visible_param1",
                            action='store_true')
        parser.add_argument('--test_parameter',
                            dest="visible_param2",
                            action='store_true')

        self.assertRaises(SystemExit, parser.parse_args, ['--test'])

    def test_raise_ambiguity_error_two_hidden_argument(self):
        parser = shell.CinderClientArgumentParser(add_help=False)
        parser.add_argument('--test-parameter',
                            dest="hidden_param1",
                            action='store_true',
                            help=argparse.SUPPRESS)
        parser.add_argument('--test_parameter',
                            dest="hidden_param2",
                            action='store_true',
                            help=argparse.SUPPRESS)

        self.assertRaises(SystemExit, parser.parse_args, ['--test'])


class TestLoadVersionedActions(utils.TestCase):
    def setUp(self):
        super(TestLoadVersionedActions, self).setUp()

        self.mock_completion()

    def test_load_versioned_actions(self):
        parser = cinderclient.shell.CinderClientArgumentParser()
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.0"), False, [])
        self.assertIn('fake-action', shell.subcommands.keys())
        self.assertEqual(
            "fake_action 3.0 to 3.1",
            shell.subcommands['fake-action'].get_default('func')())

        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.2"), False, [])
        self.assertIn('fake-action', shell.subcommands.keys())
        self.assertEqual(
            "fake_action 3.2 to 3.3",
            shell.subcommands['fake-action'].get_default('func')())

        self.assertIn('fake-action2', shell.subcommands.keys())
        self.assertEqual(
            "fake_action2",
            shell.subcommands['fake-action2'].get_default('func')())

    def test_load_versioned_actions_not_in_version_range(self):
        parser = cinderclient.shell.CinderClientArgumentParser()
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion('3.10000'), False, [])
        self.assertNotIn('fake-action', shell.subcommands.keys())
        self.assertIn('fake-action2', shell.subcommands.keys())

    def test_load_versioned_actions_unsupported_input(self):
        parser = cinderclient.shell.CinderClientArgumentParser()
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        self.assertRaises(exceptions.UnsupportedAttribute,
                          shell._find_actions, subparsers, fake_actions_module,
                          api_versions.APIVersion('3.6'), False,
                          ['another-fake-action', '--foo'])

    def test_load_versioned_actions_with_help(self):
        parser = cinderclient.shell.CinderClientArgumentParser()
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        with mock.patch.object(subparsers, 'add_parser') as mock_add_parser:
            shell._find_actions(subparsers, fake_actions_module,
                                api_versions.APIVersion("3.1"), True, [])
            self.assertIn('fake-action', shell.subcommands.keys())
            expected_help = ("help message (Supported by API versions "
                             "%(start)s - %(end)s)") % {
                'start': '3.0', 'end': '3.3'}
            expected_desc = ("help message\n\n    "
                            "This will not show up in help message\n    ")
            mock_add_parser.assert_any_call(
                'fake-action',
                help=expected_help,
                description=expected_desc,
                add_help=False,
                formatter_class=cinderclient.shell.OpenStackHelpFormatter)

    def test_load_versioned_actions_with_help_on_latest(self):
        parser = cinderclient.shell.CinderClientArgumentParser()
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        with mock.patch.object(subparsers, 'add_parser') as mock_add_parser:
            shell._find_actions(subparsers, fake_actions_module,
                                api_versions.APIVersion("3.latest"), True, [])
            self.assertIn('another-fake-action', shell.subcommands.keys())
            expected_help = (" (Supported by API versions %(start)s - "
                             "%(end)s)%(hint)s") % {
                'start': '3.6', 'end': '3.latest',
                'hint': cinderclient.shell.HINT_HELP_MSG}
            mock_add_parser.assert_any_call(
                'another-fake-action',
                help=expected_help,
                description='',
                add_help=False,
                formatter_class=cinderclient.shell.OpenStackHelpFormatter)

    @mock.patch.object(cinderclient.shell.CinderClientArgumentParser,
                       'add_argument')
    def test_load_versioned_actions_with_args(self, mock_add_arg):
        parser = cinderclient.shell.CinderClientArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.1"), False, [])
        self.assertIn('fake-action2', shell.subcommands.keys())
        mock_add_arg.assert_has_calls([
            mock.call('-h', '--help', action='help', help='==SUPPRESS=='),
            mock.call('--foo')])

    @mock.patch.object(cinderclient.shell.CinderClientArgumentParser,
                       'add_argument')
    def test_load_versioned_actions_with_args2(self, mock_add_arg):
        parser = cinderclient.shell.CinderClientArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.4"), False, [])
        self.assertIn('fake-action2', shell.subcommands.keys())
        mock_add_arg.assert_has_calls([
            mock.call('-h', '--help', action='help', help='==SUPPRESS=='),
            mock.call('--bar', help="bar help")])

    @mock.patch.object(cinderclient.shell.CinderClientArgumentParser,
                       'add_argument')
    def test_load_versioned_actions_with_args_not_in_version_range(
            self, mock_add_arg):
        parser = cinderclient.shell.CinderClientArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.10000"), False, [])
        self.assertIn('fake-action2', shell.subcommands.keys())
        mock_add_arg.assert_has_calls([
            mock.call('-h', '--help', action='help', help='==SUPPRESS==')])

    @mock.patch.object(cinderclient.shell.CinderClientArgumentParser,
                       'add_argument')
    def test_load_versioned_actions_with_args_and_help(self, mock_add_arg):
        parser = cinderclient.shell.CinderClientArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.4"), True, [])
        mock_add_arg.assert_has_calls([
            mock.call('-h', '--help', action='help', help='==SUPPRESS=='),
            mock.call('--bar',
                      help="bar help (Supported by API versions"
                           " 3.3 - 3.4)")])

    @mock.patch.object(cinderclient.shell.CinderClientArgumentParser,
                       'add_argument')
    def test_load_actions_with_versioned_args(self, mock_add_arg):
        parser = cinderclient.shell.CinderClientArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        shell = cinderclient.shell.OpenStackCinderShell()
        shell.subcommands = {}
        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.6"), False, [])
        self.assertIn(mock.call('--foo', help="first foo"),
                      mock_add_arg.call_args_list)
        self.assertNotIn(mock.call('--foo', help="second foo"),
                         mock_add_arg.call_args_list)

        mock_add_arg.reset_mock()

        shell._find_actions(subparsers, fake_actions_module,
                            api_versions.APIVersion("3.9"), False, [])
        self.assertNotIn(mock.call('--foo', help="first foo"),
                         mock_add_arg.call_args_list)
        self.assertIn(mock.call('--foo', help="second foo"),
                      mock_add_arg.call_args_list)


class ShellUtilsTest(utils.TestCase):

    @mock.patch.object(cinderclient.utils, 'print_dict')
    def test_print_volume_image(self, mock_print_dict):
        response = {'os-volume_upload_image': {'name': 'myimg1'}}
        image_resp_tuple = (202, response)
        cinderclient.shell_utils.print_volume_image(image_resp_tuple)

        response = {'os-volume_upload_image':
                    {'name': 'myimg2',
                     'volume_type': None}}
        image_resp_tuple = (202, response)
        cinderclient.shell_utils.print_volume_image(image_resp_tuple)

        response = {'os-volume_upload_image':
                    {'name': 'myimg3',
                     'volume_type': {'id': '1234', 'name': 'sometype'}}}
        image_resp_tuple = (202, response)
        cinderclient.shell_utils.print_volume_image(image_resp_tuple)

        mock_print_dict.assert_has_calls(
            (mock.call({'name': 'myimg1'}),
             mock.call({'name': 'myimg2',
                        'volume_type': None}),
             mock.call({'name': 'myimg3',
                        'volume_type': 'sometype'})))
