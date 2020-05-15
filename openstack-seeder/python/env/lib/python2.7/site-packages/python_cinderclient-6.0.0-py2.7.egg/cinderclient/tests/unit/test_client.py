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

import json
import logging

import ddt
import fixtures
from keystoneauth1 import adapter
from keystoneauth1 import exceptions as keystone_exception
import mock
from oslo_serialization import jsonutils
import six

from cinderclient import api_versions
import cinderclient.client
from cinderclient import exceptions
import cinderclient.v2.client

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes


@ddt.ddt
class ClientTest(utils.TestCase):

    def test_get_client_class_v2(self):
        output = cinderclient.client.get_client_class('2')
        self.assertEqual(cinderclient.v2.client.Client, output)

    def test_get_client_class_unknown(self):
        self.assertRaises(cinderclient.exceptions.UnsupportedVersion,
                          cinderclient.client.get_client_class, '0')

    @mock.patch.object(cinderclient.client.HTTPClient, '__init__')
    @mock.patch('cinderclient.client.SessionClient')
    def test_construct_http_client_endpoint_url(
            self, session_mock, httpclient_mock):
        os_endpoint = 'http://example.com/'
        httpclient_mock.return_value = None
        cinderclient.client._construct_http_client(
            bypass_url=os_endpoint)
        self.assertTrue(httpclient_mock.called)
        self.assertEqual(os_endpoint,
                         httpclient_mock.call_args[1].get('bypass_url'))
        session_mock.assert_not_called()

    def test_log_req(self):
        self.logger = self.useFixture(
            fixtures.FakeLogger(
                format="%(message)s",
                level=logging.DEBUG,
                nuke_handlers=True
            )
        )

        kwargs = {
            'headers': {"X-Foo": "bar"},
            'data': ('{"auth": {"tenantName": "fakeService",'
                     ' "passwordCredentials": {"username": "fakeUser",'
                     ' "password": "fakePassword"}}}')
        }

        cs = cinderclient.client.HTTPClient("user", None, None,
                                            "http://127.0.0.1:5000")
        cs.http_log_debug = True
        cs.http_log_req('PUT', kwargs)

        output = self.logger.output.split('\n')

        self.assertNotIn("fakePassword", output[1])
        self.assertIn("fakeUser", output[1])

    def test_versions(self):
        v2_url = 'http://fakeurl/v2/tenants'
        unknown_url = 'http://fakeurl/v9/tenants'

        self.assertEqual('2',
                         cinderclient.client.get_volume_api_from_url(v2_url))
        self.assertRaises(cinderclient.exceptions.UnsupportedVersion,
                          cinderclient.client.get_volume_api_from_url,
                          unknown_url)

    @mock.patch('cinderclient.client.SessionClient.get_endpoint')
    @ddt.data(
        ('http://192.168.1.1:8776/v2', 'http://192.168.1.1:8776/'),
        ('http://192.168.1.1:8776/v3/e5526285ebd741b1819393f772f11fc3',
         'http://192.168.1.1:8776/'),
        ('https://192.168.1.1:8080/volumes/v3/'
         'e5526285ebd741b1819393f772f11fc3',
         'https://192.168.1.1:8080/volumes/'),
        ('http://192.168.1.1/volumes/v3/e5526285ebd741b1819393f772f11fc3',
         'http://192.168.1.1/volumes/'),
        ('https://volume.example.com/', 'https://volume.example.com/'))
    @ddt.unpack
    def test_get_base_url(self, url, expected_base, mock_get_endpoint):
        mock_get_endpoint.return_value = url
        cs = cinderclient.client.SessionClient(self, api_version='3.0')
        self.assertEqual(expected_base, cs._get_base_url())

    @mock.patch.object(adapter.Adapter, 'request')
    @mock.patch.object(exceptions, 'from_response')
    def test_sessionclient_request_method(
            self, mock_from_resp, mock_request):
        kwargs = {
            "body": {
                "volume": {
                    "status": "creating",
                    "imageRef": "username",
                    "attach_status": "detached"
                },
                "authenticated": "True"
            }
        }

        resp = {
            "text": {
                "volume": {
                    "status": "creating",
                    "id": "431253c0-e203-4da2-88df-60c756942aaf",
                    "size": 1
                }
            },
            "code": 202
        }

        request_id = "req-f551871a-4950-4225-9b2c-29a14c8f075e"
        mock_response = utils.TestResponse({
            "status_code": 202,
            "text": six.b(json.dumps(resp)),
            "headers": {"x-openstack-request-id": request_id},
        })

        # 'request' method of Adaptor will return 202 response
        mock_request.return_value = mock_response
        session_client = cinderclient.client.SessionClient(session=mock.Mock())
        response, body = session_client.request(mock.sentinel.url,
                                                'POST', **kwargs)
        self.assertIsNotNone(session_client._logger)

        # In this case, from_response method will not get called
        # because response status_code is < 400
        self.assertEqual(202, response.status_code)
        self.assertFalse(mock_from_resp.called)

    @mock.patch.object(adapter.Adapter, 'request')
    def test_sessionclient_request_method_raises_badrequest(
            self, mock_request):
        kwargs = {
            "body": {
                "volume": {
                    "status": "creating",
                    "imageRef": "username",
                    "attach_status": "detached"
                },
                "authenticated": "True"
            }
        }

        resp = {
            "badRequest": {
                "message": "Invalid image identifier or unable to access "
                           "requested image.",
                "code": 400
            }
        }

        mock_response = utils.TestResponse({
            "status_code": 400,
            "text": six.b(json.dumps(resp)),
        })

        # 'request' method of Adaptor will return 400 response
        mock_request.return_value = mock_response
        session_client = cinderclient.client.SessionClient(
            session=mock.Mock())

        # 'from_response' method will raise BadRequest because
        # resp.status_code is 400
        self.assertRaises(exceptions.BadRequest, session_client.request,
                          mock.sentinel.url, 'POST', **kwargs)
        self.assertIsNotNone(session_client._logger)

    @mock.patch.object(adapter.Adapter, 'request')
    def test_sessionclient_request_method_raises_overlimit(
            self, mock_request):
        resp = {
            "overLimitFault": {
                "message": "This request was rate-limited.",
                "code": 413
            }
        }

        mock_response = utils.TestResponse({
            "status_code": 413,
            "text": six.b(json.dumps(resp)),
        })

        # 'request' method of Adaptor will return 413 response
        mock_request.return_value = mock_response
        session_client = cinderclient.client.SessionClient(
            session=mock.Mock())

        self.assertRaises(exceptions.OverLimit, session_client.request,
                          mock.sentinel.url, 'GET')
        self.assertIsNotNone(session_client._logger)

    @mock.patch.object(exceptions, 'from_response')
    def test_keystone_request_raises_auth_failure_exception(
            self, mock_from_resp):

        kwargs = {
            "body": {
                "volume": {
                    "status": "creating",
                    "imageRef": "username",
                    "attach_status": "detached"
                },
                "authenticated": "True"
            }
        }

        with mock.patch.object(adapter.Adapter, 'request',
                               side_effect=
                               keystone_exception.AuthorizationFailure()):
            session_client = cinderclient.client.SessionClient(
                session=mock.Mock())
            self.assertRaises(keystone_exception.AuthorizationFailure,
                              session_client.request,
                              mock.sentinel.url, 'POST', **kwargs)

        # As keystonesession.request method will raise
        # AuthorizationFailure exception, check exceptions.from_response
        # is not getting called.
        self.assertFalse(mock_from_resp.called)


