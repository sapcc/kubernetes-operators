# Copyright (c) 2016 Red Hat Inc.
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

from cinderclient import api_versions
from cinderclient.v3 import services

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes


class ServicesTest(utils.TestCase):

    def test_list_services_with_cluster_info(self):
        cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.7'))
        services_list = cs.services.list()
        cs.assert_called('GET', '/os-services')
        self.assertEqual(3, len(services_list))
        for service in services_list:
            self.assertIsInstance(service, services.Service)
            # Make sure cluster fields from v3.7 is present and not None
            self.assertIsNotNone(getattr(service, 'cluster'))
        self._assert_request_id(services_list)

    def test_api_version(self):
        client = fakes.FakeClient(version_header='3.0')
        svs = client.services.server_api_version()
        [self.assertIsInstance(s, services.Service) for s in svs]

    def test_set_log_levels(self):
        expected = {'level': 'debug', 'binary': 'cinder-api',
                    'server': 'host1', 'prefix': 'sqlalchemy.'}

        cs = fakes.FakeClient(version_header='3.32')
        cs.services.set_log_levels(expected['level'], expected['binary'],
                                   expected['server'], expected['prefix'])

        cs.assert_called('PUT', '/os-services/set-log', body=expected)

    def test_get_log_levels(self):
        expected = {'binary': 'cinder-api', 'server': 'host1',
                    'prefix': 'sqlalchemy.'}

        cs = fakes.FakeClient(version_header='3.32')
        result = cs.services.get_log_levels(expected['binary'],
                                            expected['server'],
                                            expected['prefix'])

        cs.assert_called('PUT', '/os-services/get-log', body=expected)
        expected = [services.LogLevel(cs.services,
                                      {'binary': 'cinder-api', 'host': 'host1',
                                       'prefix': 'prefix1', 'level': 'DEBUG'},
                                      loaded=True),
                    services.LogLevel(cs.services,
                                      {'binary': 'cinder-api', 'host': 'host1',
                                       'prefix': 'prefix2', 'level': 'INFO'},
                                      loaded=True),
                    services.LogLevel(cs.services,
                                      {'binary': 'cinder-volume',
                                       'host': 'host@backend#pool',
                                       'prefix': 'prefix3',
                                       'level': 'WARNING'},
                                      loaded=True),
                    services.LogLevel(cs.services,
                                      {'binary': 'cinder-volume',
                                       'host': 'host@backend#pool',
                                       'prefix': 'prefix4', 'level': 'ERROR'},
                                      loaded=True)]
        # Since it will be sorted by the prefix we can compare them directly
        self.assertListEqual(expected, result)

    def test_list_services_with_backend_state(self):
        cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.49'))
        services_list = cs.services.list()
        cs.assert_called('GET', '/os-services')
        self.assertEqual(3, len(services_list))
        for service in services_list:
            self.assertIsInstance(service, services.Service)
            # Make sure backend_state fields from v3.49 is present and not
            # None
            if service.binary == 'cinder-volume':
                self.assertIsNotNone(getattr(service, 'backend_state',
                                             None))
        self._assert_request_id(services_list)
