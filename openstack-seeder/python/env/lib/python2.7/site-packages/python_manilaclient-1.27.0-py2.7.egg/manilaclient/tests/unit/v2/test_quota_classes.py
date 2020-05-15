# Copyright 2013 OpenStack Foundation
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
from manilaclient.v2 import quota_classes


@ddt.ddt
class QuotaClassSetsTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return quota_classes.QuotaClassSetManager(api=mock_microversion)

    def _get_resource_path(self, microversion):
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            return quota_classes.RESOURCE_PATH
        return quota_classes.RESOURCE_PATH_LEGACY

    @ddt.data("2.6", "2.7")
    def test_class_quotas_get(self, microversion):
        class_name = 'test'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        expected_url = "%s/test" % resource_path
        with mock.patch.object(manager, '_get',
                               mock.Mock(return_value='fake_get')):
            manager.get(class_name)

            manager._get.assert_called_once_with(
                expected_url, "quota_class_set")

    @ddt.data("2.6", "2.7")
    def test_update_quota(self, microversion):
        class_name = 'test'
        manager = self._get_manager(microversion)
        resource_path = self._get_resource_path(microversion)
        expected_url = "%s/test" % resource_path
        expected_body = {
            'quota_class_set': {
                'class_name': class_name,
                'shares': 1,
                'snapshots': 2,
                'gigabytes': 3,
                'snapshot_gigabytes': 4,
                'share_networks': 5,
            },
        }
        with mock.patch.object(manager, '_update',
                               mock.Mock(return_value='fake_update')):
            manager.update(
                class_name, shares=1, snapshots=2, gigabytes=3,
                snapshot_gigabytes=4, share_networks=5)

            manager._update.assert_called_once_with(
                expected_url, expected_body)
