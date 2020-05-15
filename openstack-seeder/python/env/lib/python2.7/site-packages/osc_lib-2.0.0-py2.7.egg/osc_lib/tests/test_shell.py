#   Copyright 2012-2013 OpenStack Foundation
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

import copy
import mock
import os
import sys
import testtools

from osc_lib import shell
from osc_lib.tests import utils

from openstack.config import loader as config   # noqa

DEFAULT_AUTH_URL = "http://127.0.0.1:5000/v2.0/"
DEFAULT_PROJECT_ID = "xxxx-yyyy-zzzz"
DEFAULT_PROJECT_NAME = "project"
DEFAULT_DOMAIN_ID = "aaaa-bbbb-cccc"
DEFAULT_DOMAIN_NAME = "default"
DEFAULT_USER_DOMAIN_ID = "aaaa-bbbb-cccc"
DEFAULT_USER_DOMAIN_NAME = "domain"
DEFAULT_PROJECT_DOMAIN_ID = "aaaa-bbbb-cccc"
DEFAULT_PROJECT_DOMAIN_NAME = "domain"
DEFAULT_USERNAME = "username"
DEFAULT_PASSWORD = "password"

DEFAULT_CLOUD = "altocumulus"
DEFAULT_REGION_NAME = "ZZ9_Plural_Z_Alpha"
DEFAULT_TOKEN = "token"
DEFAULT_SERVICE_URL = "http://127.0.0.1:8771/v3.0/"
DEFAULT_AUTH_PLUGIN = "v2password"
DEFAULT_INTERFACE = "internal"

DEFAULT_COMPUTE_API_VERSION = ""
DEFAULT_IDENTITY_API_VERSION = ""
DEFAULT_IMAGE_API_VERSION = ""
DEFAULT_VOLUME_API_VERSION = ""
DEFAULT_NETWORK_API_VERSION = ""

LIB_COMPUTE_API_VERSION = ""
LIB_IDENTITY_API_VERSION = ""
LIB_IMAGE_API_VERSION = ""
LIB_VOLUME_API_VERSION = ""
LIB_NETWORK_API_VERSION = ""

CLOUD_1 = {
    'clouds': {
        'scc': {
            'auth': {
                'auth_url': DEFAULT_AUTH_URL,
                'project_name': DEFAULT_PROJECT_NAME,
                'username': 'zaphod',
            },
            'region_name': 'occ-cloud,krikkit',
            'donut': 'glazed',
            'interface': 'public',
        }
    }
}

CLOUD_2 = {
    'clouds': {
        'megacloud': {
            'cloud': 'megadodo',
            'auth': {
                'project_name': 'heart-o-gold',
                'username': 'zaphod',
            },
            'region_name': 'occ-cloud,krikkit,occ-env',
            'log_file': '/tmp/test_log_file',
            'log_level': 'debug',
            'cert': 'mycert',
            'key': 'mickey',
        }
    }
}

PUBLIC_1 = {
    'public-clouds': {
        'megadodo': {
            'auth': {
                'auth_url': DEFAULT_AUTH_URL,
                'project_name': DEFAULT_PROJECT_NAME,
            },
            'region_name': 'occ-public',
            'donut': 'cake',
        }
    }
}


# The option table values is a tuple of (<value>, <test-opt>, <test-env>)
# where <value> is the test value to use, <test-opt> is True if this option
# should be tested as a CLI option and <test-env> is True of this option
# should be tested as an environment variable.

# Global options that should be parsed before shell.initialize_app() is called
global_options = {
    '--os-cloud': (DEFAULT_CLOUD, True, True),
    '--os-region-name': (DEFAULT_REGION_NAME, True, True),
    '--os-default-domain': (DEFAULT_DOMAIN_NAME, True, True),
    '--os-cacert': ('/dev/null', True, True),
    '--timing': (True, True, False),
    '--os-interface': (DEFAULT_INTERFACE, True, True)
}
if shell.osprofiler_profiler:
    global_options['--os-profile'] = ('SECRET_KEY', True, True)


class TestShellArgV(utils.TestShell):
    """Test the deferred help flag"""

    def setUp(self):
        super(TestShellArgV, self).setUp()

    def test_shell_argv(self):
        """Test argv decoding

        Python 2 does nothing with argv while Python 3 decodes it into
        Unicode before we ever see it.  We manually decode when running
        under Python 2 so verify that we get the right argv types.

        Use the argv supplied by the test runner so we get actual Python
        runtime behaviour; we only need to check the type of argv[0]
        which will alwyas be present.
        """

        with mock.patch(
                "osc_lib.shell.OpenStackShell.run",
                self.app,
        ):
            # Ensure type gets through unmolested through shell.main()
            argv = sys.argv
            shell.main(sys.argv)
            self.assertEqual(type(argv[0]), type(self.app.call_args[0][0][0]))

            # When shell.main() gets sys.argv itself it should be decoded
            shell.main()
            self.assertEqual(type(u'x'), type(self.app.call_args[0][0][0]))


