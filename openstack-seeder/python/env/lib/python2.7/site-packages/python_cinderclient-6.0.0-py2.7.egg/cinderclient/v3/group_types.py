# Copyright (c) 2016 EMC Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Group Type interface."""

from six.moves.urllib import parse

from cinderclient import api_versions
from cinderclient import base


class GroupType(base.Resource):
    """A Group Type is the type of group to be created."""
    def __repr__(self):
        return "<GroupType: %s>" % self.name

    @property
    def is_public(self):
        """
        Provide a user-friendly accessor to is_public
        """
        return self._info.get("is_public",
                              self._info.get("is_public", 'N/A'))

    @api_versions.wraps("3.11")
    def get_keys(self):
        """Get group specs from a group type.

        :param type: The :class:`GroupType` to get specs from
        """
        _resp, body = self.manager.api.client.get(
            "/group_types/%s/group_specs" %
            base.getid(self))
        return body["group_specs"]

    @api_versions.wraps("3.11")
    def set_keys(self, metadata):
        """Set group specs on a group type.

        :param type : The :class:`GroupType` to set spec on
        :param metadata: A dict of key/value pairs to be set
        """
        body = {'group_specs': metadata}
        return self.manager._create(
            "/group_types/%s/group_specs" % base.getid(self),
            body,
            "group_specs",
            return_raw=True)

    @api_versions.wraps("3.11")
    def unset_keys(self, keys):
        """Unset specs on a group type.

        :param type_id: The :class:`GroupType` to unset spec on
        :param keys: A list of keys to be unset
        """

        for k in keys:
            resp = self.manager._delete(
                "/group_types/%s/group_specs/%s" % (
                base.getid(self), k))
            if resp:
                return resp


class GroupTypeManager(base.ManagerWithFind):
    """Manage :class:`GroupType` resources."""
    resource_class = GroupType

    @api_versions.wraps("3.11")
    def list(self, search_opts=None, is_public=None):
        """Lists all group types.

        :rtype: list of :class:`GroupType`.
        """
        if not search_opts:
            search_opts = dict()

        query_string = ''
        if 'is_public' not in search_opts:
            search_opts['is_public'] = is_public

        query_string = "?%s" % parse.urlencode(search_opts)
        return self._list("/group_types%s" % (query_string), "group_types")

    @api_versions.wraps("3.11")
    def get(self, group_type):
        """Get a specific group type.

        :param group_type: The ID of the :class:`GroupType` to get.
        :rtype: :class:`GroupType`
        """
        return self._get("/group_types/%s" % base.getid(group_type),
                         "group_type")

    @api_versions.wraps("3.11")
    def default(self):
        """Get the default group type.

        :rtype: :class:`GroupType`
        """
        return self._get("/group_types/default", "group_type")

    @api_versions.wraps("3.11")
    def delete(self, group_type):
        """Deletes a specific group_type.

        :param group_type: The name or ID of the :class:`GroupType` to get.
        """
        return self._delete("/group_types/%s" % base.getid(group_type))

    @api_versions.wraps("3.11")
    def create(self, name, description=None, is_public=True):
        """Creates a group type.

        :param name: Descriptive name of the group type
        :param description: Description of the group type
        :param is_public: Group type visibility
        :rtype: :class:`GroupType`
        """

        body = {
            "group_type": {
                "name": name,
                "description": description,
                "is_public": is_public,
            }
        }

        return self._create("/group_types", body, "group_type")

    @api_versions.wraps("3.11")
    def update(self, group_type, name=None, description=None, is_public=None):
        """Update the name and/or description for a group type.

        :param group_type: The ID of the :class:`GroupType` to update.
        :param name: Descriptive name of the group type.
        :param description: Description of the group type.
        :rtype: :class:`GroupType`
        """

        body = {
            "group_type": {
                "name": name,
                "description": description
            }
        }
        if is_public is not None:
            body["group_type"]["is_public"] = is_public

        return self._update("/group_types/%s" % base.getid(group_type),
                            body, response_key="group_type")
