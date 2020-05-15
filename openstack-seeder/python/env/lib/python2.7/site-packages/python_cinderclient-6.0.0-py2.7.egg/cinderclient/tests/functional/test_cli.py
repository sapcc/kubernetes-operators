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


from cinderclient.tests.functional import base


class CinderVolumeTests(base.ClientTestBase):
    """Check of base cinder volume commands."""

    CREATE_VOLUME_PROPERTY = (
        'attachments',
        'os-vol-tenant-attr:tenant_id',
        'availability_zone', 'bootable',
        'created_at', 'description', 'encrypted', 'id',
        'metadata', 'name', 'size', 'status',
        'user_id', 'volume_type')

    SHOW_VOLUME_PROPERTY = ('attachment_ids', 'attached_servers',
                       'availability_zone', 'bootable',
                       'created_at', 'description', 'encrypted', 'id',
                       'metadata', 'name', 'size', 'status',
                       'user_id', 'volume_type')

    def test_volume_create_delete_id(self):
        """Create and delete a volume by ID."""
        volume = self.object_create('volume', params='1')
        self.assert_object_details(self.CREATE_VOLUME_PROPERTY, volume.keys())
        self.object_delete('volume', volume['id'])
        self.check_object_deleted('volume', volume['id'])

    def test_volume_create_delete_name(self):
        """Create and delete a volume by name."""
        volume = self.object_create('volume',
                                    params='1 --name TestVolumeNamedCreate')

        self.cinder('delete', params='TestVolumeNamedCreate')
        self.check_object_deleted('volume', volume['id'])

    def test_volume_show(self):
        """Show volume details."""
        volume = self.object_create('volume', params='1 --name TestVolumeShow')
        output = self.cinder('show', params='TestVolumeShow')
        volume = self._get_property_from_output(output)
        self.assertEqual('TestVolumeShow', volume['name'])
        self.assert_object_details(self.SHOW_VOLUME_PROPERTY, volume.keys())

        self.object_delete('volume', volume['id'])
        self.check_object_deleted('volume', volume['id'])

    def test_volume_extend(self):
        """Extend a volume size."""
        volume = self.object_create('volume',
                                    params='1 --name TestVolumeExtend')
        self.cinder('extend', params="%s %s" % (volume['id'], 2))
        self.wait_for_object_status('volume', volume['id'], 'available')
        output = self.cinder('show', params=volume['id'])
        volume = self._get_property_from_output(output)
        self.assertEqual('2', volume['size'])

        self.object_delete('volume', volume['id'])
        self.check_object_deleted('volume', volume['id'])


class CinderSnapshotTests(base.ClientTestBase):
    """Check of base cinder snapshot commands."""

    SNAPSHOT_PROPERTY = ('created_at', 'description', 'metadata', 'id',
                         'name', 'size', 'status', 'volume_id')

    def test_snapshot_create_and_delete(self):
        """Create a volume snapshot and then delete."""
        volume = self.object_create('volume', params='1')
        snapshot = self.object_create('snapshot', params=volume['id'])
        self.assert_object_details(self.SNAPSHOT_PROPERTY, snapshot.keys())
        self.object_delete('snapshot', snapshot['id'])
        self.check_object_deleted('snapshot', snapshot['id'])
        self.object_delete('volume', volume['id'])
        self.check_object_deleted('volume', volume['id'])


class CinderBackupTests(base.ClientTestBase):
    """Check of base cinder backup commands."""

    BACKUP_PROPERTY = ('id', 'name', 'volume_id')

    def test_backup_create_and_delete(self):
        """Create a volume backup and then delete."""
        volume = self.object_create('volume', params='1')
        backup = self.object_create('backup', params=volume['id'])
        self.assert_object_details(self.BACKUP_PROPERTY, backup.keys())
        self.object_delete('volume', volume['id'])
        self.check_object_deleted('volume', volume['id'])
        self.object_delete('backup', backup['id'])
        self.check_object_deleted('backup', backup['id'])
