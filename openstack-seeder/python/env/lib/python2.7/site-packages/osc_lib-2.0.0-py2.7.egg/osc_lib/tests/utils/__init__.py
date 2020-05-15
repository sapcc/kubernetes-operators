#   Copyright 2012-2013 OpenStack Foundation
#   Copyright 2013 Nebula Inc.
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

import contextlib
import copy
import json as jsonutils
import mock
import os

from cliff import columns as cliff_columns
import fixtures
from keystoneauth1 import loading

from openstack.config import cloud_region
from openstack.config import defaults

from oslo_utils import importutils
from requests_mock.contrib import fixture
import six
import testtools

from osc_lib import clientmanager
from osc_lib import shell
from osc_lib.tests import fakes


def fake_execute(shell, cmd):
    """Pretend to execute shell commands."""
    return shell.run(cmd.split())


def make_shell(shell_class=None):
    """Create a new command shell and mock out some bits."""
    if shell_class is None:
        shell_class = shell.OpenStackShell
    _shell = shell_class()
    _shell.command_manager = mock.Mock()
    # _shell.cloud = mock.Mock()

    return _shell


def opt2attr(opt):
    if opt.startswith('--os-'):
        attr = opt[5:]
    elif opt.startswith('--'):
        attr = opt[2:]
    else:
        attr = opt
    return attr.lower().replace('-', '_')


def opt2env(opt):
    return opt[2:].upper().replace('-', '_')


class EnvFixture(fixtures.Fixture):
    """Environment Fixture.

    This fixture replaces os.environ with provided env or an empty env.
    """

    def __init__(self, env=None):
        self.new_env = env or {}

    def _setUp(self):
        self.orig_env, os.environ = os.environ, self.new_env
        self.addCleanup(self.revert)

    def revert(self):
        os.environ = self.orig_env


class ParserException(Exception):
    pass


class TestCase(testtools.TestCase):

    def setUp(self):
        testtools.TestCase.setUp(self)

        if (os.environ.get("OS_STDOUT_CAPTURE") == "True" or
                os.environ.get("OS_STDOUT_CAPTURE") == "1"):
            stdout = self.useFixture(fixtures.StringStream("stdout")).stream
            self.useFixture(fixtures.MonkeyPatch("sys.stdout", stdout))

        if (os.environ.get("OS_STDERR_CAPTURE") == "True" or
                os.environ.get("OS_STDERR_CAPTURE") == "1"):
            stderr = self.useFixture(fixtures.StringStream("stderr")).stream
            self.useFixture(fixtures.MonkeyPatch("sys.stderr", stderr))

    def assertNotCalled(self, m, msg=None):
        """Assert a function was not called"""

        if m.called:
            if not msg:
                msg = 'method %s should not have been called' % m
            self.fail(msg)

    @contextlib.contextmanager
    def subTest(self, *args, **kwargs):
        """This is a wrapper to unittest's subTest method.

        This wrapper suppresses 2 issues:
         * lack of support in older Python versions
         * bug in testtools that breaks support for all versions
        """
        try:
            with super(TestCase, self).subTest(*args, **kwargs):
                yield
        except TypeError:
            # NOTE(elhararb): subTest is supported by unittest only from PY3.4
            if six.PY2:
                yield
            else:
                raise
        except AttributeError:
            # TODO(elhararb): remove this except clause when subTest is
            #                 enabled in testtools
            yield


class TestCommand(TestCase):
    """Test cliff command classes"""

    def setUp(self):
        super(TestCommand, self).setUp()
        # Build up a fake app
        self.fake_stdout = fakes.FakeStdout()
        self.fake_log = fakes.FakeLog()
        self.app = fakes.FakeApp(self.fake_stdout, self.fake_log)
        self.app.client_manager = fakes.FakeClientManager()

    def check_parser(self, cmd, args, verify_args):
        cmd_parser = cmd.get_parser('check_parser')
        try:
            parsed_args = cmd_parser.parse_args(args)
        except SystemExit:
            raise ParserException("Argument parse failed")
        for av in verify_args:
            attr, value = av
            if attr:
                self.assertIn(attr, parsed_args)
                self.assertEqual(value, getattr(parsed_args, attr))
        return parsed_args

    def assertItemEqual(self, expected, actual):
        """Compare item considering formattable columns.

        This method compares an observed item to an expected item column by
        column. If a column is a formattable column, observed and expected
        columns are compared using human_readable() and machine_readable().
        """
        self.assertEqual(len(expected), len(actual))
        for col_expected, col_actual in zip(expected, actual):
            if isinstance(col_expected, cliff_columns.FormattableColumn):
                self.assertIsInstance(col_actual, col_expected.__class__)
                self.assertEqual(col_expected.human_readable(),
                                 col_actual.human_readable())
                self.assertEqual(col_expected.machine_readable(),
                                 col_actual.machine_readable())
            else:
                self.assertEqual(col_expected, col_actual)

    def assertListItemEqual(self, expected, actual):
        """Compare a list of items considering formattable columns.

        Each pair of observed and expected items are compared
        using assertItemEqual() method.
        """
        self.assertEqual(len(expected), len(actual))
        for item_expected, item_actual in zip(expected, actual):
            self.assertItemEqual(item_expected, item_actual)


