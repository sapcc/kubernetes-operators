# Copyright 2015 Andrew Kerr
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

RESOURCES_PATH = '/share-groups'
RESOURCE_PATH = '/share-groups/%s'
RESOURCE_PATH_ACTION = '/share-groups/%s/action'
RESOURCES_NAME = 'share_groups'
RESOURCE_NAME = 'share_group'


class ShareGroup(common_base.Resource):
    """A share group is a logical grouping of shares on a single backend."""

    def __repr__(self):
        return "<Share Group: %s>" % self.id

    def update(self, **kwargs):
        """Update this share group."""
        self.manager.update(self, **kwargs)

    def delete(self, force=False):
        """Delete this share group."""
        self.manager.delete(self, force=force)

    def reset_state(self, state):
        """Update this share group with the provided state."""
        self.manager.reset_state(self, state)


class ShareGroupManager(base.ManagerWithFind):
    """Manage :class:`ShareGroup` resources."""
    resource_class = ShareGroup

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def create(self, share_group_type=None, share_types=None,
               share_network=None, name=None, description=None,
               source_share_group_snapshot=None, availability_zone=None):
        """Create a Share Group.

        :param share_group_type: either instance of ShareGroupType or text
            with UUID
        :param share_types: list of the share types allowed in the group. May
            not be supplied when 'source_group_snapshot_id' is provided.  These
            may be ShareType objects or UUIDs.
        :param share_network: either the share network object or text of the
            UUID - represents the share network to use when creating a
            share group when driver_handles_share_servers = True.
        :param name: text - name of the new share group
        :param description: text - description of the share group
        :param source_share_group_snapshot: text - either instance of
            ShareGroupSnapshot or text with UUID from which this shar_group is
            to be created. May not be supplied when 'share_types' is provided.
        :param availability_zone: name of the availability zone where the
            group is to be created
        :rtype: :class:`ShareGroup`
        """

        if share_types and source_share_group_snapshot:
            raise ValueError('Cannot specify a share group with both'
                             'share_types and source_share_group_snapshot.')

        body = {}

        if name:
            body['name'] = name
        if description:
            body['description'] = description
        if availability_zone:
            body['availability_zone'] = availability_zone
        if share_group_type:
            body['share_group_type_id'] = common_base.getid(share_group_type)
        if share_network:
            body['share_network_id'] = common_base.getid(share_network)

        if source_share_group_snapshot:
            body['source_share_group_snapshot_id'] = common_base.getid(
                source_share_group_snapshot)
        elif share_types:
            body['share_types'] = [common_base.getid(share_type)
                                   for share_type in share_types]

        return self._create(
            RESOURCES_PATH, {RESOURCE_NAME: body}, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def get(self, share_group):
        """Get a share group.

        :param share_group: either ShareGroup object or text with its UUID
        :rtype: :class:`ShareGroup`
        """
        share_group_id = common_base.getid(share_group)
        url = RESOURCE_PATH % share_group_id
        return self._get(url, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def list(self, detailed=True, search_opts=None,
             sort_key=None, sort_dir=None):
        """Get a list of all share groups.

        :param detailed: Whether to return detailed share group info or not.
        :param search_opts: dict with search options to filter out groups.
            available keys include (('name1', 'name2', ...), 'type'):
            - ('offset', int)
            - ('limit', int)
            - ('all_tenants', int)
            - ('name', text)
            - ('status', text)
            - ('share_server_id', text)
            - ('share_group_type_id', text)
            - ('source_share_group_snapshot_id', text)
            - ('host', text)
            - ('share_network_id', text)
            - ('project_id', text)
        :param sort_key: Key to be sorted (i.e. 'created_at' or 'status').
        :param sort_dir: Sort direction, should be 'desc' or 'asc'.
        :rtype: list of :class:`ShareGroup`
        """

        search_opts = search_opts or {}

        if sort_key is not None:
            if sort_key in constants.SHARE_GROUP_SORT_KEY_VALUES:
                search_opts['sort_key'] = sort_key
                # NOTE(cknight): Replace aliases with appropriate keys
                if sort_key == 'share_group_type':
                    search_opts['sort_key'] = 'share_group_type_id'
                elif sort_key == 'share_network':
                    search_opts['sort_key'] = 'share_network_id'
            else:
                msg = 'sort_key must be one of the following: %s.'
                msg_args = ', '.join(constants.SHARE_GROUP_SORT_KEY_VALUES)
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
    def update(self, share_group, **kwargs):
        """Updates a share group.

        :param share_group: either ShareGroup object or text with its UUID
        :rtype: :class:`ShareGroup`
        """
        share_group_id = common_base.getid(share_group)
        url = RESOURCE_PATH % share_group_id
        if not kwargs:
            return self._get(url, RESOURCE_NAME)
        else:
            body = {RESOURCE_NAME: kwargs}
            return self._update(url, body, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def delete(self, share_group, force=False):
        """Delete a share group.

        :param share_group: either ShareGroup object or text with its UUID
        :param force: True to force the deletion
        """
        share_group_id = common_base.getid(share_group)
        if force:
            url = RESOURCE_PATH_ACTION % share_group_id
            body = {'force_delete': None}
            self.api.client.post(url, body=body)
        else:
            url = RESOURCE_PATH % share_group_id
            self._delete(url)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def reset_state(self, share_group, state):
        """Update the specified share group with the provided state.

        :param share_group: either ShareGroup object or text with its UUID
        :param state: The new state for the share group
        """

        share_group_id = common_base.getid(share_group)
        url = RESOURCE_PATH_ACTION % share_group_id
        body = {'reset_status': {'status': state}}
        self.api.client.post(url, body=body)
