# Copyright 2015 Mirantis inc.
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
from manilaclient import extension
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_instance_export_locations


extensions = [
    extension.Extension('share_instance_export_locations',
                        share_instance_export_locations),
]
cs = fakes.FakeClient(extensions=extensions)


@ddt.ddt
class ShareInstanceExportLocationsTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return (
            share_instance_export_locations.ShareInstanceExportLocationManager(
                api=mock_microversion)
        )

    def test_list_of_export_locations(self):
        share_instance_id = '1234'
        cs.share_instance_export_locations.list(
            share_instance_id, search_opts=None)
        cs.assert_called(
            'GET', '/share_instances/%s/export_locations' % share_instance_id)

    def test_get_single_export_location(self):
        share_instance_id = '1234'
        el_uuid = 'fake_el_uuid'
        cs.share_instance_export_locations.get(share_instance_id, el_uuid)
        cs.assert_called(
            'GET',
            ('/share_instances/%(share_instance_id)s/export_locations/'
             '%(el_uuid)s') % {
                 'share_instance_id': share_instance_id, 'el_uuid': el_uuid})
