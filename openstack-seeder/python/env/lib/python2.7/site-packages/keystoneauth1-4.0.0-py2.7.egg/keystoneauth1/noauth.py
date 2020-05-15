# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from keystoneauth1 import plugin


class NoAuth(plugin.BaseAuthPlugin):
    """A provider that will always use no auth.

    This is useful to unify session/adapter loading for services
    that might be deployed in standalone/noauth mode.
    """

    def __init__(self, endpoint=None):
        super(NoAuth, self).__init__()
        self.endpoint = endpoint

    def get_token(self, session, **kwargs):
        return 'notused'

    def get_endpoint(self, session, **kwargs):
        """Return the supplied endpoint.

        Using this plugin the same endpoint is returned regardless of the
        parameters passed to the plugin. endpoint_override overrides the
        endpoint specified when constructing the plugin.
        """
        return kwargs.get('endpoint_override') or self.endpoint
