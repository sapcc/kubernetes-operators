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
import os

import fixtures
import mock
import requests
from requests_mock.contrib import fixture as requests_mock_fixture
import six
import testtools


REQUEST_ID = ['req-test-request-id']


class TestCase(testtools.TestCase):
    TEST_REQUEST_BASE = {
        'verify': True,
    }

    def setUp(self):
        super(TestCase, self).setUp()
        if (os.environ.get('OS_STDOUT_CAPTURE') == 'True' or
                os.environ.get('OS_STDOUT_CAPTURE') == '1'):
            stdout = self.useFixture(fixtures.StringStream('stdout')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout))
        if (os.environ.get('OS_STDERR_CAPTURE') == 'True' or
                os.environ.get('OS_STDERR_CAPTURE') == '1'):
            stderr = self.useFixture(fixtures.StringStream('stderr')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stderr', stderr))

        # FIXME(eharney) - this should only be needed for shell tests
        self.mock_completion()

    def _assert_request_id(self, obj, count=1):
        self.assertTrue(hasattr(obj, 'request_ids'))
        self.assertEqual(REQUEST_ID * count, obj.request_ids)

    def assert_called_anytime(self, method, url, body=None,
                              partial_body=None):
        return self.shell.cs.assert_called_anytime(method, url, body,
                                                   partial_body)

    def mock_completion(self):
        patcher = mock.patch(
            'cinderclient.base.Manager.write_to_completion_cache')
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch('cinderclient.base.Manager.completion_cache')
        patcher.start()
        self.addCleanup(patcher.stop)


class FixturedTestCase(TestCase):

    client_fixture_class = None
    data_fixture_class = None

    def setUp(self):
        super(FixturedTestCase, self).setUp()

        self.requests = self.useFixture(requests_mock_fixture.Fixture())
        self.data_fixture = None
        self.client_fixture = None
        self.cs = None

        if self.client_fixture_class:
            fix = self.client_fixture_class(self.requests)
            self.client_fixture = self.useFixture(fix)
            self.cs = self.client_fixture.new_client()

        if self.data_fixture_class:
            fix = self.data_fixture_class(self.requests)
            self.data_fixture = self.useFixture(fix)

    def assert_called(self, method, path, body=None):
        self.assertEqual(method, self.requests.last_request.method)
        self.assertEqual(path, self.requests.last_request.path_url)

        if body:
            req_data = self.requests.last_request.body
            if isinstance(req_data, six.binary_type):
                req_data = req_data.decode('utf-8')
            if not isinstance(body, six.string_types):
                # json load if the input body to match against is not a string
                req_data = json.loads(req_data)
            self.assertEqual(body, req_data)


class TestResponse(requests.Response):
    """Class used to wrap requests.Response.

    Provides some convenience to initialize with a dict.
    """

    def __init__(self, data):
        super(TestResponse, self).__init__()
        self._content = None
        self._text = None

        if isinstance(data, dict):
            self.status_code = data.get('status_code', None)
            self.headers = data.get('headers', None)
            self.reason = data.get('reason', '')
            # Fake text and content attributes to streamline Response creation
            text = data.get('text', None)
            self._content = text
            self._text = text
        else:
            self.status_code = data

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._text
