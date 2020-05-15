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

from keystoneauth1.access import service_catalog
from keystoneauth1 import exceptions as ksa_exceptions
from keystoneauth1.identity import generic as generic_plugin
from keystoneauth1.identity.v3 import k2k
from keystoneauth1 import loading
from keystoneauth1 import noauth
from keystoneauth1 import token_endpoint

from openstack.config import cloud_config
from openstack.config import defaults
from openstack import connection

from osc_lib.api import auth
from osc_lib import clientmanager
from osc_lib import exceptions as exc
from osc_lib.tests import fakes
from osc_lib.tests import utils

AUTH_REF = {'version': 'v2.0'}
AUTH_REF.update(fakes.TEST_RESPONSE_DICT['access'])
SERVICE_CATALOG = service_catalog.ServiceCatalogV2(AUTH_REF)

AUTH_DICT = {
    'auth_url': fakes.AUTH_URL,
    'username': fakes.USERNAME,
    'password': fakes.PASSWORD,
    'project_name': fakes.PROJECT_NAME
}


# This is deferred in api.auth but we need it here...
auth.get_options_list()


class Container(object):
    attr = clientmanager.ClientCache(lambda x: object())
    buggy_attr = clientmanager.ClientCache(lambda x: x.foo)

    def __init__(self):
        pass


class TestClientCache(utils.TestCase):

    def test_singleton(self):
        # NOTE(dtroyer): Verify that the ClientCache descriptor only invokes
        # the factory one time and always returns the same value after that.
        c = Container()
        self.assertEqual(c.attr, c.attr)

    def test_attribute_error_propagates(self):
        c = Container()
        err = self.assertRaises(exc.PluginAttributeError,
                                getattr, c, 'buggy_attr')
        self.assertNotIsInstance(err, AttributeError)
        self.assertEqual("'Container' object has no attribute 'foo'", str(err))


