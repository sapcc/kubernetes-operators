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

"""Asynchronous User Message interface."""
from manilaclient import api_versions
from manilaclient import base
from manilaclient.common.apiclient import base as common_base
from manilaclient.common import constants

RESOURCES_PATH = '/messages'
RESOURCE_PATH = '/messages/%s'
RESOURCES_NAME = 'messages'
RESOURCE_NAME = 'message'


class Message(common_base.Resource):
    NAME_ATTR = 'id'

    def __repr__(self):
        return "<Message: %s>" % self.id

    def delete(self):
        """Delete this message."""
        return self.manager.delete(self)


class MessageManager(base.ManagerWithFind):
    """Manage :class:`Message` resources."""
    resource_class = Message

    @api_versions.wraps('2.37')
    def get(self, message_id):
        """Get a message.

        :param message_id: The ID of the message to get.
        :rtype: :class:`Message`
        """
        return self._get(RESOURCE_PATH % message_id, RESOURCE_NAME)

    @api_versions.wraps('2.37')
    def list(self, search_opts=None, sort_key=None, sort_dir=None):
        """Lists all messages.

        :param search_opts: Search options to filter out messages.
        :rtype: list of :class:`Message`
        """
        search_opts = search_opts or {}

        if sort_key is not None:
            if sort_key in constants.MESSAGE_SORT_KEY_VALUES:
                search_opts['sort_key'] = sort_key
            else:
                raise ValueError(
                    'sort_key must be one of the following: %s.'
                    % ', '.join(constants.MESSAGE_SORT_KEY_VALUES))

        if sort_dir is not None:
            if sort_dir in constants.SORT_DIR_VALUES:
                search_opts['sort_dir'] = sort_dir
            else:
                raise ValueError('sort_dir must be one of the following: %s.'
                                 % ', '.join(constants.SORT_DIR_VALUES))

        query_string = self._build_query_string(search_opts)

        path = RESOURCES_PATH + query_string
        return self._list(path, RESOURCES_NAME)

    @api_versions.wraps('2.37')
    def delete(self, message):
        """Delete a message."""

        loc = RESOURCE_PATH % common_base.getid(message)

        return self._delete(loc)
