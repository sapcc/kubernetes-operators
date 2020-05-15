# Copyright 2014 OpenStack Foundation
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

"""Volume type access interface."""

from cinderclient.apiclient import base as common_base
from cinderclient import base


class VolumeTypeAccess(base.Resource):
    def __repr__(self):
        return "<VolumeTypeAccess: %s>" % self.project_id


class VolumeTypeAccessManager(base.ManagerWithFind):
    """
    Manage :class:`VolumeTypeAccess` resources.
    """
    resource_class = VolumeTypeAccess

    def list(self, volume_type):
        return self._list(
            '/types/%s/os-volume-type-access' % base.getid(volume_type),
            'volume_type_access')

    def add_project_access(self, volume_type, project):
        """Add a project to the given volume type access list."""
        info = {'project': project}
        return self._action('addProjectAccess', volume_type, info)

    def remove_project_access(self, volume_type, project):
        """Remove a project from the given volume type access list."""
        info = {'project': project}
        return self._action('removeProjectAccess', volume_type, info)

    def _action(self, action, volume_type, info, **kwargs):
        """Perform a volume type action."""
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/types/%s/action' % base.getid(volume_type)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)