class TestClientManager(TestCase):
    """ClientManager class test framework"""

    default_password_auth = {
        'auth_url': fakes.AUTH_URL,
        'username': fakes.USERNAME,
        'password': fakes.PASSWORD,
        'project_name': fakes.PROJECT_NAME,
    }
    default_token_auth = {
        'auth_url': fakes.AUTH_URL,
        'token': fakes.AUTH_TOKEN,
    }

    def setUp(self):
        super(TestClientManager, self).setUp()
        self.mock = mock.Mock()
        self.requests = self.useFixture(fixture.Fixture())
        # fake v2password token retrieval
        self.stub_auth(json=fakes.TEST_RESPONSE_DICT)
        # fake token and token_endpoint retrieval
        self.stub_auth(json=fakes.TEST_RESPONSE_DICT,
                       url='/'.join([fakes.AUTH_URL, 'v2.0/tokens']))
        # fake v3password token retrieval
        self.stub_auth(json=fakes.TEST_RESPONSE_DICT_V3,
                       url='/'.join([fakes.AUTH_URL, 'v3/auth/tokens']))
        # fake password token retrieval
        self.stub_auth(json=fakes.TEST_RESPONSE_DICT_V3,
                       url='/'.join([fakes.AUTH_URL, 'auth/tokens']))
        # fake password version endpoint discovery
        self.stub_auth(json=fakes.TEST_VERSIONS,
                       url=fakes.AUTH_URL,
                       verb='GET')

        # Mock the auth plugin
        self.auth_mock = mock.Mock()

    def stub_auth(self, json=None, url=None, verb=None, **kwargs):
        subject_token = fakes.AUTH_TOKEN
        base_url = fakes.AUTH_URL
        if json:
            text = jsonutils.dumps(json)
            headers = {
                'X-Subject-Token': subject_token,
                'Content-Type': 'application/json',
            }
        if not url:
            url = '/'.join([base_url, 'tokens'])
        url = url.replace("/?", "?")
        if not verb:
            verb = 'POST'
        self.requests.register_uri(
            verb,
            url,
            headers=headers,
            text=text,
        )

    def _clientmanager_class(self):
        """Allow subclasses to override the ClientManager class"""
        return clientmanager.ClientManager

    def _make_clientmanager(
        self,
        auth_args=None,
        config_args=None,
        identity_api_version=None,
        auth_plugin_name=None,
        auth_required=None,
    ):

        if identity_api_version is None:
            identity_api_version = '2.0'
        if auth_plugin_name is None:
            auth_plugin_name = 'password'

        if auth_plugin_name.endswith('password'):
            auth_dict = copy.deepcopy(self.default_password_auth)
        elif auth_plugin_name.endswith('token'):
            auth_dict = copy.deepcopy(self.default_token_auth)
        else:
            auth_dict = {}

        if auth_args is not None:
            auth_dict = auth_args

        cli_options = defaults.get_defaults()
        cli_options.update({
            'auth_type': auth_plugin_name,
            'auth': auth_dict,
            'interface': fakes.INTERFACE,
            'region_name': fakes.REGION_NAME,
            # 'workflow_api_version': '2',
        })
        if config_args is not None:
            cli_options.update(config_args)

        loader = loading.get_plugin_loader(auth_plugin_name)
        auth_plugin = loader.load_from_options(**auth_dict)
        client_manager = self._clientmanager_class()(
            cli_options=cloud_region.CloudRegion(
                name='t1',
                region_name='1',
                config=cli_options,
                auth_plugin=auth_plugin,
            ),
            api_version={
                'identity': identity_api_version,
            },
        )
        client_manager._auth_required = auth_required is True
        client_manager.setup_auth()
        client_manager.auth_ref

        self.assertEqual(
            auth_plugin_name,
            client_manager.auth_plugin_name,
        )
        return client_manager


