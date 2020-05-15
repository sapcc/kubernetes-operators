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
from manilaclient.v2 import share_instances


extensions = [
    extension.Extension('share_instances', share_instances),
]
cs = fakes.FakeClient(extensions=extensions)


@ddt.ddt
class ShareInstancesTest(utils.TestCase):

    def _get_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return share_instances.ShareInstanceManager(api=mock_microversion)

    def test_list(self):
        cs.share_instances.list(search_opts=None)
        cs.assert_called('GET', '/share_instances')

    @ddt.data(('id', 'b4991315-eb7d-43ec-979e-5715d4399827'),
              ('path', '//0.0.0.0/fake_path'))
    @ddt.unpack
    def test_list_by_export_location(self, filter_type, value):
        cs.share_instances.list(export_location=value)
        cs.assert_called(
            'GET', '/share_instances?export_location_' +
            filter_type + '=' + value)

    def test_get(self):
        instance = type('None', (object, ), {'id': '1234'})
        cs.share_instances.get(instance)
        cs.assert_called('GET', '/share_instances/1234')

    @ddt.data(
        ("2.6", type("InstanceUUID", (object, ), {"uuid": "1234"})),
        ("2.7", type("InstanceUUID", (object, ), {"uuid": "1234"})),
        ("2.6", type("InstanceID", (object, ), {"id": "1234"})),
        ("2.7", type("InstanceID", (object, ), {"id": "1234"})),
        ("2.6", "1234"),
        ("2.7", "1234"),
    )
    @ddt.unpack
    def test_reset_instance_state(self, microversion, instance):
        manager = self._get_manager(microversion)
        state = 'available'
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            action_name = "reset_status"
        else:
            action_name = "os-reset_status"

        with mock.patch.object(manager, "_action", mock.Mock()):
            manager.reset_state(instance, state)

            manager._action.assert_called_once_with(
                action_name, instance, {"status": state})

    @ddt.data(
        ("2.6", type('InstanceUUID', (object, ), {"uuid": "1234"})),
        ("2.6", "1234"),
        ("2.7", type('InstanceUUID', (object, ), {"uuid": "1234"})),
        ("2.7", "1234"),
    )
    @ddt.unpack
    def test_force_delete_share_snapshot(self, microversion, instance):
        manager = self._get_manager(microversion)
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            action_name = "force_delete"
        else:
            action_name = "os-force_delete"

        with mock.patch.object(manager, "_action", mock.Mock()):
            manager.force_delete(instance)

            manager._action.assert_called_once_with(action_name, "1234")

    @ddt.data(
        ("2.6", "1234", "migrating_to"),
        ("2.6", "1234", "error"),
        ("2.6", "1234", "available"),
        ("2.7", "1234", "error_deleting"),
        ("2.7", "1234", "deleting"),
        ("2.7", "1234", "migrating"),
    )
    @ddt.unpack
    def test_valid_instance_state(self, microversion, instance, state):
        manager = self._get_manager(microversion)
        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            action_name = "reset_status"
        else:
            action_name = "os-reset_status"

        with mock.patch.object(manager, "_action", mock.Mock()):
            manager.reset_state(instance, state)

            manager._action.assert_called_once_with(
                action_name, instance, {"status": state})
