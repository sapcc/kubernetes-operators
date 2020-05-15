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


import ddt
import mock

import manilaclient
from manilaclient import exceptions
from manilaclient.tests.unit import utils
from manilaclient.v2 import client
from oslo_utils import uuidutils


@ddt.ddt
class ClientTest(utils.TestCase):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.catalog = {
            'share': [
                {'region': 'TestRegion', 'publicURL': 'http://1.2.3.4'},
            ],
        }

    def test_adapter_properties(self):
        # sample of properties, there are many more
        retries = 3
        base_url = uuidutils.generate_uuid(dashed=False)

        s = client.session.Session()
        c = client.Client(session=s,
                          api_version=manilaclient.API_MAX_VERSION,
                          service_catalog_url=base_url, retries=retries,
                          input_auth_token='token')

        self.assertEqual(base_url, c.client.endpoint_url)
        self.assertEqual(retries, c.client.retries)

    def test_auth_via_token_invalid(self):
        self.assertRaises(exceptions.ClientException, client.Client,
                          api_version=manilaclient.API_MAX_VERSION,
                          input_auth_token="token")

    def test_auth_via_token_and_session(self):
        s = client.session.Session()
        base_url = uuidutils.generate_uuid(dashed=False)

        c = client.Client(input_auth_token='token',
                          service_catalog_url=base_url, session=s,
                          api_version=manilaclient.API_MAX_VERSION)

        self.assertIsNotNone(c.client)
        self.assertIsNone(c.keystone_client)

    def test_auth_via_token(self):
        base_url = uuidutils.generate_uuid(dashed=False)

        c = client.Client(input_auth_token='token',
                          service_catalog_url=base_url,
                          api_version=manilaclient.API_MAX_VERSION)

        self.assertIsNotNone(c.client)
        self.assertIsNone(c.keystone_client)

    @mock.patch.object(client.Client, '_get_keystone_client', mock.Mock())
    def test_valid_region_name_v1(self):
        self.mock_object(client.httpclient, 'HTTPClient')
        kc = client.Client._get_keystone_client.return_value
        kc.service_catalog = mock.Mock()
        kc.service_catalog.get_endpoints = mock.Mock(return_value=self.catalog)
        c = client.Client(api_version=manilaclient.API_DEPRECATED_VERSION,
                          service_type="share",
                          region_name='TestRegion')
        self.assertTrue(client.Client._get_keystone_client.called)
        kc.service_catalog.get_endpoints.assert_called_with('share')
        client.httpclient.HTTPClient.assert_called_with(
            'http://1.2.3.4',
            mock.ANY,
            'python-manilaclient',
            insecure=False,
            cacert=None,
            timeout=None,
            retries=None,
            http_log_debug=False,
            api_version=manilaclient.API_DEPRECATED_VERSION)
        self.assertIsNotNone(c.client)

    @mock.patch.object(client.Client, '_get_keystone_client', mock.Mock())
    def test_nonexistent_region_name(self):
        kc = client.Client._get_keystone_client.return_value
        kc.service_catalog = mock.Mock()
        kc.service_catalog.get_endpoints = mock.Mock(return_value=self.catalog)
        self.assertRaises(RuntimeError, client.Client,
                          api_version=manilaclient.API_MAX_VERSION,
                          region_name='FakeRegion')
        self.assertTrue(client.Client._get_keystone_client.called)
        kc.service_catalog.get_endpoints.assert_called_with('sharev2')

    @mock.patch.object(client.Client, '_get_keystone_client', mock.Mock())
    def test_regions_with_same_name(self):
        self.mock_object(client.httpclient, 'HTTPClient')
        catalog = {
            'sharev2': [
                {'region': 'FirstRegion', 'publicURL': 'http://1.2.3.4'},
                {'region': 'secondregion', 'publicURL': 'http://1.1.1.1'},
                {'region': 'SecondRegion', 'publicURL': 'http://2.2.2.2'},
            ],
        }
        kc = client.Client._get_keystone_client.return_value
        kc.service_catalog = mock.Mock()
        kc.service_catalog.get_endpoints = mock.Mock(return_value=catalog)
        c = client.Client(api_version=manilaclient.API_MIN_VERSION,
                          service_type='sharev2',
                          region_name='SecondRegion')
        self.assertTrue(client.Client._get_keystone_client.called)
        kc.service_catalog.get_endpoints.assert_called_with('sharev2')
        client.httpclient.HTTPClient.assert_called_with(
            'http://2.2.2.2',
            mock.ANY,
            'python-manilaclient',
            insecure=False,
            cacert=None,
            timeout=None,
            retries=None,
            http_log_debug=False,
            api_version=manilaclient.API_MIN_VERSION)
        self.assertIsNotNone(c.client)

    def _get_client_args(self, **kwargs):
        client_args = {
            'auth_url': 'both',
            'api_version': manilaclient.API_DEPRECATED_VERSION,
            'username': 'fake_username',
            'service_type': 'sharev2',
            'region_name': 'SecondRegion',
            'input_auth_token': None,
            'session': None,
            'service_catalog_url': None,
            'user_id': 'foo_user_id',
            'user_domain_name': 'foo_user_domain_name',
            'user_domain_id': 'foo_user_domain_id',
            'project_name': 'foo_project_name',
            'project_domain_name': 'foo_project_domain_name',
            'project_domain_id': 'foo_project_domain_id',
            'endpoint_type': 'publicUrl',
            'cert': 'foo_cert',
        }
        client_args.update(kwargs)
        return client_args

    @ddt.data(
        {'auth_url': 'only_v3', 'api_key': 'password_backward_compat',
         'endpoint_type': 'publicURL', 'project_id': 'foo_tenant_project_id'},
        {'password': 'renamed_api_key', 'endpoint_type': 'public',
         'tenant_id': 'foo_tenant_project_id'},
    )
    def test_client_init_no_session_no_auth_token_v3(self, kwargs):
        def fake_url_for(version):
            if version == 'v3.0':
                return 'url_v3.0'
            elif version == 'v2.0' and self.auth_url == 'both':
                return 'url_v2.0'
            else:
                return None

        self.mock_object(client.httpclient, 'HTTPClient')
        self.mock_object(client.ks_client, 'Client')
        self.mock_object(client.session.discover, 'Discover')
        self.mock_object(client.session, 'Session')
        client_args = self._get_client_args(**kwargs)
        client_args['api_version'] = manilaclient.API_MIN_VERSION
        self.auth_url = client_args['auth_url']
        catalog = {
            'share': [
                {'region': 'SecondRegion', 'region_id': 'SecondRegion',
                 'url': 'http://4.4.4.4', 'interface': 'public',
                 },
            ],
            'sharev2': [
                {'region': 'FirstRegion', 'interface': 'public',
                 'region_id': 'SecondRegion', 'url': 'http://1.1.1.1'},
                {'region': 'secondregion', 'interface': 'public',
                 'region_id': 'SecondRegion', 'url': 'http://2.2.2.2'},
                {'region': 'SecondRegion', 'interface': 'internal',
                 'region_id': 'SecondRegion', 'url': 'http://3.3.3.1'},
                {'region': 'SecondRegion', 'interface': 'public',
                 'region_id': 'SecondRegion', 'url': 'http://3.3.3.3'},
                {'region': 'SecondRegion', 'interface': 'admin',
                 'region_id': 'SecondRegion', 'url': 'http://3.3.3.2'},
            ],
        }
        client.session.discover.Discover.return_value.url_for.side_effect = (
            fake_url_for)
        client.ks_client.Client.return_value.auth_token.return_value = (
            'fake_token')
        mocked_ks_client = client.ks_client.Client.return_value
        mocked_ks_client.service_catalog.get_endpoints.return_value = catalog

        client.Client(**client_args)

        client.httpclient.HTTPClient.assert_called_with(
            'http://3.3.3.3', mock.ANY, 'python-manilaclient', insecure=False,
            cacert=None, timeout=None, retries=None, http_log_debug=False,
            api_version=manilaclient.API_MIN_VERSION)

        client.ks_client.Client.assert_called_with(
            session=mock.ANY, version=(3, 0), auth_url='url_v3.0',
            username=client_args['username'],
            password=client_args.get('password', client_args.get('api_key')),
            user_id=client_args['user_id'],
            user_domain_name=client_args['user_domain_name'],
            user_domain_id=client_args['user_domain_id'],
            project_id=client_args.get('tenant_id',
                                       client_args.get('project_id')),
            project_name=client_args['project_name'],
            project_domain_name=client_args['project_domain_name'],
            project_domain_id=client_args['project_domain_id'],
            region_name=client_args['region_name'],
        )
        mocked_ks_client.service_catalog.get_endpoints.assert_called_with(
            client_args['service_type'])
        mocked_ks_client.authenticate.assert_called_with()

    @ddt.data(
        {'auth_url': 'only_v2', 'api_key': 'foo', 'project_id': 'bar'},
        {'password': 'foo', 'tenant_id': 'bar'},
    )
    def test_client_init_no_session_no_auth_token_v2(self, kwargs):
        self.mock_object(client.httpclient, 'HTTPClient')
        self.mock_object(client.ks_client, 'Client')
        self.mock_object(client.session.discover, 'Discover')
        self.mock_object(client.session, 'Session')
        client_args = self._get_client_args(**kwargs)
        client_args['api_version'] = manilaclient.API_MIN_VERSION
        self.auth_url = client_args['auth_url']
        catalog = {
            'share': [
                {'region': 'SecondRegion', 'publicUrl': 'http://4.4.4.4'},
            ],
            'sharev2': [
                {'region': 'FirstRegion', 'publicUrl': 'http://1.1.1.1'},
                {'region': 'secondregion', 'publicUrl': 'http://2.2.2.2'},
                {'region': 'SecondRegion', 'internalUrl': 'http://3.3.3.1',
                 'publicUrl': 'http://3.3.3.3', 'adminUrl': 'http://3.3.3.2'},
            ],
        }
        client.session.discover.Discover.return_value.url_for.side_effect = (
            lambda v: 'url_v2.0' if v == 'v2.0' else None)
        client.ks_client.Client.return_value.auth_token.return_value = (
            'fake_token')
        mocked_ks_client = client.ks_client.Client.return_value
        mocked_ks_client.service_catalog.get_endpoints.return_value = catalog

        client.Client(**client_args)

        client.httpclient.HTTPClient.assert_called_with(
            'http://3.3.3.3', mock.ANY, 'python-manilaclient', insecure=False,
            cacert=None, timeout=None, retries=None, http_log_debug=False,
            api_version=manilaclient.API_MIN_VERSION)
        client.ks_client.Client.assert_called_with(
            session=mock.ANY, version=(2, 0), auth_url='url_v2.0',
            username=client_args['username'],
            password=client_args.get('password', client_args.get('api_key')),
            tenant_id=client_args.get('tenant_id',
                                      client_args.get('project_id')),
            tenant_name=client_args['project_name'],
            region_name=client_args['region_name'], cert=client_args['cert'],
            use_keyring=False, force_new_token=False, stale_duration=300)
        mocked_ks_client.service_catalog.get_endpoints.assert_called_with(
            client_args['service_type'])
        mocked_ks_client.authenticate.assert_called_with()

    @mock.patch.object(client.ks_client, 'Client', mock.Mock())
    @mock.patch.object(client.session.discover, 'Discover', mock.Mock())
    @mock.patch.object(client.session, 'Session', mock.Mock())
    def test_client_init_no_session_no_auth_token_endpoint_not_found(self):
        self.mock_object(client.httpclient, 'HTTPClient')
        client_args = self._get_client_args(
            auth_urli='fake_url',
            password='foo_password',
            tenant_id='foo_tenant_id')
        discover = client.session.discover.Discover
        discover.return_value.url_for.return_value = None
        mocked_ks_client = client.ks_client.Client.return_value

        self.assertRaises(
            exceptions.CommandError, client.Client, **client_args)

        self.assertTrue(client.session.Session.called)
        self.assertTrue(client.session.discover.Discover.called)
        self.assertFalse(client.httpclient.HTTPClient.called)
        self.assertFalse(client.ks_client.Client.called)
        self.assertFalse(mocked_ks_client.service_catalog.get_endpoints.called)
        self.assertFalse(mocked_ks_client.authenticate.called)
