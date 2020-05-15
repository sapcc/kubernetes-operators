# Copyright (C) 2015 Hewlett-Packard Development Company, L.P.
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

"""Pools interface (v2 extension)"""

from cinderclient import base


class Pool(base.Resource):
    NAME_ATTR = 'name'

    def __repr__(self):
        return "<Pool: %s>" % self.name


class PoolManager(base.Manager):
    """Manage :class:`Pool` resources."""
    resource_class = Pool

    def list(self, detailed=False):
        """Lists all

        :rtype: list of :class:`Pool`
        """
        if detailed is True:
            pools = self._list("/scheduler-stats/get_pools?detail=True",
                               "pools")
            # Other than the name, all of the pool data is buried below in
            # a 'capabilities' dictionary. In order to be consistent with the
            # get-pools command line, these elements are moved up a level to
            # be attributes of the pool itself.
            for pool in pools:
                if hasattr(pool, 'capabilities'):
                    for k, v in pool.capabilities.items():
                        setattr(pool, k, v)

                    # Remove the capabilities dictionary since all of its
                    # elements have been copied up to the containing pool
                    del pool.capabilities
            return pools
        else:
            pools = self._list("/scheduler-stats/get_pools", "pools")

            # avoid cluttering the basic pool list with capabilities dict
            for pool in pools:
                if hasattr(pool, 'capabilities'):
                    del pool.capabilities
            return pools
