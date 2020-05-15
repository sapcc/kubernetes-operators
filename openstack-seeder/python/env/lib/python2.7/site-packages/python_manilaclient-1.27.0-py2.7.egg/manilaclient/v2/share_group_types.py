# Copyright 2016 Clinton Knight
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Interface for share group types extension."""

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common.apiclient import base as common_base

RESOURCES_PATH = '/share-group-types'
RESOURCE_PATH = '/share-group-types/%s'
RESOURCE_PATH_ACTION = '/share-group-types/%s/action'
RESOURCES_NAME = 'share_group_types'
RESOURCE_NAME = 'share_group_type'

GROUP_SPECS_RESOURCES_PATH = '/share-group-types/%s/group-specs'
GROUP_SPECS_RESOURCE_PATH = '/share-group-types/%s/group-specs/%s'
GROUP_SPECS_RESOURCES_NAME = 'group_specs'


class ShareGroupType(common_base.Resource):
    """A Share Group Type is the type of share group to be created."""

    def __init__(self, manager, info, loaded=False):
        super(ShareGroupType, self).__init__(manager, info, loaded)
        self._group_specs = info.get(GROUP_SPECS_RESOURCES_NAME, {})

    def __repr__(self):
        return "<Share Group Type: %s>" % self.name

    @property
    def is_public(self):
        """Provide a user-friendly accessor to share-type-access."""
        return self._info.get('is_public', 'N/A')

    def get_keys(self, prefer_resource_data=True):
        """Get group specs from a share group type.

        :param prefer_resource_data: By default group_specs are retrieved from
            resource data, but user can force this method to make an API call
            and update the group specs in this object.
        :return: dict with group specs
        """
        if prefer_resource_data:
            return self._group_specs
        else:
            share_group_type_id = common_base.getid(self)
            url = GROUP_SPECS_RESOURCES_PATH % share_group_type_id
            _resp, body = self.manager.api.client.get(url)
            self._group_specs = body.get(GROUP_SPECS_RESOURCES_NAME, {})
            return self._group_specs

    def set_keys(self, group_specs):
        """Set group specs on a share group type.

        :param extra_specs: A dict of key/value pairs to be set on this object
        :return: dict with group specs
        """
        share_group_type_id = common_base.getid(self)
        url = GROUP_SPECS_RESOURCES_PATH % share_group_type_id
        body = {GROUP_SPECS_RESOURCES_NAME: group_specs}
        return self.manager._create(
            url, body, GROUP_SPECS_RESOURCES_NAME, return_raw=True)

    def unset_keys(self, keys):
        """Unset group specs on a share group type.

        :param keys: A list of keys on this object to be unset
        :return: None if successful, else API response on failure
        """
        share_group_type_id = common_base.getid(self)
        for k in keys:
            url = GROUP_SPECS_RESOURCE_PATH % (share_group_type_id, k)
            resp = self.manager._delete(url)
            if resp is not None:
                return resp


class ShareGroupTypeManager(base.ManagerWithFind):
    """Manage :class:`ShareGroupType` resources."""
    resource_class = ShareGroupType

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def create(self, name, share_types, is_public=False, group_specs=None):
        """Create a share group type.

        :param name: Descriptive name of the share group type
        :param share_types: list of either instances of ShareType or text
           with share type UUIDs
        :param is_public: True to create a public share group type
        :param group_specs: dict containing group spec key-value pairs
        :rtype: :class:`ShareGroupType`
        """
        if not share_types:
            raise ValueError('At least one share type must be specified when '
                             'creating a share group type.')
        body = {
            'name': name,
            'is_public': is_public,
            'group_specs': group_specs or {},
            'share_types': [common_base.getid(share_type)
                            for share_type in share_types],
        }
        return self._create(
            RESOURCES_PATH, {RESOURCE_NAME: body}, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def get(self, share_group_type="default"):
        """Get a specific share group type.

        :param share_group_type: either instance of ShareGroupType, or text
           with UUID, or 'default'
        :rtype: :class:`ShareGroupType`
        """
        share_group_type_id = common_base.getid(share_group_type)
        url = RESOURCE_PATH % share_group_type_id
        return self._get(url, RESOURCE_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def list(self, show_all=True, search_opts=None):
        """Get a list of all share group types.

        :rtype: list of :class:`ShareGroupType`.
        """
        query_string = '?is_public=all' if show_all else ''
        url = RESOURCES_PATH + query_string
        return self._list(url, RESOURCES_NAME)

    @api_versions.wraps("2.31")
    @api_versions.experimental_api
    def delete(self, share_group_type):
        """Delete a specific share group type.

        :param share_group_type: either instance of ShareGroupType, or text
           with UUID
        """
        share_group_type_id = common_base.getid(share_group_type)
        url = RESOURCE_PATH % share_group_type_id
        self._delete(url)
