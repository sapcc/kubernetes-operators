# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
#
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
import json as json_
import os

import fixtures
from keystoneauth1 import session as keystone_session
from oslotest import base as test
from requests_mock.contrib import fixture as req_fixture
import six
from six.moves.urllib import parse as urlparse

from designateclient import client
from designateclient.utils import AdapterWithTimeout

_TRUE_VALUES = ('True', 'true', '1', 'yes')


class TestCase(test.BaseTestCase):

    """Test case base class for all unit tests."""

    def setUp(self):
        """Run before each test method to initialize test environment."""

        super(TestCase, self).setUp()
        test_timeout = os.environ.get('OS_TEST_TIMEOUT', 0)
        try:
            test_timeout = int(test_timeout)
        except ValueError:
            # If timeout value is invalid do not set a timeout.
            test_timeout = 0
        if test_timeout > 0:
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

        self.useFixture(fixtures.NestedTempfile())
        self.useFixture(fixtures.TempHomeDir())

        if os.environ.get('OS_STDOUT_CAPTURE') in _TRUE_VALUES:
            stdout = self.useFixture(fixtures.StringStream('stdout')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout))
        if os.environ.get('OS_STDERR_CAPTURE') in _TRUE_VALUES:
            stderr = self.useFixture(fixtures.StringStream('stderr')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stderr', stderr))

        self.log_fixture = self.useFixture(fixtures.FakeLogger())


class APITestCase(TestCase):
    """Test case base class for all unit tests."""

    TEST_URL = "http://127.0.0.1:9001/"
    VERSION = None

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCase, self).setUp()
        self.log_fixture = self.useFixture(fixtures.FakeLogger())

        self.requests = self.useFixture(req_fixture.Fixture())
        self.client = self.get_client()

    def get_base(self, base_url=None):
        if not base_url:
            base_url = '%sv%s' % (self.TEST_URL, self.VERSION)
        return base_url

    def stub_url(self, method, parts=None, base_url=None, json=None, **kwargs):
        base_url = self.get_base(base_url)

        if json:
            kwargs['text'] = json_.dumps(json)
            headers = kwargs.setdefault('headers', {})
            headers['Content-Type'] = 'application/json'

        if parts:
            url = '/'.join([p.strip('/') for p in [base_url] + parts])
        else:
            url = base_url

        url = url.replace("/?", "?")
        self.requests.register_uri(method, url, **kwargs)

    def get_client(self, version=None, session=None):
        version = version or self.VERSION
        session = session or keystone_session.Session()
        adapted = AdapterWithTimeout(
            session=session, endpoint_override=self.get_base())
        return client.Client(version, session=adapted)

    def assertRequestBodyIs(self, body=None, json=None):
        last_request_body = self.requests.last_request.body
        if json:
            val = json_.loads(last_request_body)
            self.assertEqual(json, val)
        elif body:
            self.assertEqual(body, last_request_body)

    def assertQueryStringIs(self, qs=''):
        """Verify the QueryString matches what is expected.

        The qs parameter should be of the format \'foo=bar&abc=xyz\'
        """
        expected = urlparse.parse_qs(qs, keep_blank_values=True)
        parts = urlparse.urlparse(self.requests.last_request.url)
        querystring = urlparse.parse_qs(parts.query, keep_blank_values=True)
        self.assertEqual(expected, querystring)

    def assertQueryStringContains(self, **kwargs):
        """Verify the query string contains the expected parameters.

        This method is used to verify that the query string for the most recent
        request made contains all the parameters provided as ``kwargs``, and
        that the value of each parameter contains the value for the kwarg. If
        the value for the kwarg is an empty string (''), then all that's
        verified is that the parameter is present.

        """
        parts = urlparse.urlparse(self.requests.last_request.url)
        qs = urlparse.parse_qs(parts.query, keep_blank_values=True)

        for k, v in six.iteritems(kwargs):
            self.assertIn(k, qs)
            self.assertIn(v, qs[k])

    def assertRequestHeaderEqual(self, name, val):
        """Verify that the last request made contains a header and its value

        The request must have already been made.
        """
        headers = self.requests.last_request.headers
        self.assertEqual(val, headers.get(name))
