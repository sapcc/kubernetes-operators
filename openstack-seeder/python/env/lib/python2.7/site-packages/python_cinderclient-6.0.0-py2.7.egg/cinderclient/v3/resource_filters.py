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

"""Resource filters interface."""

from cinderclient import api_versions
from cinderclient import base


class ResourceFilter(base.Resource):
    NAME_ATTR = 'resource'

    def __repr__(self):
        return "<ResourceFilter: %s>" % self.resource


class ResourceFilterManager(base.ManagerWithFind):
    """Manage :class:`ResourceFilter` resources."""

    resource_class = ResourceFilter

    @api_versions.wraps('3.33')
    def list(self, resource=None):
        """List all resource filters."""
        url = '/resource_filters'
        if resource is not None:
            url += '?resource=%s' % resource
        return self._list(url, "resource_filters")
