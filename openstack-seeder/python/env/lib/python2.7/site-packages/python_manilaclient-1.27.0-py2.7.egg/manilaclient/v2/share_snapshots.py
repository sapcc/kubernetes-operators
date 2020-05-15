# Copyright 2012 NetApp
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
"""Interface for shares extension."""

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common.apiclient import base as common_base
from manilaclient.common import constants


class ShareSnapshot(common_base.Resource):
    """Represent a snapshot of a share."""

    def __repr__(self):
        return "<ShareSnapshot: %s>" % self.id

    def update(self, **kwargs):
        """Update this snapshot."""
        self.manager.update(self, **kwargs)

    def reset_state(self, state):
        """Update the snapshot with the provided state."""
        self.manager.reset_state(self, state)

    def delete(self):
        """Delete this snapshot."""
        self.manager.delete(self)

    def force_delete(self):
        """Delete the specified snapshot ignoring its current state."""
        self.manager.force_delete(self)

    def unmanage_snapshot(self):
        """Unmanage this snapshot."""
        self.manager.unmanage(self)

    def allow(self, access_type, access_to):
        """Allow access to a share snapshot."""
        return self.manager.allow(self, access_type, access_to)

    def deny(self, id):
        """Denies access to a share snapshot."""
        return self.manager.deny(self, id)

    def access_list(self):
        return self.manager.access_list(self)


class ShareSnapshotManager(base.ManagerWithFind):
    """Manage :class:`ShareSnapshot` resources."""
    resource_class = ShareSnapshot

    def create(self, share, force=False, name=None, description=None):
        """Create a snapshot of the given share.

        :param share_id: The ID of the share to snapshot.
        :param force: If force is True, create a snapshot even if the
                      share is busy. Default is False.
        :param name: Name of the snapshot
        :param description: Description of the snapshot
        :rtype: :class:`ShareSnapshot`
        """
        body = {'snapshot': {'share_id': common_base.getid(share),
                             'force': force,
                             'name': name,
                             'description': description}}
        return self._create('/snapshots', body, 'snapshot')

    @api_versions.wraps("2.12")
    def manage(self, share, provider_location,
               driver_options=None,
               name=None, description=None):
        """Manage an existing share snapshot.

        :param share: The share object.
        :param provider_location: The provider location of
                                  the snapshot on the backend.
        :param driver_options: dict - custom set of key-values.
        :param name: text - name of new snapshot
        :param description: - description for new snapshot
        """
        driver_options = driver_options if driver_options else {}
        body = {
            'share_id': common_base.getid(share),
            'provider_location': provider_location,
            'driver_options': driver_options,
            'name': name,
            'description': description,
        }
        return self._create('/snapshots/manage', {'snapshot': body},
                            'snapshot')

    @api_versions.wraps("2.12")
    def unmanage(self, snapshot):
        """Unmanage a share snapshot.

        :param snapshot: either snapshot object or text with its ID.
        """
        return self._action("unmanage", snapshot)

    def get(self, snapshot):
        """Get a snapshot.

        :param snapshot: The :class:`ShareSnapshot` instance or string with ID
            of snapshot to delete.
        :rtype: :class:`ShareSnapshot`
        """
        snapshot_id = common_base.getid(snapshot)
        return self._get('/snapshots/%s' % snapshot_id, 'snapshot')

    def list(self, detailed=True, search_opts=None, sort_key=None,
             sort_dir=None):
        """Get a list of snapshots of shares.

        :param search_opts: Search options to filter out shares.
        :param sort_key: Key to be sorted.
        :param sort_dir: Sort direction, should be 'desc' or 'asc'.
        :rtype: list of :class:`ShareSnapshot`
        """
        search_opts = search_opts or {}

        if sort_key is not None:
            if sort_key in constants.SNAPSHOT_SORT_KEY_VALUES:
                search_opts['sort_key'] = sort_key
            else:
                raise ValueError(
                    'sort_key must be one of the following: %s.'
                    % ', '.join(constants.SNAPSHOT_SORT_KEY_VALUES))

        if sort_dir is not None:
            if sort_dir in constants.SORT_DIR_VALUES:
                search_opts['sort_dir'] = sort_dir
            else:
                raise ValueError(
                    'sort_dir must be one of the following: %s.'
                    % ', '.join(constants.SORT_DIR_VALUES))

        query_string = self._build_query_string(search_opts)

        if detailed:
            path = "/snapshots/detail%s" % (query_string,)
        else:
            path = "/snapshots%s" % (query_string,)

        return self._list(path, 'snapshots')

    def delete(self, snapshot):
        """Delete a snapshot of a share.

        :param snapshot: The :class:`ShareSnapshot` to delete.
        """
        self._delete("/snapshots/%s" % common_base.getid(snapshot))

    def _do_force_delete(self, snapshot, action_name="force_delete"):
        """Delete the specified snapshot ignoring its current state."""
        return self._action(action_name, common_base.getid(snapshot))

    @api_versions.wraps("1.0", "2.6")
    def force_delete(self, snapshot):
        return self._do_force_delete(snapshot, "os-force_delete")

    @api_versions.wraps("2.7")  # noqa
    def force_delete(self, snapshot):
        return self._do_force_delete(snapshot, "force_delete")

    def update(self, snapshot, **kwargs):
        """Update a snapshot.

        :param snapshot: The :class:`ShareSnapshot` instance or string with ID
            of snapshot to delete.
        :rtype: :class:`ShareSnapshot`
        """
        if not kwargs:
            return

        body = {'snapshot': kwargs, }
        snapshot_id = common_base.getid(snapshot)
        return self._update("/snapshots/%s" % snapshot_id, body)

    def _do_reset_state(self, snapshot, state, action_name="reset_status"):
        """Update the specified share snapshot with the provided state."""
        return self._action(action_name, snapshot, {"status": state})

    @api_versions.wraps("1.0", "2.6")
    def reset_state(self, snapshot, state):
        return self._do_reset_state(snapshot, state, "os-reset_status")

    @api_versions.wraps("2.7")  # noqa
    def reset_state(self, snapshot, state):
        return self._do_reset_state(snapshot, state, "reset_status")

    def _do_allow(self, snapshot, access_type, access_to):
        access_params = {
            'access_type': access_type,
            'access_to': access_to,
        }

        return self._action('allow_access', snapshot,
                            access_params)[1]['snapshot_access']

    @api_versions.wraps("2.32")
    def allow(self, snapshot, access_type, access_to):
        return self._do_allow(snapshot, access_type, access_to)

    def _do_deny(self, snapshot, id):
        return self._action('deny_access', snapshot, {'access_id': id})

    @api_versions.wraps("2.32")
    def deny(self, snapshot, id):
        return self._do_deny(snapshot, id)

    def _do_access_list(self, snapshot):
        snapshot_id = common_base.getid(snapshot)
        access_list = self._list("/snapshots/%s/access-list" % snapshot_id,
                                 'snapshot_access_list')
        return access_list

    @api_versions.wraps("2.32")
    def access_list(self, snapshot):
        return self._do_access_list(snapshot)

    def _action(self, action, snapshot, info=None, **kwargs):
        """Perform a snapshot 'action'."""
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/snapshots/%s/action' % common_base.getid(snapshot)
        return self.api.client.post(url, body=body)
