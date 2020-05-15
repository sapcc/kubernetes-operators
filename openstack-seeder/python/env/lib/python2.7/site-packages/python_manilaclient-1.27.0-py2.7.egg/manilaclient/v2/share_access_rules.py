# Copyright 2018 Huawei Corporation.
# All Rights Reserved.
#
# Copyright 2018
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
"""Interface for share access rules extension."""

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common.apiclient import base as common_base

RESOURCE_PATH = '/share-access-rules/%s'
RESOURCE_NAME = 'access'

RESOURCES_METADATA_PATH = '/share-access-rules/%s/metadata'
RESOURCE_METADATA_PATH = '/share-access-rules/%s/metadata/%s'
RESOURCE_LIST_PATH = '/share-access-rules'


class ShareAccessRule(common_base.Resource):
    """A Share Access Rule."""

    def __repr__(self):
        return "<Share Access Rule: %s>" % self.id

    def delete(self):
        """"Delete this share access rule."""
        self.manager.delete(self)


class ShareAccessRuleManager(base.ManagerWithFind):
    """Manage :class:`ShareAccessRule` resources."""

    resource_class = ShareAccessRule

    @api_versions.wraps("2.45")
    def get(self, share_access_rule):
        """Get a specific share access rule.

        :param share_access_rule: either instance of ShareAccessRule, or text
           with UUID
        :rtype: :class:`ShareAccessRule`
        """
        share_access_rule_id = common_base.getid(share_access_rule)
        url = RESOURCE_PATH % share_access_rule_id
        return self._get(url, RESOURCE_NAME)

    @api_versions.wraps("2.45")
    def set_metadata(self, access, metadata):
        """Set or update metadata for share access rule.

        :param share_access_rule: either share access rule object or
            text with its ID.
        :param metadata: A list of keys to be set.
        """
        body = {'metadata': metadata}
        access_id = common_base.getid(access)
        url = RESOURCES_METADATA_PATH % access_id
        return self._update(url, body, "metadata")

    @api_versions.wraps("2.45")
    def unset_metadata(self, access, keys):
        """Unset metadata on a share access rule.

        :param keys: A list of keys on this object to be unset
        :return: None if successful, else API response on failure
        """
        for k in keys:
            url = RESOURCE_METADATA_PATH % (common_base.getid(access), k)
            self._delete(url)

    @api_versions.wraps("2.45")
    def access_list(self, share, search_opts=None):
        search_opts = search_opts or {}
        search_opts['share_id'] = common_base.getid(share)
        query_string = self._build_query_string(search_opts)
        url = RESOURCE_LIST_PATH + query_string
        return self._list(url, 'access_list')
