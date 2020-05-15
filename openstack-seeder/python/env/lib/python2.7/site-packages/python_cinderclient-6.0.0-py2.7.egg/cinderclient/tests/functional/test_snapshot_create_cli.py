#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import six

from cinderclient.tests.functional import base


class CinderSnapshotTests(base.ClientTestBase):
    """Check of cinder snapshot commands."""
    def setUp(self):
        super(CinderSnapshotTests, self).setUp()
        self.volume = self.object_create('volume', params='1')

    def test_snapshot_create_description(self):
        """Test steps:

        1) create volume in Setup()
        2) create snapshot with description
        3) check that snapshot has right description
        """
        description = 'test_description'
        snapshot = self.object_create('snapshot',
                                      params='--description {0} {1}'.
                                      format(description, self.volume['id']))
        self.assertEqual(description, snapshot['description'])
        self.object_delete('snapshot', snapshot['id'])
        self.check_object_deleted('snapshot', snapshot['id'])

    def test_snapshot_create_metadata(self):
        """Test steps:

        1) create volume in Setup()
        2) create snapshot with metadata
        3) check that metadata complies entered
        """
        snapshot = self.object_create(
            'snapshot',
            params='--metadata test_metadata=test_date {0}'.format(
                self.volume['id']))
        self.assertEqual(six.text_type({u'test_metadata': u'test_date'}),
                         snapshot['metadata'])
        self.object_delete('snapshot', snapshot['id'])
        self.check_object_deleted('snapshot', snapshot['id'])
