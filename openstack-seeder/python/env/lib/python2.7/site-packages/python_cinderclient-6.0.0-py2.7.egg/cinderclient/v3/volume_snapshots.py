# Copyright (c) 2013 OpenStack Foundation
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

"""Volume snapshot interface (v3 extension)."""

from cinderclient import api_versions
from cinderclient.apiclient import base as common_base
from cinderclient import base


class Snapshot(base.Resource):
    """A Snapshot is a point-in-time snapshot of an openstack volume."""

    def __repr__(self):
        return "<Snapshot: %s>" % self.id

    def delete(self, force=False):
        """Delete this snapshot."""
        return self.manager.delete(self, force)

    def update(self, **kwargs):
        """Update the name or description for this snapshot."""
        return self.manager.update(self, **kwargs)

    @property
    def progress(self):
        return self._info.get('os-extended-snapshot-attributes:progress')

    @property
    def project_id(self):
        return self._info.get('os-extended-snapshot-attributes:project_id')

    def reset_state(self, state):
        """Update the snapshot with the provided state."""
        return self.manager.reset_state(self, state)

    def set_metadata(self, metadata):
        """Set metadata of this snapshot."""
        return self.manager.set_metadata(self, metadata)

    def delete_metadata(self, keys):
        """Delete metadata of this snapshot."""
        return self.manager.delete_metadata(self, keys)

    def update_all_metadata(self, metadata):
        """Update_all metadata of this snapshot."""
        return self.manager.update_all_metadata(self, metadata)

    def manage(self, volume_id, ref, name=None, description=None,
               metadata=None):
        """Manage an existing snapshot."""
        self.manager.manage(volume_id=volume_id, ref=ref, name=name,
                            description=description, metadata=metadata)

    def list_manageable(self, host, detailed=True, marker=None, limit=None,
                        offset=None, sort=None, cluster=None):
        return self.manager.list_manageable(host, detailed=detailed,
                                            marker=marker, limit=limit,
                                            offset=offset, sort=sort,
                                            cluster=cluster)

    def unmanage(self, snapshot):
        """Unmanage a snapshot."""
        self.manager.unmanage(snapshot)


class SnapshotManager(base.ManagerWithFind):
    """Manage :class:`Snapshot` resources."""
    resource_class = Snapshot

    def create(self, volume_id, force=False,
               name=None, description=None, metadata=None):

        """Creates a snapshot of the given volume.

        :param volume_id: The ID of the volume to snapshot.
        :param force: If force is True, create a snapshot even if the volume is
        attached to an instance. Default is False.
        :param name: Name of the snapshot
        :param description: Description of the snapshot
        :param metadata: Metadata of the snapshot
        :rtype: :class:`Snapshot`
        """

        if metadata is None:
            snapshot_metadata = {}
        else:
            snapshot_metadata = metadata

        body = {'snapshot': {'volume_id': volume_id,
                             'force': force,
                             'name': name,
                             'description': description,
                             'metadata': snapshot_metadata}}
        return self._create('/snapshots', body, 'snapshot')

    def get(self, snapshot_id):
        """Shows snapshot details.

        :param snapshot_id: The ID of the snapshot to get.
        :rtype: :class:`Snapshot`
        """
        return self._get("/snapshots/%s" % snapshot_id, "snapshot")

    def list(self, detailed=True, search_opts=None, marker=None, limit=None,
             sort=None):
        """Get a list of all snapshots.

        :rtype: list of :class:`Snapshot`
        """
        resource_type = "snapshots"
        url = self._build_list_url(resource_type, detailed=detailed,
                                   search_opts=search_opts, marker=marker,
                                   limit=limit, sort=sort)
        return self._list(url, resource_type, limit=limit)

    def delete(self, snapshot, force=False):
        """Delete a snapshot.

        :param snapshot: The :class:`Snapshot` to delete.
        :param force: Allow delete in state other than error or available.
        """
        if force:
            return self._action('os-force_delete', snapshot)
        else:
            return self._delete("/snapshots/%s" % base.getid(snapshot))

    def update(self, snapshot, **kwargs):
        """Update the name or description for a snapshot.

        :param snapshot: The :class:`Snapshot` to update.
        """
        if not kwargs:
            return

        body = {"snapshot": kwargs}

        return self._update("/snapshots/%s" % base.getid(snapshot), body)

    def reset_state(self, snapshot, state):
        """Update the specified snapshot with the provided state."""
        return self._action('os-reset_status', snapshot,
                            {'status': state} if state else {})

    def _action(self, action, snapshot, info=None, **kwargs):
        """Perform a snapshot action."""
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/snapshots/%s/action' % base.getid(snapshot)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)

    def update_snapshot_status(self, snapshot, update_dict):
        return self._action('os-update_snapshot_status',
                            base.getid(snapshot), update_dict)

    def set_metadata(self, snapshot, metadata):
        """Update/Set a snapshots metadata.

        :param snapshot: The :class:`Snapshot`.
        :param metadata: A list of keys to be set.
        """
        body = {'metadata': metadata}
        return self._create("/snapshots/%s/metadata" % base.getid(snapshot),
                            body, "metadata")

    def delete_metadata(self, snapshot, keys):
        """Delete specified keys from snapshot metadata.

        :param snapshot: The :class:`Snapshot`.
        :param keys: A list of keys to be removed.
        """
        response_list = []
        snapshot_id = base.getid(snapshot)
        for k in keys:
            resp, body = self._delete("/snapshots/%s/metadata/%s" %
                                      (snapshot_id, k))
            response_list.append(resp)

        return common_base.ListWithMeta([], response_list)

    def update_all_metadata(self, snapshot, metadata):
        """Update_all snapshot metadata.

        :param snapshot: The :class:`Snapshot`.
        :param metadata: A list of keys to be updated.
        """
        body = {'metadata': metadata}
        return self._update("/snapshots/%s/metadata" % base.getid(snapshot),
                            body)

    def manage(self, volume_id, ref, name=None, description=None,
               metadata=None):
        """Manage an existing snapshot."""
        body = {'snapshot': {'volume_id': volume_id,
                             'ref': ref,
                             'name': name,
                             'description': description,
                             'metadata': metadata
                             }
                }
        return self._create('/os-snapshot-manage', body, 'snapshot')

    @api_versions.wraps('3.8')
    def list_manageable(self, host, detailed=True, marker=None, limit=None,
                        offset=None, sort=None, cluster=None):
        search_opts = {'cluster': cluster} if cluster else {'host': host}
        url = self._build_list_url("manageable_snapshots", detailed=detailed,
                                   search_opts=search_opts, marker=marker,
                                   limit=limit, offset=offset, sort=sort)
        return self._list(url, "manageable-snapshots")

    def unmanage(self, snapshot):
        """Unmanage a snapshot."""
        return self._action('os-unmanage', snapshot, None)
