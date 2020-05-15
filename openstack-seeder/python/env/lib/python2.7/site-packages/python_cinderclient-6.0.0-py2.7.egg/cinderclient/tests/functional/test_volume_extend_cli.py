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
import six

from tempest.lib import exceptions

from cinderclient.tests.functional import base


@ddt.ddt
class CinderVolumeExtendNegativeTests(base.ClientTestBase):
    """Check of cinder volume extend command."""

    def setUp(self):
        super(CinderVolumeExtendNegativeTests, self).setUp()
        self.volume = self.object_create('volume', params='1')

    @ddt.data(
        ('', (r'too few arguments|the following arguments are required')),
        ('-1', (r'Invalid input for field/attribute new_size. Value: -1. '
                r'-1 is less than the minimum of 1')),
        ('0', (r'Invalid input for field/attribute new_size. Value: 0. '
               r'0 is less than the minimum of 1')),
        ('size', (r'invalid int value')),
        ('0.2', (r'invalid int value')),
        ('2 GB', (r'unrecognized arguments')),
        ('999999999', (r'VolumeSizeExceedsAvailableQuota')),
    )
    @ddt.unpack
    def test_volume_extend_with_incorrect_size(self, value, ex_text):

        six.assertRaisesRegex(
            self, exceptions.CommandFailed, ex_text, self.cinder, 'extend',
            params='{0} {1}'.format(self.volume['id'], value))

    @ddt.data(
        ('', (r'too few arguments|the following arguments are required')),
        ('1234-1234-1234', (r'No volume with a name or ID of')),
        ('my_volume', (r'No volume with a name or ID of')),
        ('1234 1234', (r'unrecognized arguments'))
    )
    @ddt.unpack
    def test_volume_extend_with_incorrect_volume_id(self, value, ex_text):

        six.assertRaisesRegex(
            self, exceptions.CommandFailed, ex_text, self.cinder, 'extend',
            params='{0} 2'.format(value))
