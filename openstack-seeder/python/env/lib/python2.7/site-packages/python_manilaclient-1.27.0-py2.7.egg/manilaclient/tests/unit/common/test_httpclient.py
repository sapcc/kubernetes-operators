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

import ddt
import mock
import re
import requests

import manilaclient
from manilaclient.common import httpclient
from manilaclient import exceptions
from manilaclient.tests.unit import utils

fake_user_agent = "fake"

fake_response = utils.TestResponse({
    "status_code": 200,
    "text": '{"hi": "there"}',
})
mock_request = mock.Mock(return_value=(fake_response))

bad_400_response = utils.TestResponse({
    "status_code": 400,
    "text": '{"error": {"message": "n/a", "details": "Terrible!"}}',
})
bad_400_request = mock.Mock(return_value=(bad_400_response))

bad_401_response = utils.TestResponse({
    "status_code": 401,
    "text": '{"error": {"message": "FAILED!", "details": "DETAILS!"}}',
})
bad_401_request = mock.Mock(return_value=(bad_401_response))

bad_500_response = utils.TestResponse({
    "status_code": 500,
    "text": '{"error": {"message": "FAILED!", "details": "DETAILS!"}}',
})
bad_500_request = mock.Mock(return_value=(bad_500_response))

retry_after_response = utils.TestResponse({
    "status_code": 413,
    "text": '',
    "headers": {
        "retry-after": "5"
    },
})
retry_after_mock_request = mock.Mock(return_value=retry_after_response)

retry_after_no_headers_response = utils.TestResponse({
    "status_code": 413,
    "text": '',
})
retry_after_no_headers_mock_request = mock.Mock(
    return_value=retry_after_no_headers_response)

retry_after_non_supporting_response = utils.TestResponse({
    "status_code": 403,
    "text": '',
    "headers": {
        "retry-after": "5"
    },
})
retry_after_non_supporting_mock_request = mock.Mock(
    return_value=retry_after_non_supporting_response)


def get_authed_client(endpoint_url="http://example.com", retries=0):
    cl = httpclient.HTTPClient(endpoint_url, "token", fake_user_agent,
                               retries=retries, http_log_debug=True,
                               api_version=manilaclient.API_MAX_VERSION)
    return cl


@ddt.ddt
class ClientTest(utils.TestCase):

    def setUp(self):
        super(ClientTest, self).setUp()
        self.max_version = manilaclient.API_MAX_VERSION
        self.max_version_str = self.max_version.get_string()

    @ddt.data(
        "http://manila.example.com/v2/b2d18606-2673-4965-885a-4f5a8b955b9b",
        "http://manila.example.com/v1",
        "http://manila.example.com/share/v2.22/",
        "http://manila.example.com/share/v1/"
        "b2d18606-2673-4965-885a-4f5a8b955b9b",
        "http://10.10.10.10:3366/v1",
        "http://10.10.10.10:3366/v2/b2d18606-2673-4965-885a-4f5a8b955b9b",
        "http://manila.example.com:3366/v1.1/",
        "http://manila.example.com:3366/v2/"
        "b2d18606-2673-4965-885a-4f5a8b955b9b")
    def test_get(self, endpoint_url):
        cl = get_authed_client(endpoint_url)

        @mock.patch.object(requests, "request", mock_request)
        @mock.patch('time.time', mock.Mock(return_value=1234))
        def test_get_call():
            resp, body = cl.get("/hi")
            headers = {
                "X-Auth-Token": "token",
                "User-Agent": fake_user_agent,
                cl.API_VERSION_HEADER: self.max_version_str,
                'Accept': 'application/json',
            }
            mock_request.assert_called_with(
                "GET",
                endpoint_url + "/hi",
                headers=headers,
                **self.TEST_REQUEST_BASE)
            # Automatic JSON parsing
            self.assertEqual(body, {"hi": "there"})
            self.assertEqual(re.split('/v[0-9]+[\.0-9]*',
                                      endpoint_url)[0] + "/", cl.base_url)

        test_get_call()

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
        self.assertEqual(self.requests, [])

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
        self.assertEqual(self.requests, [mock_request])

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
        self.assertEqual(self.requests, [mock_request])

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
        self.assertEqual(self.requests, [])

    def test_get_with_retries_none(self):
        cl = get_authed_client(retries=None)

        @mock.patch.object(requests, "request", bad_401_request)
        def test_get_call():
            resp, body = cl.get("/hi")

        self.assertRaises(exceptions.Unauthorized, test_get_call)

    @ddt.data(
        "http://manila.example.com/v1/b2d18606-2673-4965-885a-4f5a8b955b9b",
        "http://manila.example.com/v1",
        "http://manila.example.com/share/v2.1/",
        "http://manila.example.com/share/v1/"
        "b2d18606-2673-4965-885a-4f5a8b955b9b",
        "http://10.10.10.10:3366/v1.1",
        "http://10.10.10.10:3366/v2/b2d18606-2673-4965-885a-4f5a8b955b9b",
        "http://manila.example.com:3366/v2.22/",
        "http://manila.example.com:3366/v1/"
        "b2d18606-2673-4965-885a-4f5a8b955b9b")
    def test_post(self, endpoint_url):
        cl = get_authed_client(endpoint_url)

        @mock.patch.object(requests, "request", mock_request)
        def test_post_call():
            cl.post("/hi", body=[1, 2, 3])
            headers = {
                "X-Auth-Token": "token",
                "Content-Type": "application/json",
                'Accept': 'application/json',
                "X-Openstack-Manila-Api-Version": self.max_version_str,
                "User-Agent": fake_user_agent
            }
            mock_request.assert_called_with(
                "POST",
                endpoint_url + "/hi",
                headers=headers,
                data='[1, 2, 3]',
                **self.TEST_REQUEST_BASE)
            self.assertEqual(re.split('/v[0-9]+[\.0-9]*',
                                      endpoint_url)[0] + "/", cl.base_url)

        test_post_call()
