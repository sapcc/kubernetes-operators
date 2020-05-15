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

from keystoneauth1 import adapter
from keystoneauth1 import session as keystone_session

from designateclient.tests.base import TestCase
from designateclient.v2.client import Client


class TestClient(TestCase):
    def test_init(self):
        self.assertRaises(ValueError, Client)

    def test_init_with_session(self):
        session = keystone_session.Session()
        adapted = adapter.Adapter(session=session)
        client = Client(session=adapted)
        assert client.session

    def test_init_with_session_timeout(self):
        session = keystone_session.Session()
        client = Client(
            session=session,
            timeout=1)
        assert client.session.timeout == 1

    def test_init_with_auth(self):
        session = keystone_session.Session()
        client = Client(
            auth='http://127.0.0.1:22/',
            session=session)
        assert client.session.auth
