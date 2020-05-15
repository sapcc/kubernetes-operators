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

import os

from keystoneauth1 import loading
from keystoneauth1 import plugin


class CinderNoAuthPlugin(plugin.BaseAuthPlugin):
    def __init__(self, user_id, project_id=None, roles=None, endpoint=None):
        self._user_id = user_id
        self._project_id = project_id if project_id else user_id
        self._endpoint = endpoint
        self._roles = roles
        self.auth_token = '%s:%s' % (self._user_id,
                                     self._project_id)

    def get_headers(self, session, **kwargs):
        return {'x-user-id': self._user_id,
                'x-project-id': self._project_id,
                'X-Auth-Token': self.auth_token}

    def get_user_id(self, session, **kwargs):
        return self._user_id

    def get_project_id(self, session, **kwargs):
        return self._project_id

    def get_endpoint(self, session, **kwargs):
        return '%s/%s' % (self._endpoint, self._project_id)

    def invalidate(self):
        pass


class CinderOpt(loading.Opt):
    @property
    def argparse_args(self):
        return ['--%s' % o.name for o in self._all_opts]

    @property
    def argparse_default(self):
        # select the first ENV that is not false-y or return None
        for o in self._all_opts:
            v = os.environ.get('Cinder_%s' % o.name.replace('-', '_').upper())
            if v:
                return v
        return self.default


class CinderNoAuthLoader(loading.BaseLoader):
    plugin_class = CinderNoAuthPlugin

    def get_options(self):
        options = super(CinderNoAuthLoader, self).get_options()
        options.extend([
            CinderOpt('user-id', help='User ID', required=True,
                      metavar="<cinder user id>"),
            CinderOpt('project-id', help='Project ID',
                      metavar="<cinder project id>"),
            CinderOpt('endpoint', help='Cinder endpoint',
                      dest="endpoint", required=True,
                      metavar="<cinder endpoint>"),
        ])
        return options
