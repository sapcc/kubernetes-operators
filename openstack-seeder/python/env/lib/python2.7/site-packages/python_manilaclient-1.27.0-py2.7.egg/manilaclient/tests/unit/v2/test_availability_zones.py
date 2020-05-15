# Copyright 2016 Mirantis, Inc.
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
import mock

from manilaclient import api_versions
from manilaclient.tests.unit import utils
from manilaclient.v2 import availability_zones


@ddt.ddt
class AvailabilityZoneTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return availability_zones.AvailabilityZoneManager(
            api=mock_microversion)

    def _get_resource_path(self, microversion):
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            return availability_zones.RESOURCE_PATH
        return availability_zones.RESOURCE_PATH_LEGACY

    @ddt.data("2.6", "2.7", api_versions.MIN_VERSION, api_versions.MAX_VERSION)
    def test_list(self, microversion):
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        self.mock_object(manager, "_list")

        result = manager.list()

        manager._list.assert_called_once_with(
            resource_path, availability_zones.RESOURCE_NAME)
        self.assertEqual(manager._list.return_value, result)

    def test_representation(self):
        resource = availability_zones.AvailabilityZone(None, {})
        resource.id = "9d21a755-b5ca-453e-a155-ee9c9066d909"
        expected = "<AvailabilityZone: 9d21a755-b5ca-453e-a155-ee9c9066d909>"
        self.assertEqual(repr(resource), expected)
