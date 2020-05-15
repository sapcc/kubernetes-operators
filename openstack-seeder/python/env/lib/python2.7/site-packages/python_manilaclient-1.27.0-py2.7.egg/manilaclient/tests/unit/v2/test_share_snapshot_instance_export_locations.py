# Copyright (c) 2017 Hitachi Data Systems
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


from manilaclient import extension
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_snapshot_instance_export_locations


extensions = [
    extension.Extension('share_snapshot_export_locations',
                        share_snapshot_instance_export_locations),
]
cs = fakes.FakeClient(extensions=extensions)


class ShareSnapshotInstanceExportLocationsTest(utils.TestCase):
    def test_list_snapshot_instance(self):
        snapshot_instance_id = '1234'
        cs.share_snapshot_instance_export_locations.list(
            snapshot_instance_id, search_opts=None)
        cs.assert_called(
            'GET', '/snapshot-instances/%s/export-locations'
                   % snapshot_instance_id)

    def test_get_snapshot_instance(self):
        snapshot_instance_id = '1234'
        el_id = 'fake_el_id'
        cs.share_snapshot_instance_export_locations.get(
            el_id, snapshot_instance_id)
        cs.assert_called(
            'GET',
            ('/snapshot-instances/%(snapshot_id)s/export-locations/'
             '%(el_id)s') % {
                'snapshot_id': snapshot_instance_id, 'el_id': el_id})