class TestShell(TestCase):

    # Full name of the OpenStackShell class to test (cliff.app.App subclass)
    shell_class_name = "osc_lib.shell.OpenStackShell"

    def setUp(self):
        super(TestShell, self).setUp()
        self.shell_class = importutils.import_class(self.shell_class_name)
        self.cmd_patch = mock.patch(self.shell_class_name + ".run_subcommand")
        self.cmd_save = self.cmd_patch.start()
        self.addCleanup(self.cmd_patch.stop)
        self.app = mock.Mock("Test Shell")

    def _assert_initialize_app_arg(self, cmd_options, default_args):
        """Check the args passed to initialize_app()

        The argv argument to initialize_app() is the remainder from parsing
        global options declared in both cliff.app and
        osc_lib.OpenStackShell build_option_parser().  Any global
        options passed on the command line should not be in argv but in
        _shell.options.
        """

        with mock.patch(
                self.shell_class_name + ".initialize_app",
                self.app,
        ):
            _shell = make_shell(shell_class=self.shell_class)
            _cmd = cmd_options + " module list"
            fake_execute(_shell, _cmd)

            self.app.assert_called_with(["module", "list"])
            for k in default_args.keys():
                self.assertEqual(
                    default_args[k],
                    vars(_shell.options)[k],
                    "%s does not match" % k,
                )

    def _assert_cloud_region_arg(self, cmd_options, default_args):
        """Check the args passed to OpenStackConfig.get_one()

        The argparse argument to get_one() is an argparse.Namespace
        object that contains all of the options processed to this point in
        initialize_app().
        """

        cloud = mock.Mock(name="cloudy")
        cloud.config = {}
        self.occ_get_one = mock.Mock(return_value=cloud)
        with mock.patch(
                "openstack.config.loader.OpenStackConfig.get_one",
                self.occ_get_one,
        ):
            _shell = make_shell(shell_class=self.shell_class)
            _cmd = cmd_options + " module list"
            fake_execute(_shell, _cmd)

            self.app.assert_called_with(["module", "list"])
            opts = self.occ_get_one.call_args[1]['argparse']
            for k in default_args.keys():
                self.assertEqual(
                    default_args[k],
                    vars(opts)[k],
                    "%s does not match" % k,
                )

    def _test_options_init_app(self, test_opts):
        """Test options on the command line"""
        for opt in test_opts.keys():
            if not test_opts[opt][1]:
                continue
            key = opt2attr(opt)
            if isinstance(test_opts[opt][0], str):
                cmd = opt + " " + test_opts[opt][0]
            else:
                cmd = opt
            kwargs = {
                key: test_opts[opt][0],
            }
            self._assert_initialize_app_arg(cmd, kwargs)

    def _test_env_init_app(self, test_opts):
        """Test options in the environment"""
        for opt in test_opts.keys():
            if not test_opts[opt][2]:
                continue
            key = opt2attr(opt)
            kwargs = {
                key: test_opts[opt][0],
            }
            env = {
                opt2env(opt): test_opts[opt][0],
            }
            os.environ = env.copy()
            self._assert_initialize_app_arg("", kwargs)

    def _test_options_get_one_cloud(self, test_opts):
        """Test options sent "to openstack.config"""
        for opt in test_opts.keys():
            if not test_opts[opt][1]:
                continue
            key = opt2attr(opt)
            if isinstance(test_opts[opt][0], str):
                cmd = opt + " " + test_opts[opt][0]
            else:
                cmd = opt
            kwargs = {
                key: test_opts[opt][0],
            }
            self._assert_cloud_region_arg(cmd, kwargs)

    def _test_env_get_one_cloud(self, test_opts):
        """Test environment options sent "to openstack.config"""
        for opt in test_opts.keys():
            if not test_opts[opt][2]:
                continue
            key = opt2attr(opt)
            kwargs = {
                key: test_opts[opt][0],
            }
            env = {
                opt2env(opt): test_opts[opt][0],
            }
            os.environ = env.copy()
            self._assert_cloud_region_arg("", kwargs)
