# Copyright (C) 2016 EMC Corporation.
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

"""Group interface (v3 extension)."""
from cinderclient import api_versions
from cinderclient.apiclient import base as common_base
from cinderclient import base
from cinderclient import utils


class Group(base.Resource):
    """A Group of volumes."""
    def __repr__(self):
        return "<Group: %s>" % self.id

    def delete(self, delete_volumes=False):
        """Delete this group."""
        return self.manager.delete(self, delete_volumes)

    def update(self, **kwargs):
        """Update the name or description for this group."""
        return self.manager.update(self, **kwargs)

    def reset_state(self, state):
        """Reset the group's state with specified one"""
        return self.manager.reset_state(self, state)

    def enable_replication(self):
        """Enables replication for this group."""
        return self.manager.enable_replication(self)

    def disable_replication(self):
        """Disables replication for this group."""
        return self.manager.disable_replication(self)

    def failover_replication(self, allow_attached_volume=False,
                             secondary_backend_id=None):
        """Fails over replication for this group."""
        return self.manager.failover_replication(self,
            allow_attached_volume,
            secondary_backend_id)

    def list_replication_targets(self):
        """Lists replication targets for this group."""
        return self.manager.list_replication_targets(self)


class GroupManager(base.ManagerWithFind):
    """Manage :class:`Group` resources."""
    resource_class = Group

    @api_versions.wraps('3.13')
    def create(self, group_type, volume_types, name=None,
               description=None, user_id=None,
               project_id=None, availability_zone=None):
        """Creates a group.

        :param group_type: Type of the Group
        :param volume_types: Types of volume
        :param name: Name of the Group
        :param description: Description of the Group
        :param user_id: User id derived from context
        :param project_id: Project id derived from context
        :param availability_zone: Availability Zone to use
        :rtype: :class:`Group`
        """
        body = {'group': {'name': name,
                          'description': description,
                          'group_type': group_type,
                          'volume_types': volume_types.split(','),
                          'availability_zone': availability_zone,
                          }}

        return self._create('/groups', body, 'group')

    @api_versions.wraps('3.20')
    def reset_state(self, group, state):
        """Update the provided group with the provided state.

        :param group: The :class:`Group` to set the state.
        :param state: The state of the group to be set.
        """
        body = {'status': state} if state else {}
        return self._action('reset_status', group, body)

    @api_versions.wraps('3.14')
    def create_from_src(self, group_snapshot_id, source_group_id,
                        name=None, description=None, user_id=None,
                        project_id=None):
        """Creates a group from a group snapshot or a source group.

        :param group_snapshot_id: UUID of a GroupSnapshot
        :param source_group_id: UUID of a source Group
        :param name: Name of the Group
        :param description: Description of the Group
        :param user_id: User id derived from context
        :param project_id: Project id derived from context
        :rtype: A dictionary containing Group metadata
        """

        # NOTE(wanghao): According the API schema in cinder side, client
        # should NOT specify the group_snapshot_id and source_group_id at
        # same time, even one of them is None.
        if group_snapshot_id:
            create_key = 'group_snapshot_id'
            create_value = group_snapshot_id
        elif source_group_id:
            create_key = 'source_group_id'
            create_value = source_group_id

        body = {'create-from-src': {'name': name,
                                    'description': description,
                                    create_key: create_value}}

        self.run_hooks('modify_body_for_action', body,
                       'create-from-src')
        resp, body = self.api.client.post(
            "/groups/action", body=body)
        return common_base.DictWithMeta(body['group'], resp)

    @api_versions.wraps('3.13')
    def get(self, group_id, **kwargs):
        """Get a group.

        :param group_id: The ID of the group to get.
        :rtype: :class:`Group`
        """
        query_params = utils.unicode_key_value_to_string(kwargs)
        query_string = utils.build_query_param(query_params, sort=True)

        return self._get("/groups/%s" % group_id + query_string,
                         "group")

    @api_versions.wraps('3.13')
    def list(self, detailed=True, search_opts=None, list_volume=False):
        """Lists all groups.

        :rtype: list of :class:`Group`
        """
        if list_volume:
            if not search_opts:
                search_opts = {}
            search_opts['list_volume'] = True
        query_string = utils.build_query_param(search_opts, sort=True)

        detail = ""
        if detailed:
            detail = "/detail"

        return self._list("/groups%s%s" % (detail, query_string),
                          "groups")

    @api_versions.wraps('3.13')
    def delete(self, group, delete_volumes=False):
        """Delete a group.

        :param group: the :class:`Group` to delete.
        :param delete_volumes: delete volumes in the group.
        """
        body = {'delete': {'delete-volumes': delete_volumes}}
        self.run_hooks('modify_body_for_action', body, 'group')
        url = '/groups/%s/action' % base.getid(group)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)

    @api_versions.wraps('3.13')
    def update(self, group, **kwargs):
        """Update the name or description for a group.

        :param Group: The :class:`Group` to update.
        """
        if not kwargs:
            return

        body = {"group": kwargs}

        return self._update("/groups/%s" %
                            base.getid(group), body)

    def _action(self, action, group, info=None, **kwargs):
        """Perform a group "action."

        :param action: an action to be performed on the group
        :param group: a group to perform the action on
        :param info: details of the action
        :param **kwargs: other parameters
        """

        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/groups/%s/action' % base.getid(group)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)

    @api_versions.wraps('3.38')
    def enable_replication(self, group):
        """Enables replication for a group.

        :param group: the :class:`Group` to enable replication.
        """
        body = {'enable_replication': {}}
        self.run_hooks('modify_body_for_action', body, 'group')
        url = '/groups/%s/action' % base.getid(group)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)

    @api_versions.wraps('3.38')
    def disable_replication(self, group):
        """disables replication for a group.

        :param group: the :class:`Group` to disable replication.
        """
        body = {'disable_replication': {}}
        self.run_hooks('modify_body_for_action', body, 'group')
        url = '/groups/%s/action' % base.getid(group)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)

    @api_versions.wraps('3.38')
    def failover_replication(self, group, allow_attached_volume=False,
                             secondary_backend_id=None):
        """fails over replication for a group.

        :param group: the :class:`Group` to failover.
        :param allow attached volumes: allow attached volumes in the group.
        :param secondary_backend_id: secondary backend id.
        """
        body = {
            'failover_replication': {
                'allow_attached_volume': allow_attached_volume,
                'secondary_backend_id': secondary_backend_id
            }
        }
        self.run_hooks('modify_body_for_action', body, 'group')
        url = '/groups/%s/action' % base.getid(group)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)

    @api_versions.wraps('3.38')
    def list_replication_targets(self, group):
        """List replication targets for a group.

        :param group: the :class:`Group` to list replication targets.
        """
        body = {'list_replication_targets': {}}
        self.run_hooks('modify_body_for_action', body, 'group')
        url = '/groups/%s/action' % base.getid(group)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)