class TestClientManager(utils.TestClientManager):

    def test_client_manager_none(self):
        none_auth = {
            'endpoint': fakes.AUTH_URL,
        }
        client_manager = self._make_clientmanager(
            auth_args=none_auth,
            auth_plugin_name='none',
        )

        self.assertEqual(
            fakes.AUTH_URL,
            client_manager._cli_options.config['auth']['endpoint'],
        )
        self.assertIsInstance(
            client_manager.auth,
            noauth.NoAuth,
        )
        # Check that the endpoint option works as the override
        self.assertEqual(
            fakes.AUTH_URL,
            client_manager.get_endpoint_for_service_type('baremetal'),
        )

    def test_client_manager_admin_token(self):
        token_auth = {
            'endpoint': fakes.AUTH_URL,
            'token': fakes.AUTH_TOKEN,
        }
        client_manager = self._make_clientmanager(
            auth_args=token_auth,
            auth_plugin_name='admin_token',
        )

        self.assertEqual(
            fakes.AUTH_URL,
            client_manager._cli_options.config['auth']['endpoint'],
        )
        self.assertEqual(
            fakes.AUTH_TOKEN,
            client_manager.auth.get_token(None),
        )
        self.assertIsInstance(
            client_manager.auth,
            token_endpoint.Token,
        )
        # NOTE(dtroyer): This is intentionally not assertFalse() as the return
        #                value from is_service_available() may be == None
        self.assertNotEqual(
            False,
            client_manager.is_service_available('network'),
        )

    def test_client_manager_password(self):
        client_manager = self._make_clientmanager(
            auth_required=True,
        )

        self.assertEqual(
            fakes.AUTH_URL,
            client_manager._cli_options.config['auth']['auth_url'],
        )
        self.assertEqual(
            fakes.USERNAME,
            client_manager._cli_options.config['auth']['username'],
        )
        self.assertEqual(
            fakes.PASSWORD,
            client_manager._cli_options.config['auth']['password'],
        )
        self.assertIsInstance(
            client_manager.auth,
            generic_plugin.Password,
        )
        self.assertTrue(client_manager.verify)
        self.assertIsNone(client_manager.cert)

        # These need to stick around until the old-style clients are gone
        self.assertEqual(
            AUTH_REF.pop('version'),
            client_manager.auth_ref.version,
        )
        self.assertEqual(
            fakes.to_unicode_dict(AUTH_REF),
            client_manager.auth_ref._data['access'],
        )
        self.assertEqual(
            dir(SERVICE_CATALOG),
            dir(client_manager.auth_ref.service_catalog),
        )
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify(self):
        client_manager = self._make_clientmanager(
            auth_required=True,
        )

        self.assertTrue(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_ca(self):
        config_args = {
            'cacert': 'cafile',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        # Test that client_manager.verify is Requests-compatible,
        # i.e. it contains the value of cafile here
        self.assertTrue(client_manager.verify)
        self.assertEqual('cafile', client_manager.verify)
        self.assertEqual('cafile', client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_false(self):
        config_args = {
            'verify': False,
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        self.assertFalse(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_insecure(self):
        config_args = {
            'insecure': True,
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        self.assertFalse(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_verify_insecure_ca(self):
        config_args = {
            'insecure': True,
            'cacert': 'cafile',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
            auth_required=True,
        )

        # insecure overrides cacert
        self.assertFalse(client_manager.verify)
        self.assertIsNone(client_manager.cacert)
        self.assertTrue(client_manager.is_service_available('network'))

    def test_client_manager_password_client_cert(self):
        config_args = {
            'cert': 'cert',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
        )

        self.assertEqual('cert', client_manager.cert)

    def test_client_manager_password_client_key(self):
        config_args = {
            'cert': 'cert',
            'key': 'key',
        }
        client_manager = self._make_clientmanager(
            config_args=config_args,
        )

        self.assertEqual(('cert', 'key'), client_manager.cert)

    def test_client_manager_select_auth_plugin_password(self):
        # test password auth
        auth_args = {
            'auth_url': fakes.AUTH_URL,
            'username': fakes.USERNAME,
            'password': fakes.PASSWORD,
            'tenant_name': fakes.PROJECT_NAME,
        }
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='2.0',
            auth_plugin_name='v2password',
        )

        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.update({
            'user_domain_name': 'default',
            'project_domain_name': 'default',
        })
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
            auth_plugin_name='v3password',
        )

        # Use v2.0 auth args
        auth_args = {
            'auth_url': fakes.AUTH_URL,
            'username': fakes.USERNAME,
            'password': fakes.PASSWORD,
            'tenant_name': fakes.PROJECT_NAME,
        }
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='2.0',
        )

        # Use v3 auth args
        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.update({
            'user_domain_name': 'default',
            'project_domain_name': 'default',
        })
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
        )

        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.pop('username')
        auth_args.update({
            'user_id': fakes.USER_ID,
        })
        self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
        )

    def test_client_manager_select_auth_plugin_token(self):
        # test token auth
        self._make_clientmanager(
            # auth_args=auth_args,
            identity_api_version='2.0',
            auth_plugin_name='v2token',
        )
        self._make_clientmanager(
            # auth_args=auth_args,
            identity_api_version='3',
            auth_plugin_name='v3token',
        )
        self._make_clientmanager(
            # auth_args=auth_args,
            identity_api_version='x',
            auth_plugin_name='token',
        )

    def test_client_manager_select_auth_plugin_failure(self):
        self.assertRaises(
            ksa_exceptions.NoMatchingPlugin,
            self._make_clientmanager,
            identity_api_version='3',
            auth_plugin_name='bad_plugin',
        )

    @mock.patch('osc_lib.api.auth.check_valid_authentication_options')
    def test_client_manager_auth_setup_once(self, check_authn_options_func):
        loader = loading.get_plugin_loader('password')
        auth_plugin = loader.load_from_options(**AUTH_DICT)
        cli_options = defaults.get_defaults()
        cli_options.update({
            'auth_type': 'password',
            'auth': AUTH_DICT,
            'interface': fakes.INTERFACE,
            'region_name': fakes.REGION_NAME,
        })
        client_manager = self._clientmanager_class()(
            cli_options=cloud_config.CloudConfig(
                name='t1',
                region='1',
                config=cli_options,
                auth_plugin=auth_plugin,
            ),
            api_version={
                'identity': '2.0',
            },
        )
        self.assertFalse(client_manager._auth_setup_completed)
        client_manager.setup_auth()
        self.assertTrue(check_authn_options_func.called)
        self.assertTrue(client_manager._auth_setup_completed)

        # now make sure we don't do auth setup the second time around
        # by checking whether check_valid_auth_options() gets called again
        check_authn_options_func.reset_mock()
        client_manager.auth_ref
        check_authn_options_func.assert_not_called()

    def test_client_manager_endpoint_disabled(self):
        auth_args = copy.deepcopy(self.default_password_auth)
        auth_args.update({
            'user_domain_name': 'default',
            'project_domain_name': 'default',
        })
        # v3 fake doesn't have network endpoint
        client_manager = self._make_clientmanager(
            auth_args=auth_args,
            identity_api_version='3',
            auth_plugin_name='v3password',
        )

        self.assertFalse(client_manager.is_service_available('network'))

    def test_client_manager_k2k_auth_setup(self):
        loader = loading.get_plugin_loader('password')
        auth_plugin = loader.load_from_options(**AUTH_DICT)
        cli_options = defaults.get_defaults()
        cli_options.update({
            'auth_type': 'password',
            'auth': AUTH_DICT,
            'interface': fakes.INTERFACE,
            'region_name': fakes.REGION_NAME,
            'service_provider': fakes.SERVICE_PROVIDER_ID,
            'remote_project_id': fakes.PROJECT_ID
        })
        client_manager = self._clientmanager_class()(
            cli_options=cloud_config.CloudConfig(
                name='t1',
                region='1',
                config=cli_options,
                auth_plugin=auth_plugin,
            ),
            api_version={
                'identity': '3',
            },
        )

        self.assertFalse(client_manager._auth_setup_completed)
        client_manager.setup_auth()
        # Note(knikolla): Make sure that the auth object is of the correct
        # type and that the service_provider is correctly set.
        self.assertIsInstance(client_manager.auth, k2k.Keystone2Keystone)
        self.assertEqual(client_manager.auth._sp_id, fakes.SERVICE_PROVIDER_ID)
        self.assertEqual(client_manager.auth.project_id, fakes.PROJECT_ID)
        self.assertTrue(client_manager._auth_setup_completed)

    def test_client_manager_none_auth(self):
        # test token auth
        client_manager = self._make_clientmanager(
            auth_args={},
            auth_plugin_name='none',
        )
        self.assertIsNone(
            client_manager.get_endpoint_for_service_type('compute'))

    def test_client_manager_endpoint_override(self):
        # test token auth
        client_manager = self._make_clientmanager(
            auth_args={},
            config_args={'compute_endpoint_override': 'http://example.com',
                         'foo_bar_endpoint_override': 'http://example2.com'},
            auth_plugin_name='none',
        )
        self.assertEqual(
            'http://example.com',
            client_manager.get_endpoint_for_service_type('compute'))
        self.assertEqual(
            'http://example2.com',
            client_manager.get_endpoint_for_service_type('foo-bar'))
        self.assertTrue(client_manager.is_service_available('compute'))


class TestClientManagerSDK(utils.TestClientManager):

    def test_client_manager_connection(self):
        client_manager = self._make_clientmanager(
            auth_required=True,
        )

        self.assertIsInstance(
            client_manager.sdk_connection,
            connection.Connection,
        )
