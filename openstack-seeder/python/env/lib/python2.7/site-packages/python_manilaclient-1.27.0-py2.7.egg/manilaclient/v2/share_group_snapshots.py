# Copyright 2015 Chuck Fouts
# Copyright 2016 Clinton Knight
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

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common.apiclient import base as common_base
from manilaclient.common import constants

RESOURCES_PATH = '/share-group-snapshots'
RESOURCE_PATH = '/share-group-snapshots/%s'
RESOURCE_PATH_ACTION = '/share-group-snapshots/%s/action'
RESOURCES_NAME = 'share_group_snapshots'
RESOURCE_NAME = 'share_group_snapshot'


class ShareGroupSnapshot(common_base.Resource):
    """A snapshot of a share group."""

    def __repr__(self):
        return "<Share Group Snapshot: %s>" % self.id

    def update(self, **kwargs):
        """Update this share group snapshot."""
        self.manager.update(self, **kwargs)

    def delete(self):
        """Delete this share group snapshot."""
        self.manager.delete(self)

    def reset_state(self, state):
        """Update this share group snapshot with the provided state."""
        self.manager.reset_state(self, state)


class ShareGroupSnapshotManager(base.ManagerWithFind):
    """Manage :class:`ShareGroupSnapshot` resources."""
    resource_class = ShareGroupSnapshot

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def create(self, share_group, name=None, description=None):
        """Create a share group snapshot.

        :param share_group: either ShareGroup object or text with its UUID
        :param name: text - name of the new group snapshot
        :param description: text - description of the group snapshot
        :rtype: :class:`ShareGroupSnapshot`
        """
        share_group_id = common_base.getid(share_group)
        body = {'share_group_id': share_group_id}
        if name:
            body['name'] = name
        if description:
            body['description'] = description

        return self._create(
            RESOURCES_PATH, {RESOURCE_NAME: body}, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def get(self, share_group_snapshot):
        """Get a share group snapshot.

        :param share_group_snapshot: either share group snapshot object or text
            with its UUID
        :rtype: :class:`ShareGroupSnapshot`
        """
        share_group_snapshot_id = common_base.getid(share_group_snapshot)
        url = RESOURCE_PATH % share_group_snapshot_id
        return self._get(url, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def list(self, detailed=True, search_opts=None,
             sort_key=None, sort_dir=None):
        """Get a list of all share group snapshots.

        :param detailed: Whether to return detailed snapshot info or not.
        :param search_opts: dict with search options to filter out snapshots.
            available keys are below (('name1', 'name2', ...), 'type'):
            - ('all_tenants', int)
            - ('offset', int)
            - ('limit', int)
            - ('name', text)
            - ('status', text)
            - ('share_group_id', text)
        :param sort_key: Key to be sorted (i.e. 'created_at' or 'status').
        :param sort_dir: Sort direction, should be 'desc' or 'asc'.
        :rtype: list of :class:`ShareGroupSnapshot`
        """

        search_opts = search_opts or {}

        if sort_key is not None:
            if sort_key in constants.SHARE_GROUP_SNAPSHOT_SORT_KEY_VALUES:
                search_opts['sort_key'] = sort_key
            else:
                msg = 'sort_key must be one of the following: %s.'
                msg_args = ', '.join(
                    constants.SHARE_GROUP_SNAPSHOT_SORT_KEY_VALUES)
                raise ValueError(msg % msg_args)

        if sort_dir is not None:
            if sort_dir in constants.SORT_DIR_VALUES:
                search_opts['sort_dir'] = sort_dir
            else:
                raise ValueError('sort_dir must be one of the following: %s.'
                                 % ', '.join(constants.SORT_DIR_VALUES))

        query_string = self._build_query_string(search_opts)

        if detailed:
            url = RESOURCES_PATH + '/detail' + query_string
        else:
            url = RESOURCES_PATH + query_string

        return self._list(url, RESOURCES_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def update(self, share_group_snapshot, **kwargs):
        """Updates a share group snapshot.

        :param share_group_snapshot: either ShareGroupSnapshot object or text
            with its UUID
        :rtype: :class:`ShareGroupSnapshot`
        """
        share_group_snapshot_id = common_base.getid(share_group_snapshot)
        url = RESOURCE_PATH % share_group_snapshot_id
        if not kwargs:
            return self._get(url, RESOURCE_NAME)
        else:
            body = {RESOURCE_NAME: kwargs}
            return self._update(url, body, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def delete(self, share_group_snapshot, force=False):
        """Delete a share group snapshot.

        :param share_group_snapshot: either ShareGroupSnapshot object or text
            with its UUID
        :param force: True to force the deletion
        """
        share_group_snapshot_id = common_base.getid(share_group_snapshot)
        if force:
            url = RESOURCE_PATH_ACTION % share_group_snapshot_id
            body = {'force_delete': None}
            self.api.client.post(url, body=body)
        else:
            url = RESOURCE_PATH % share_group_snapshot_id
            self._delete(url)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def reset_state(self, share_group_snapshot, state):
        """Update the specified share group snapshot.

        :param share_group_snapshot: either ShareGroupSnapshot object or text
            with its UUID
        :param state: The new state for the share group snapshot
        """
        share_group_snapshot_id = common_base.getid(share_group_snapshot)
        url = RESOURCE_PATH_ACTION % share_group_snapshot_id
        body = {'reset_status': {'status': state}}
        self.api.client.post(url, body=body)