class ClientTestSensitiveInfo(utils.TestCase):
    def test_req_does_not_log_sensitive_info(self):
        self.logger = self.useFixture(
            fixtures.FakeLogger(
                format="%(message)s",
                level=logging.DEBUG,
                nuke_handlers=True
            )
        )

        secret_auth_token = "MY_SECRET_AUTH_TOKEN"
        kwargs = {
            'headers': {"X-Auth-Token": secret_auth_token},
            'data': ('{"auth": {"tenantName": "fakeService",'
                     ' "passwordCredentials": {"username": "fakeUser",'
                     ' "password": "fakePassword"}}}')
        }

        cs = cinderclient.client.HTTPClient("user", None, None,
                                            "http://127.0.0.1:5000")
        cs.http_log_debug = True
        cs.http_log_req('PUT', kwargs)

        output = self.logger.output.split('\n')
        self.assertNotIn(secret_auth_token, output[1])

    def test_resp_does_not_log_sensitive_info(self):
        self.logger = self.useFixture(
            fixtures.FakeLogger(
                format="%(message)s",
                level=logging.DEBUG,
                nuke_handlers=True
            )
        )
        cs = cinderclient.client.HTTPClient("user", None, None,
                                            "http://127.0.0.1:5000")
        resp = mock.Mock()
        resp.status_code = 200
        resp.headers = {
            'x-compute-request-id': 'req-f551871a-4950-4225-9b2c-29a14c8f075e'
        }
        auth_password = "kk4qD6CpKFLyz9JD"
        body = {
            "connection_info": {
                "driver_volume_type": "iscsi",
                "data": {
                    "auth_password": auth_password,
                    "target_discovered": False,
                    "encrypted": False,
                    "qos_specs": None,
                    "target_iqn": ("iqn.2010-10.org.openstack:volume-"
                                   "a2f33dcc-1bb7-45ba-b8fc-5b38179120f8"),
                    "target_portal": "10.0.100.186:3260",
                    "volume_id": "a2f33dcc-1bb7-45ba-b8fc-5b38179120f8",
                    "target_lun": 1,
                    "access_mode": "rw",
                    "auth_username": "s4BfSfZ67Bo2mnpuFWY8",
                    "auth_method": "CHAP"
                }
            }
        }
        resp.text = jsonutils.dumps(body)
        cs.http_log_debug = True
        cs.http_log_resp(resp)

        output = self.logger.output.split('\n')
        self.assertIn('***', output[1], output)
        self.assertNotIn(auth_password, output[1], output)


