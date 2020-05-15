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
class CinderVolumeNegativeTests(base.ClientTestBase):
    """Check of cinder volume create commands."""

    @ddt.data(
        ('', (r'Size is a required parameter')),
        ('-1', (r'Invalid input for field/attribute size')),
        ('0', (r"Invalid input for field/attribute size")),
        ('size', (r'invalid int value')),
        ('0.2', (r'invalid int value')),
        ('2 GB', (r'unrecognized arguments')),
        ('999999999', (r'VolumeSizeExceedsAvailableQuota')),
    )
    @ddt.unpack
    def test_volume_create_with_incorrect_size(self, value, ex_text):

        six.assertRaisesRegex(self, exceptions.CommandFailed, ex_text,
                              self.object_create, 'volume', params=value)


class CinderVolumeTests(base.ClientTestBase):
    """Check of cinder volume create commands."""
    def setUp(self):
        super(CinderVolumeTests, self).setUp()
        self.volume = self.object_create('volume', params='1')

    def test_volume_create_from_snapshot(self):
        """Test steps:

        1) create volume in Setup()
        2) create snapshot
        3) create volume from snapshot
        4) check that volume from snapshot has been successfully created
        """
        snapshot = self.object_create('snapshot', params=self.volume['id'])
        volume_from_snapshot = self.object_create('volume',
                                           params='--snapshot-id {0} 1'.
                                           format(snapshot['id']))
        self.object_delete('snapshot', snapshot['id'])
        self.check_object_deleted('snapshot', snapshot['id'])
        cinder_list = self.cinder('list')
        self.assertIn(volume_from_snapshot['id'], cinder_list)

    def test_volume_create_from_volume(self):
        """Test steps:

        1) create volume in Setup()
        2) create volume from volume
        3) check that volume from volume has been successfully created
        """
        volume_from_volume = self.object_create('volume',
                                         params='--source-volid {0} 1'.
                                         format(self.volume['id']))
        cinder_list = self.cinder('list')
        self.assertIn(volume_from_volume['id'], cinder_list)


class CinderVolumeTestsWithParameters(base.ClientTestBase):
    """Check of cinder volume create commands with parameters."""
    def test_volume_create_description(self):
        """Test steps:

        1) create volume with description
        2) check that volume has right description
        """
        volume_description = 'test_description'
        volume = self.object_create('volume',
                                    params='--description {0} 1'.
                                    format(volume_description))
        self.assertEqual(volume_description, volume['description'])

    def test_volume_create_metadata(self):
        """Test steps:

        1) create volume with metadata
        2) check that metadata complies entered
        """
        volume = self.object_create(
            'volume', params='--metadata test_metadata=test_date 1')
        self.assertEqual(six.text_type({u'test_metadata': u'test_date'}),
                         volume['metadata'])
