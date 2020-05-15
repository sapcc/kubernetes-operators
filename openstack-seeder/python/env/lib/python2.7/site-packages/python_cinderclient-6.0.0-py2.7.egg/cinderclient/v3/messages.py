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

"""Message interface (v3 extension)."""

from cinderclient import api_versions
from cinderclient import base


class Message(base.Resource):
    NAME_ATTR = 'id'

    def __repr__(self):
        return "<Message: %s>" % self.id

    def delete(self):
        """Delete this message."""
        return self.manager.delete(self)


class MessageManager(base.ManagerWithFind):
    """Manage :class:`Message` resources."""
    resource_class = Message

    @api_versions.wraps('3.3')
    def get(self, message_id):
        """Get a message.

        :param message_id: The ID of the message to get.
        :rtype: :class:`Message`
        """
        return self._get("/messages/%s" % message_id, "message")

    @api_versions.wraps('3.3', '3.4')
    def list(self, **kwargs):
        """Lists all messages.

        :rtype: list of :class:`Message`
        """

        resource_type = "messages"
        url = self._build_list_url(resource_type, detailed=False)
        return self._list(url, resource_type)

    @api_versions.wraps('3.5')  # noqa: F811
    def list(self, search_opts=None, marker=None, limit=None, sort=None):
        """Lists all messages.

        :param search_opts: Search options to filter out volumes.
        :param marker: Begin returning volumes that appear later in the volume
                       list than that represented by this volume id.
        :param limit: Maximum number of volumes to return.
        :param sort: Sort information
        :rtype: list of :class:`Message`
        """
        resource_type = "messages"
        url = self._build_list_url(resource_type, detailed=False,
                                   search_opts=search_opts, marker=marker,
                                   limit=limit, sort=sort)
        return self._list(url, resource_type, limit=limit)

    @api_versions.wraps('3.3')
    def delete(self, message):
        """Delete a message."""

        loc = "/messages/%s" % base.getid(message)

        return self._delete(loc)