@ddt.ddt
class GetAPIVersionTestCase(utils.TestCase):

    @mock.patch('cinderclient.client.requests.get')
    def test_get_server_version_v2(self, mock_request):

        mock_response = utils.TestResponse({
            "status_code": 200,
            "text": json.dumps(fakes.fake_request_get_no_v3())
        })

        mock_request.return_value = mock_response

        url = "http://192.168.122.127:8776/v2/e5526285ebd741b1819393f772f11fc3"

        min_version, max_version = cinderclient.client.get_server_version(url)
        self.assertEqual(api_versions.APIVersion('2.0'), min_version)
        self.assertEqual(api_versions.APIVersion('2.0'), max_version)

    @mock.patch('cinderclient.client.requests.get')
    @ddt.data(
        'http://192.168.122.127:8776/v3/e5526285ebd741b1819393f772f11fc3',
        'https://192.168.122.127:8776/v3/e55285ebd741b1819393f772f11fc3',
        'http://192.168.122.127/volumesv3/e5526285ebd741b1819393f772f11fc3'
        )
    def test_get_server_version(self, url, mock_request):
        mock_response = utils.TestResponse({
            "status_code": 200,
            "text": json.dumps(fakes.fake_request_get())
        })

        mock_request.return_value = mock_response

        min_version, max_version = cinderclient.client.get_server_version(url)
        self.assertEqual(min_version, api_versions.APIVersion('3.0'))
        self.assertEqual(max_version, api_versions.APIVersion('3.16'))

    @mock.patch('cinderclient.client.requests.get')
    def test_get_server_version_insecure(self, mock_request):
        mock_response = utils.TestResponse({
            "status_code": 200,
            "text": json.dumps(fakes.fake_request_get_no_v3())
        })

        mock_request.return_value = mock_response

        url = (
            "https://192.168.122.127:8776/v3/e5526285ebd741b1819393f772f11fc3")
        expected_url = "https://192.168.122.127:8776/"

        cinderclient.client.get_server_version(url, True)

        mock_request.assert_called_once_with(expected_url, verify=False)

    @mock.patch('cinderclient.client.requests.get')
    def test_get_server_version_cacert(self, mock_request):
        mock_response = utils.TestResponse({
            "status_code": 200,
            "text": json.dumps(fakes.fake_request_get_no_v3())
        })

        mock_request.return_value = mock_response

        url = (
            "https://192.168.122.127:8776/v3/e5526285ebd741b1819393f772f11fc3")
        expected_url = "https://192.168.122.127:8776/"

        cacert = '/path/to/cert'
        cinderclient.client.get_server_version(url, cacert=cacert)

        mock_request.assert_called_once_with(expected_url, verify=cacert)

    @mock.patch('cinderclient.client.requests.get')
    @ddt.data('3.12', '3.40')
    def test_get_highest_client_server_version(self, version, mock_request):

        mock_response = utils.TestResponse({
            "status_code": 200,
            "text": json.dumps(fakes.fake_request_get())
        })

        mock_request.return_value = mock_response

        url = "http://192.168.122.127:8776/v3/e5526285ebd741b1819393f772f11fc3"

        with mock.patch.object(api_versions, 'MAX_VERSION', version):
            highest = (
                cinderclient.client.get_highest_client_server_version(url))
        expected = version if version == '3.12' else '3.16'
        self.assertEqual(expected, highest)
