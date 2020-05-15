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
import mock
import requests
import uuid

from cinderclient import client
from cinderclient import exceptions
from cinderclient.tests.unit import utils


fake_auth_response = {
    "access": {
        "token": {
            "expires": "2014-11-01T03:32:15-05:00",
            "id": "FAKE_ID",
        },
        "serviceCatalog": [
            {
                "type": "volumev2",
                "endpoints": [
                    {
                        "adminURL": "http://localhost:8776/v2",
                        "region": "RegionOne",
                        "internalURL": "http://localhost:8776/v2",
                        "publicURL": "http://localhost:8776/v2",
                    },
                ],
            },
        ],
    },
}

fake_response = utils.TestResponse({
    "status_code": 200,
    "text": '{"hi": "there"}',
})
mock_request = mock.Mock(return_value=(fake_response))

fake_201_response = utils.TestResponse({
    "status_code": 201,
    "text": json.dumps(fake_auth_response),
})
mock_201_request = mock.Mock(return_value=(fake_201_response))

refused_response = utils.TestResponse({
    "status_code": 400,
    "text": '[Errno 111] Connection refused',
})
refused_mock_request = mock.Mock(return_value=(refused_response))

bad_400_response = utils.TestResponse({
    "status_code": 400,
    "text": '',
})
bad_400_request = mock.Mock(return_value=(bad_400_response))

bad_401_response = utils.TestResponse({
    "status_code": 401,
    "text": '{"error": {"message": "FAILED!", "details": "DETAILS!"}}',
})
bad_401_request = mock.Mock(return_value=(bad_401_response))

bad_413_response = utils.TestResponse({
    "status_code": 413,
    "headers": {"Retry-After": "1", "x-compute-request-id": "1234"},
})
bad_413_request = mock.Mock(return_value=(bad_413_response))

bad_500_response = utils.TestResponse({
    "status_code": 500,
    "text": '{"error": {"message": "FAILED!", "details": "DETAILS!"}}',
})
bad_500_request = mock.Mock(return_value=(bad_500_response))

connection_error_request = mock.Mock(
    side_effect=requests.exceptions.ConnectionError)

timeout_error_request = mock.Mock(
    side_effect=requests.exceptions.Timeout)


def get_client(retries=0, **kwargs):
    cl = client.HTTPClient("username", "password",
                           "project_id", "auth_test", retries=retries,
                           **kwargs)
    return cl


def get_authed_client(retries=0, **kwargs):
    cl = get_client(retries=retries, **kwargs)
    cl.management_url = "http://example.com"
    cl.auth_token = "token"
    cl.get_service_url = mock.Mock(return_value="http://example.com")
    return cl


def get_authed_endpoint_url(retries=0):
    cl = client.HTTPClient("username", "password",
                           "project_id", "auth_test",
                           bypass_url="volume/v100/", retries=retries)
    cl.auth_token = "token"
    return cl


