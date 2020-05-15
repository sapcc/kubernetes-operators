# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Author: Federico Ceratto <federico.ceratto@hp.com>
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

from keystoneauth1.identity import generic
from keystoneauth1 import session as keystone_session
from mock import Mock

from designateclient.tests import v2
from designateclient.v2.client import Client


def create_session(timeout=None):
    auth = generic.Password(auth_url='', username='', password='',
                            tenant_name='')
    return keystone_session.Session(auth=auth, timeout=timeout)


class TestTimeout(v2.APIV2TestCase, v2.CrudMixin):

    def setUp(self):
        super(TestTimeout, self).setUp()

        # Mock methods in KeyStone's Session
        self._saved_methods = (
            keystone_session.Session.get_auth_headers,
            keystone_session.Session.get_endpoint,
            keystone_session.Session._send_request,
        )

        resp = Mock()
        resp.text = ''
        resp.status_code = 200

        keystone_session.Session.get_auth_headers = Mock(
            return_value=[]
        )
        keystone_session.Session.get_endpoint = Mock(
            return_value='foo'
        )
        keystone_session.Session._send_request = Mock(
            return_value=resp,
        )
        self.mock_send_request = keystone_session.Session._send_request

    def tearDown(self):
        super(TestTimeout, self).tearDown()
        (
            keystone_session.Session.get_auth_headers,
            keystone_session.Session.get_endpoint,
            keystone_session.Session._send_request,
        ) = self._saved_methods

    def _call_request_and_check_timeout(self, client, timeout):
        """call the mocked _send_request() and check if the timeout was set
        """
        client.limits.get()
        self.assertTrue(self.mock_send_request.called)
        kw = self.mock_send_request.call_args[1]
        if timeout is None:
            self.assertNotIn('timeout', kw)
        else:
            self.assertEqual(timeout, kw['timeout'])

    def test_no_timeout(self):
        session = create_session(timeout=None)
        client = Client(session=session)
        self.assertIsNone(session.timeout)
        self.assertIsNone(client.session.timeout)
        self._call_request_and_check_timeout(client, None)

    def test_timeout_in_session(self):
        session = create_session(timeout=1)
        client = Client(session=session)
        self.assertEqual(1, session.timeout)
        self.assertIsNone(client.session.timeout)
        self._call_request_and_check_timeout(client, 1)

    def test_timeout_override_session_timeout(self):
        # The adapter timeout should override the session timeout
        session = create_session(timeout=10)
        self.assertEqual(10, session.timeout)
        client = Client(session=session, timeout=2)
        self.assertEqual(2, client.session.timeout)
        self._call_request_and_check_timeout(client, 2)

    def test_timeout_update(self):
        session = create_session(timeout=1)
        client = Client(session=session)
        self.assertEqual(1, session.timeout)
        self.assertIsNone(client.session.timeout)
        self._call_request_and_check_timeout(client, 1)

        session.timeout = 2
        self.assertEqual(2, session.timeout)

        self._call_request_and_check_timeout(client, 2)
