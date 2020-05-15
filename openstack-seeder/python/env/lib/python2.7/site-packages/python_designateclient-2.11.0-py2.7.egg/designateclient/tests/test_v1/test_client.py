# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Author: Kiall Mac Innes <kiall@hp.com>
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

from designateclient.tests import test_v1
from designateclient import utils
from designateclient import v1

from keystoneauth1 import session as keystone_session


class TestClient(test_v1.APIV1TestCase):
    def test_all_tenants(self):
        # Create a client with the all_tenants flag set to True
        client = v1.Client(all_tenants=True)

        # Verify this has been picked up
        self.assertTrue(client.all_tenants)

    def test_all_tenants_not_supplied(self):
        # Create a client without supplying any all_tenants flag
        client = v1.Client()

        # Verify all_tenants is False
        self.assertFalse(client.all_tenants)
        self.assertIsNotNone(client.all_tenants)

    def test_all_tenants_through_session(self):
        # Create a session with the all_tenants flag set to True
        session = utils.get_session(
            auth_url='Anything',
            endpoint='Anything',
            domain_id='Anything',
            domain_name='Anything',
            project_id='Anything',
            project_name='Anything',
            project_domain_name='Anything',
            project_domain_id='Anything',
            username='Anything',
            user_id='Anything',
            password='Anything',
            user_domain_id='Anything',
            user_domain_name='Anything',
            token=None,
            insecure=False,
            cacert=None,
            all_tenants=True)

        # Create a client using the pre-created session
        client = v1.Client(session=session)

        # Verify the all_tenants flag has been picked up
        self.assertTrue(client.all_tenants)

    def test_edit_managed(self):
        # Create a client with the edit_managed flag set to True
        client = v1.Client(edit_managed=True)

        # Verify this has been picked up
        self.assertTrue(client.edit_managed)

    def test_edit_managed_not_supplied(self):
        # Create a client without supplying any edit_managed flag
        client = v1.Client()

        # Verify edit_managed is False
        self.assertFalse(client.edit_managed)
        self.assertIsNotNone(client.edit_managed)

    def test_edit_managed_through_session(self):
        # Create a session with the edit_managed flag set to True
        session = utils.get_session(
            auth_url='Anything',
            endpoint='Anything',
            domain_id='Anything',
            domain_name='Anything',
            project_id='Anything',
            project_name='Anything',
            project_domain_name='Anything',
            project_domain_id='Anything',
            username='Anything',
            user_id='Anything',
            password='Anything',
            user_domain_id='Anything',
            user_domain_name='Anything',
            token=None,
            insecure=False,
            cacert=None,
            edit_managed=True)

        # Create a client using the pre-created session
        client = v1.Client(session=session)

        # Verify the edit_managed flag has been picked up
        self.assertTrue(client.edit_managed)

    def test_timeout_new_session(self):
        client = v1.Client(
            auth_url="http://127.0.0.1:22/",
            timeout=1,
        )
        assert client.session.timeout == 1

    def test_timeout_override_session_timeout(self):
        # The adapter timeout should override the session timeout
        session = keystone_session.Session(timeout=10)
        client = v1.Client(
            auth_url="http://127.0.0.1:22/",
            session=session,
            timeout=2,
        )
        self.assertEqual(2, client.session.timeout)
