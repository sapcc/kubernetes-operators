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
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_replica_export_locations

cs = fakes.FakeClient()


@ddt.ddt
class ShareReplicaExportLocationsTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return (
            share_replica_export_locations.ShareReplicaExportLocationManager(
                api=mock_microversion)
        )

    def test_list_share_replica_export_locations(self):
        share_replica_id = '1234'
        cs.share_replica_export_locations.list(share_replica_id)
        cs.assert_called(
            'GET', '/share-replicas/%s/export-locations' % share_replica_id)

    def test_get_share_replica_export_location(self):
        share_replica_id = '1234'
        el_uuid = 'fake_el_uuid'
        cs.share_replica_export_locations.get(share_replica_id, el_uuid)
        url = ('/share-replicas/%(share_replica_id)s/export-locations/'
               '%(el_uuid)s')
        payload = {'share_replica_id': share_replica_id, 'el_uuid': el_uuid}
        cs.assert_called('GET', url % payload)
