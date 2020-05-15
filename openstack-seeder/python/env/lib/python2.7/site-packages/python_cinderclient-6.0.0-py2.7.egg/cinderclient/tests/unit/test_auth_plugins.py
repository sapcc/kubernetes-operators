# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from cinderclient.contrib import noauth
from cinderclient.tests.unit import utils


class CinderNoAuthPluginTest(utils.TestCase):
    def setUp(self):
        super(CinderNoAuthPluginTest, self).setUp()
        self.plugin = noauth.CinderNoAuthPlugin('user', 'project',
                                                endpoint='example.com')

    def test_auth_token(self):
        auth_token = 'user:project'
        self.assertEqual(auth_token, self.plugin.auth_token)

    def test_auth_token_no_project(self):
        auth_token = 'user:user'
        plugin = noauth.CinderNoAuthPlugin('user')
        self.assertEqual(auth_token, plugin.auth_token)

    def test_get_headers(self):
        headers = {'x-user-id': 'user',
                   'x-project-id': 'project',
                   'X-Auth-Token': 'user:project'}
        self.assertEqual(headers, self.plugin.get_headers(None))

    def test_get_endpoint(self):
        endpoint = 'example.com/project'
        self.assertEqual(endpoint, self.plugin.get_endpoint(None))
