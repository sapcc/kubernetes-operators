# Copyright 2015 Mirantis Inc.
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

import ddt
from tempest.lib.common.utils import data_utils

from manilaclient.tests.functional import base


@ddt.ddt
class SecurityServiceReadWriteTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(SecurityServiceReadWriteTest, cls).setUpClass()
        cls.name = data_utils.rand_name('autotest')
        cls.description = 'fake_description'
        cls.user = 'fake_user'
        cls.password = 'fake_password'
        cls.server = 'fake_server'
        cls.domain = 'fake_domain'
        cls.dns_ip = '1.2.3.4'
        cls.ou = 'fake_ou'

    @ddt.data(
        {'name': 'test_name'},
        {'description': 'test_description'},
        {'user': 'test_username'},
        {'password': 'test_password'},
        {'server': 'test_server'},
        {'domain': 'test_domain'},
        {'dns_ip': 'test_dns_ip'},
        {'ou': 'test_ou'},
        {'name': '""'},
        {'description': '""'},
        {'user': '""'},
        {'password': '""'},
        {'server': '""'},
        {'domain': '""'},
        {'dns_ip': '""'},
        {'ou': '""'},
    )
    def test_create_update_security_service(self, ss_data):
        expected_data = {
            'name': self.name,
            'description': self.description,
            'user': self.user,
            'password': self.password,
            'server': self.server,
            'domain': self.domain,
            'dns_ip': self.dns_ip,
            'ou': self.ou,
        }

        ss = self.create_security_service(**expected_data)
        update = self.admin_client.update_security_service(ss['id'], **ss_data)
        expected_data.update(ss_data)

        for k, v in expected_data.items():
            if v == '""':
                self.assertEqual('None', update[k])
            else:
                self.assertEqual(v, update[k])
