# Copyright (c) 2015 Clinton Knight.  All rights reserved.
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

from manilaclient import base
from manilaclient.common.apiclient import base as common_base

RESOURCES_PATH = '/scheduler-stats/pools'
RESOURCES_NAME = 'pools'


class Pool(common_base.Resource):

    def __repr__(self):
        return "<Pool: %s>" % self.name


class PoolManager(base.Manager):
    """Manage :class:`Pool` resources."""
    resource_class = Pool

    def list(self, detailed=True, search_opts=None):
        """Get a list of pools.

        :rtype: list of :class:`Pool`
        """
        query_string = self._build_query_string(search_opts)
        if detailed:
            path = '%(resources_path)s/detail%(query)s' % {
                'resources_path': RESOURCES_PATH,
                'query': query_string
            }
        else:
            path = '%(resources_path)s%(query)s' % {
                'resources_path': RESOURCES_PATH,
                'query': query_string
            }

        return self._list(path, RESOURCES_NAME)
