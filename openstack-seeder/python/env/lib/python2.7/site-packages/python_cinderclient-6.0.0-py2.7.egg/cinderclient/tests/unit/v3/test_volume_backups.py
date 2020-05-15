# Copyright (c) 2016 Intel, Inc.
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
from cinderclient import exceptions as exc
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes


class VolumesTest(utils.TestCase):

    def test_update(self):
        cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.9'))
        b = cs.backups.get('1234')
        backup = b.update(name='new-name')
        cs.assert_called(
            'PUT', '/backups/1234',
            {'backup': {'name': 'new-name'}})
        self._assert_request_id(backup)

    def test_pre_version(self):
        cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.8'))
        b = cs.backups.get('1234')
        self.assertRaises(exc.VersionNotFoundForAPIMethod,
                          b.update, name='new-name')
