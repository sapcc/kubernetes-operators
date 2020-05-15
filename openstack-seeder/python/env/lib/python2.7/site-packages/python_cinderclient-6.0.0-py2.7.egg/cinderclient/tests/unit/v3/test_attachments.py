# Copyright (C) 2016 EMC Corporation.
#
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
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes


class AttachmentsTest(utils.TestCase):

    def test_create_attachment(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.27'))
        att = cs.attachments.create(
            'e84fda45-4de4-4ce4-8f39-fc9d3b0aa05e',
            {},
            '557ad76c-ce54-40a3-9e91-c40d21665cc3',
            'null')
        cs.assert_called('POST', '/attachments')
        self.assertEqual(fakes.fake_attachment['attachment'], att)

    def test_complete_attachment(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.44'))
        att = cs.attachments.complete('a232e9ae')
        self.assertTrue(att.ok)