class TestShellHelp(utils.TestShell):
    """Test the deferred help flag"""

    def setUp(self):
        super(TestShellHelp, self).setUp()
        self.useFixture(utils.EnvFixture())

    @testtools.skip("skip until bug 1444983 is resolved")
    def test_help_options(self):
        flag = "-h list server"
        kwargs = {
            "deferred_help": True,
        }
        with mock.patch(self.app_patch + ".initialize_app", self.app):
            _shell, _cmd = utils.make_shell(), flag
            utils.fake_execute(_shell, _cmd)

            self.assertEqual(
                kwargs["deferred_help"],
                _shell.options.deferred_help,
            )


class TestShellOptions(utils.TestShell):
    """Test the option handling by argparse and openstack.config.loader

    This covers getting the CLI options through the initial processing
    and validates the arguments to initialize_app() and occ_get_one()
    """

    def setUp(self):
        super(TestShellOptions, self).setUp()
        self.useFixture(utils.EnvFixture())

    def test_empty_auth(self):
        os.environ = {}
        self._assert_initialize_app_arg("", {})
        self._assert_cloud_region_arg("", {})

    def test_no_options(self):
        os.environ = {}
        self._assert_initialize_app_arg("", {})
        self._assert_cloud_region_arg("", {})

    def test_global_options(self):
        self._test_options_init_app(global_options)
        self._test_options_get_one_cloud(global_options)

    def test_global_env(self):
        self._test_env_init_app(global_options)
        self._test_env_get_one_cloud(global_options)


