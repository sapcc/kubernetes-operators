# Copyright (C) 2012 - 2014 EMC Corporation.
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

"""cgsnapshot interface (v2 extension)."""

from cinderclient.apiclient import base as common_base
from cinderclient import base
from cinderclient import utils


class Cgsnapshot(base.Resource):
    """A cgsnapshot is snapshot of a consistency group."""
    def __repr__(self):
        return "<cgsnapshot: %s>" % self.id

    def delete(self):
        """Delete this cgsnapshot."""
        return self.manager.delete(self)

    def update(self, **kwargs):
        """Update the name or description for this cgsnapshot."""
        return self.manager.update(self, **kwargs)


class CgsnapshotManager(base.ManagerWithFind):
    """Manage :class:`Cgsnapshot` resources."""
    resource_class = Cgsnapshot

    def create(self, consistencygroup_id, name=None, description=None,
               user_id=None,
               project_id=None):
        """Creates a cgsnapshot.

        :param consistencygroup: Name or uuid of a consistency group
        :param name: Name of the cgsnapshot
        :param description: Description of the cgsnapshot
        :param user_id: User id derived from context
        :param project_id: Project id derived from context
        :rtype: :class:`Cgsnapshot`
       """

        body = {'cgsnapshot': {'consistencygroup_id': consistencygroup_id,
                               'name': name,
                               'description': description,
                               'user_id': user_id,
                               'project_id': project_id,
                               'status': "creating",
                               }}

        return self._create('/cgsnapshots', body, 'cgsnapshot')

    def get(self, cgsnapshot_id):
        """Get a cgsnapshot.

        :param cgsnapshot_id: The ID of the cgsnapshot to get.
        :rtype: :class:`Cgsnapshot`
        """
        return self._get("/cgsnapshots/%s" % cgsnapshot_id, "cgsnapshot")

    def list(self, detailed=True, search_opts=None):
        """Lists all cgsnapshots.

        :rtype: list of :class:`Cgsnapshot`
        """
        query_string = utils.build_query_param(search_opts)

        detail = ""
        if detailed:
            detail = "/detail"

        return self._list("/cgsnapshots%s%s" % (detail, query_string),
                          "cgsnapshots")

    def delete(self, cgsnapshot):
        """Delete a cgsnapshot.

        :param cgsnapshot: The :class:`Cgsnapshot` to delete.
        """
        return self._delete("/cgsnapshots/%s" % base.getid(cgsnapshot))

    def update(self, cgsnapshot, **kwargs):
        """Update the name or description for a cgsnapshot.

        :param cgsnapshot: The :class:`Cgsnapshot` to update.
        """
        if not kwargs:
            return

        body = {"cgsnapshot": kwargs}

        return self._update("/cgsnapshots/%s" % base.getid(cgsnapshot), body)

    def _action(self, action, cgsnapshot, info=None, **kwargs):
        """Perform a cgsnapshot "action."
        """
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/cgsnapshots/%s/action' % base.getid(cgsnapshot)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)