class ClientTest(utils.TestCase):

    def test_get(self):
        cl = get_authed_client()

        @mock.patch.object(requests, "request", mock_request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")
            headers = {"X-Auth-Token": "token",
                       "X-Auth-Project-Id": "project_id",
                       "User-Agent": cl.USER_AGENT,
                       'Accept': 'application/json', }
            mock_request.assert_called_with(
                "GET",
                "http://example.com/hi",
                headers=headers,
                **self.TEST_REQUEST_BASE)
            # Automatic JSON parsing
            self.assertEqual({"hi": "there"}, body)

        test_get_call()

    def test_get_global_id(self):
        global_id = "req-%s" % uuid.uuid4()
        cl = get_authed_client(global_request_id=global_id)

        @mock.patch.object(requests, "request", mock_request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")
            headers = {"X-Auth-Token": "token",
                       "X-Auth-Project-Id": "project_id",
                       "X-OpenStack-Request-ID": global_id,
                       "User-Agent": cl.USER_AGENT,
                       'Accept': 'application/json', }
            mock_request.assert_called_with(
                "GET",
                "http://example.com/hi",
                headers=headers,
                **self.TEST_REQUEST_BASE)
            # Automatic JSON parsing
            self.assertEqual({"hi": "there"}, body)

        test_get_call()

    def test_get_reauth_0_retries(self):
        cl = get_authed_client(retries=0)

        self.requests = [bad_401_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        def reauth():
            cl.management_url = "http://example.com"
            cl.auth_token = "token"

        @mock.patch.object(cl, 'authenticate', reauth)
        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")

        test_get_call()
        self.assertEqual([], self.requests)

    def test_get_retry_500(self):
        cl = get_authed_client(retries=1)

        self.requests = [bad_500_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")

        test_get_call()
        self.assertEqual([], self.requests)

    def test_get_retry_connection_error(self):
        cl = get_authed_client(retries=1)

        self.requests = [connection_error_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")

        test_get_call()
        self.assertEqual([], self.requests)

    def test_rate_limit_overlimit_exception(self):
        cl = get_authed_client(retries=1)

        self.requests = [bad_413_request,
                         bad_413_request,
                         mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")
        self.assertRaises(exceptions.OverLimit, test_get_call)
        self.assertEqual([mock_request], self.requests)

    def test_rate_limit(self):
        cl = get_authed_client(retries=1)

        self.requests = [bad_413_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")
            return resp, body

        resp, body = test_get_call()
        self.assertEqual(200, resp.status_code)
        self.assertEqual([], self.requests)

    def test_retry_limit(self):
        cl = get_authed_client(retries=1)

        self.requests = [bad_500_request, bad_500_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")

        self.assertRaises(exceptions.ClientException, test_get_call)
        self.assertEqual([mock_request], self.requests)

    def test_get_no_retry_400(self):
        cl = get_authed_client(retries=0)

        self.requests = [bad_400_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")

        self.assertRaises(exceptions.BadRequest, test_get_call)
        self.assertEqual([mock_request], self.requests)

    def test_get_retry_400_socket(self):
        cl = get_authed_client(retries=1)

        self.requests = [bad_400_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")

        test_get_call()
        self.assertEqual([], self.requests)

    def test_get_no_auth_url(self):
        client.HTTPClient("username", "password",
                          "project_id", retries=0)

    def test_post(self):
        cl = get_authed_client()

        @mock.patch.object(requests, "request", mock_request)
        def test_post_call():
            cl.post("/hi", body=[1, 2, 3])
            headers = {
                "X-Auth-Token": "token",
                "X-Auth-Project-Id": "project_id",
                "Content-Type": "application/json",
                'Accept': 'application/json',
                "User-Agent": cl.USER_AGENT
            }
            mock_request.assert_called_with(
                "POST",
                "http://example.com/hi",
                headers=headers,
                data='[1, 2, 3]',
                **self.TEST_REQUEST_BASE)

        test_post_call()

    def test_os_endpoint_url(self):
        cl = get_authed_endpoint_url()
        self.assertEqual("volume/v100", cl.bypass_url)
        self.assertEqual("volume/v100", cl.management_url)

    def test_auth_failure(self):
        cl = get_client()

        # response must not have x-server-management-url header
        @mock.patch.object(requests, "request", mock_request)
        def test_auth_call():
            self.assertRaises(exceptions.AuthorizationFailure,
                              cl.authenticate)

        test_auth_call()

    def test_auth_with_keystone_v3(self):
        cl = get_authed_client()
        cl.auth_url = 'http://example.com:5000/v3'

        @mock.patch.object(requests, "request", mock_201_request)
        def test_auth_call():
            cl.authenticate()
            headers = {
                "Content-Type": "application/json",
                'Accept': 'application/json',
                "User-Agent": cl.USER_AGENT
            }
            data = {
                "auth": {
                    "scope": {
                        "project": {
                            "domain": {"name": "Default"},
                            "name": "project_id"
                        }
                    },
                    "identity": {
                        "methods": ["password"],
                        "password": {
                            "user": {"domain": {"name": "Default"},
                                     "password": "password", "name": "username"
                                     }
                        }
                    }
                }
            }

            # Check data, we cannot do it on the call because the JSON
            # dictionary to string can generated different strings.
            actual_data = mock_201_request.call_args[1]['data']
            self.assertDictEqual(data, json.loads(actual_data))

            mock_201_request.assert_called_with(
                "POST",
                "http://example.com:5000/v3/auth/tokens",
                headers=headers,
                allow_redirects=True,
                data=actual_data,
                **self.TEST_REQUEST_BASE)

        test_auth_call()

    def test_get_retry_timeout_error(self):
        cl = get_authed_client(retries=1)

        self.requests = [timeout_error_request, mock_request]

        def request(*args, **kwargs):
            next_request = self.requests.pop(0)
            return next_request(*args, **kwargs)

        @mock.patch.object(requests, "request", request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")

        test_get_call()
        self.assertEqual([], self.requests)