class TestShellCli(utils.TestShell):
    """Test handling of specific global options

    _shell.options is the parsed command line from argparse
    _shell.client_manager.* are the values actually used

    """

    def setUp(self):
        super(TestShellCli, self).setUp()
        env = {}
        self.useFixture(utils.EnvFixture(env.copy()))

    def test_shell_args_no_options(self):
        _shell = utils.make_shell()
        with mock.patch(
                "osc_lib.shell.OpenStackShell.initialize_app",
                self.app,
        ):
            utils.fake_execute(_shell, "list user")
            self.app.assert_called_with(["list", "user"])

    def test_shell_args_tls_options(self):
        """Test the TLS verify and CA cert file options"""
        _shell = utils.make_shell()

        # Default
        utils.fake_execute(_shell, "module list")
        self.assertIsNone(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertIsNone(_shell.options.cacert)
        self.assertTrue(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

        # --verify
        utils.fake_execute(_shell, "--verify module list")
        self.assertTrue(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertIsNone(_shell.options.cacert)
        self.assertTrue(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

        # --insecure
        utils.fake_execute(_shell, "--insecure module list")
        self.assertIsNone(_shell.options.verify)
        self.assertTrue(_shell.options.insecure)
        self.assertIsNone(_shell.options.cacert)
        self.assertFalse(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

        # --os-cacert
        utils.fake_execute(_shell, "--os-cacert foo module list")
        self.assertIsNone(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertEqual('foo', _shell.options.cacert)
        self.assertEqual('foo', _shell.client_manager.verify)
        self.assertEqual('foo', _shell.client_manager.cacert)

        # --os-cacert and --verify
        utils.fake_execute(_shell, "--os-cacert foo --verify module list")
        self.assertTrue(_shell.options.verify)
        self.assertIsNone(_shell.options.insecure)
        self.assertEqual('foo', _shell.options.cacert)
        self.assertEqual('foo', _shell.client_manager.verify)
        self.assertEqual('foo', _shell.client_manager.cacert)

        # --os-cacert and --insecure
        # NOTE(dtroyer): Per bug https://bugs.launchpad.net/bugs/1447784
        #                in this combination --insecure now overrides any
        #                --os-cacert setting, where before --insecure
        #                was ignored if --os-cacert was set.
        utils.fake_execute(_shell, "--os-cacert foo --insecure module list")
        self.assertIsNone(_shell.options.verify)
        self.assertTrue(_shell.options.insecure)
        self.assertEqual('foo', _shell.options.cacert)
        self.assertFalse(_shell.client_manager.verify)
        self.assertIsNone(_shell.client_manager.cacert)

    def test_shell_args_cert_options(self):
        """Test client cert options"""
        _shell = utils.make_shell()

        # Default
        utils.fake_execute(_shell, "module list")
        self.assertEqual('', _shell.options.cert)
        self.assertEqual('', _shell.options.key)
        self.assertIsNone(_shell.client_manager.cert)

        # --os-cert
        utils.fake_execute(_shell, "--os-cert mycert module list")
        self.assertEqual('mycert', _shell.options.cert)
        self.assertEqual('', _shell.options.key)
        self.assertEqual('mycert', _shell.client_manager.cert)

        # --os-key
        utils.fake_execute(_shell, "--os-key mickey module list")
        self.assertEqual('', _shell.options.cert)
        self.assertEqual('mickey', _shell.options.key)
        self.assertIsNone(_shell.client_manager.cert)

        # --os-cert and --os-key
        utils.fake_execute(
            _shell,
            "--os-cert mycert --os-key mickey module list"
        )
        self.assertEqual('mycert', _shell.options.cert)
        self.assertEqual('mickey', _shell.options.key)
        self.assertEqual(('mycert', 'mickey'), _shell.client_manager.cert)

    @mock.patch("openstack.config.loader.OpenStackConfig._load_config_file")
    def test_shell_args_cloud_no_vendor(self, config_mock):
        """Test cloud config options without the vendor file"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_1))
        _shell = utils.make_shell()

        utils.fake_execute(
            _shell,
            "--os-cloud scc module list",
        )
        self.assertEqual(
            'scc',
            _shell.cloud.name,
        )

        # These come from clouds.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            DEFAULT_PROJECT_NAME,
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.client_manager.region_name,
        )
        self.assertEqual(
            'glazed',
            _shell.cloud.config['donut'],
        )
        self.assertEqual(
            'public',
            _shell.cloud.config['interface'],
        )

        self.assertIsNone(_shell.cloud.config['cert'])
        self.assertIsNone(_shell.cloud.config['key'])
        self.assertIsNone(_shell.client_manager.cert)

    @mock.patch("openstack.config.loader.OpenStackConfig._load_vendor_file")
    @mock.patch("openstack.config.loader.OpenStackConfig._load_config_file")
    def test_shell_args_cloud_public(self, config_mock, public_mock):
        """Test cloud config options with the vendor file"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        public_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = utils.make_shell()

        utils.fake_execute(
            _shell,
            "--os-cloud megacloud module list",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'occ-cloud',
            _shell.client_manager.region_name,
        )

        self.assertEqual('mycert', _shell.cloud.config['cert'])
        self.assertEqual('mickey', _shell.cloud.config['key'])
        self.assertEqual(('mycert', 'mickey'), _shell.client_manager.cert)

    @mock.patch("openstack.config.loader.OpenStackConfig._load_vendor_file")
    @mock.patch("openstack.config.loader.OpenStackConfig._load_config_file")
    def test_shell_args_precedence(self, config_mock, vendor_mock):
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = utils.make_shell()

        # Test command option overriding config file value
        utils.fake_execute(
            _shell,
            "--os-cloud megacloud --os-region-name krikkit module list",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )
        self.assertEqual(
            'krikkit',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'krikkit',
            _shell.client_manager.region_name,
        )


class TestShellCliPrecedence(utils.TestShell):
    """Test option precedencr order"""

    def setUp(self):
        super(TestShellCliPrecedence, self).setUp()
        env = {
            'OS_CLOUD': 'megacloud',
            'OS_REGION_NAME': 'occ-env',
        }
        self.useFixture(utils.EnvFixture(env.copy()))

    @mock.patch("openstack.config.loader.OpenStackConfig._load_vendor_file")
    @mock.patch("openstack.config.loader.OpenStackConfig._load_config_file")
    def test_shell_args_precedence_1(self, config_mock, vendor_mock):
        """Test environment overriding occ"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = utils.make_shell()

        # Test env var
        utils.fake_execute(
            _shell,
            "module list",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )

        # These come from the environment
        self.assertEqual(
            'occ-env',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'occ-env',
            _shell.client_manager.region_name,
        )

    @mock.patch("openstack.config.loader.OpenStackConfig._load_vendor_file")
    @mock.patch("openstack.config.loader.OpenStackConfig._load_config_file")
    def test_shell_args_precedence_2(self, config_mock, vendor_mock):
        """Test command line overriding environment and occ"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_2))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = utils.make_shell()

        # Test command option overriding config file value
        utils.fake_execute(
            _shell,
            "--os-region-name krikkit list user",
        )
        self.assertEqual(
            'megacloud',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'cake',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            'heart-o-gold',
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )

        # These come from the command line
        self.assertEqual(
            'krikkit',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'krikkit',
            _shell.client_manager.region_name,
        )

    @mock.patch("openstack.config.loader.OpenStackConfig._load_vendor_file")
    @mock.patch("openstack.config.loader.OpenStackConfig._load_config_file")
    def test_shell_args_precedence_3(self, config_mock, vendor_mock):
        """Test command line overriding environment and occ"""
        config_mock.return_value = ('file.yaml', copy.deepcopy(CLOUD_1))
        vendor_mock.return_value = ('file.yaml', copy.deepcopy(PUBLIC_1))
        _shell = utils.make_shell()

        # Test command option overriding config file value
        utils.fake_execute(
            _shell,
            "--os-cloud scc --os-region-name krikkit list user",
        )
        self.assertEqual(
            'scc',
            _shell.cloud.name,
        )

        # These come from clouds-public.yaml
        self.assertEqual(
            DEFAULT_AUTH_URL,
            _shell.cloud.config['auth']['auth_url'],
        )
        self.assertEqual(
            'glazed',
            _shell.cloud.config['donut'],
        )

        # These come from clouds.yaml
        self.assertEqual(
            DEFAULT_PROJECT_NAME,
            _shell.cloud.config['auth']['project_name'],
        )
        self.assertEqual(
            'zaphod',
            _shell.cloud.config['auth']['username'],
        )

        # These come from the command line
        self.assertEqual(
            'krikkit',
            _shell.cloud.config['region_name'],
        )
        self.assertEqual(
            'krikkit',
            _shell.client_manager.region_name,
        )
