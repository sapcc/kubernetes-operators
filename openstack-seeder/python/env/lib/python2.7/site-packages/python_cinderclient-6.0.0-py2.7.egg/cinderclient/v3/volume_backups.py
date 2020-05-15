# Copyright (C) 2013 Hewlett-Packard Development Company, L.P.
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

"""
Volume Backups interface (v3 extension).
"""

from cinderclient import api_versions
from cinderclient import base
from cinderclient.v2 import volume_backups


VolumeBackup = volume_backups.VolumeBackup


class VolumeBackupManager(volume_backups.VolumeBackupManager):
    @api_versions.wraps("3.9")
    def update(self, backup, **kwargs):
        """Update the name or description for a backup.

        :param backup: The :class:`Backup` to update.
        """
        if not kwargs:
            return

        body = {"backup": kwargs}

        return self._update("/backups/%s" % base.getid(backup), body)

    @api_versions.wraps("3.0")
    def create(self, volume_id, container=None,
               name=None, description=None,
               incremental=False, force=False,
               snapshot_id=None):
        """Creates a volume backup.

        :param volume_id: The ID of the volume to backup.
        :param container: The name of the backup service container.
        :param name: The name of the backup.
        :param description: The description of the backup.
        :param incremental: Incremental backup.
        :param force: If True, allows an in-use volume to be backed up.
        :param snapshot_id: The ID of the snapshot to backup. This should
                            be a snapshot of the src volume, when specified,
                            the new backup will be based on the snapshot.
        :rtype: :class:`VolumeBackup`
        """
        return self._create_backup(volume_id, container, name, description,
                                   incremental, force, snapshot_id)

    @api_versions.wraps("3.43")  # noqa: F811
    def create(self, volume_id, container=None,
               name=None, description=None,
               incremental=False, force=False,
               snapshot_id=None,
               metadata=None):
        """Creates a volume backup.

        :param volume_id: The ID of the volume to backup.
        :param container: The name of the backup service container.
        :param name: The name of the backup.
        :param description: The description of the backup.
        :param incremental: Incremental backup.
        :param force: If True, allows an in-use volume to be backed up.
        :param metadata: Key Value pairs
        :param snapshot_id: The ID of the snapshot to backup. This should
                            be a snapshot of the src volume, when specified,
                            the new backup will be based on the snapshot.
        :rtype: :class:`VolumeBackup`
        """
        # pylint: disable=function-redefined
        return self._create_backup(volume_id, container, name, description,
                                   incremental, force, snapshot_id, metadata)

    @api_versions.wraps("3.51")  # noqa: F811
    def create(self, volume_id, container=None, name=None, description=None,
               incremental=False, force=False, snapshot_id=None, metadata=None,
               availability_zone=None):
        return self._create_backup(volume_id, container, name, description,
                                   incremental, force, snapshot_id, metadata,
                                   availability_zone)

    def _create_backup(self, volume_id, container=None, name=None,
                       description=None, incremental=False, force=False,
                       snapshot_id=None, metadata=None,
                       availability_zone=None):
        """Creates a volume backup.

        :param volume_id: The ID of the volume to backup.
        :param container: The name of the backup service container.
        :param name: The name of the backup.
        :param description: The description of the backup.
        :param incremental: Incremental backup.
        :param force: If True, allows an in-use volume to be backed up.
        :param metadata: Key Value pairs
        :param snapshot_id: The ID of the snapshot to backup. This should
                            be a snapshot of the src volume, when specified,
                            the new backup will be based on the snapshot.
        :param availability_zone: The AZ where we want the backup stored.
        :rtype: :class:`VolumeBackup`
        """
        # pylint: disable=function-redefined
        body = {'backup': {'volume_id': volume_id,
                           'container': container,
                           'name': name,
                           'description': description,
                           'incremental': incremental,
                           'force': force,
                           'snapshot_id': snapshot_id, }}
        if metadata:
            body['backup']['metadata'] = metadata
        if availability_zone:
            body['backup']['availability_zone'] = availability_zone
        return self._create('/backups', body, 'backup')
