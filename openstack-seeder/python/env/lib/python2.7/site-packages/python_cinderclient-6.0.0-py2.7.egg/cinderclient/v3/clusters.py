# Copyright (c) 2016 Red Hat, Inc.
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

"""
Interface to clusters API
"""
from cinderclient import api_versions
from cinderclient import base


class Cluster(base.Resource):
    def __repr__(self):
        return "<Cluster: %s (id: %s)>" % (self.name, self.id)


class ClusterManager(base.ManagerWithFind):
    resource_class = Cluster
    base_url = '/clusters'

    def _build_url(self, url_path=None, **kwargs):
        url = self.base_url + ('/' + url_path if url_path else '')
        filters = {'%s=%s' % (k, v) for k, v in kwargs.items() if v}
        if filters:
            url = "%s?%s" % (url, "&".join(filters))
        return url

    @api_versions.wraps("3.7")
    def list(self, name=None, binary=None, is_up=None, disabled=None,
             num_hosts=None, num_down_hosts=None, detailed=False):
        """Clustered Service list.

        :param name: filter by cluster name.
        :param binary: filter by cluster binary.
        :param is_up: filtering by up/down status.
        :param disabled: filtering by disabled status.
        :param num_hosts: filtering by number of hosts.
        :param num_down_hosts: filtering by number of hosts that are down.
        :param detailed: retrieve simple or detailed list.
        """
        url_path = 'detail' if detailed else None
        url = self._build_url(url_path, name=name, binary=binary, is_up=is_up,
                              disabled=disabled, num_hosts=num_hosts,
                              num_down_hosts=num_down_hosts)
        return self._list(url, 'clusters')

    @api_versions.wraps("3.7")
    def show(self, name, binary=None):
        """Clustered Service show.

        :param name: Cluster name.
        :param binary: Clustered service binary.
        """
        url = self._build_url(name, binary=binary)
        resp, body = self.api.client.get(url)
        return self.resource_class(self, body['cluster'], loaded=True,
                                   resp=resp)

    @api_versions.wraps("3.7")
    def update(self, name, binary, disabled, disabled_reason=None):
        """Enable or disable a clustered service.

        :param name: Cluster name.
        :param binary: Clustered service binary.
        :param disabled: Boolean determining desired disabled status.
        :param disabled_reason: Value to pass as disabled reason.
        """
        url_path = 'disable' if disabled else 'enable'
        url = self._build_url(url_path)

        body = {'name': name, 'binary': binary}
        if disabled and disabled_reason:
            body['disabled_reason'] = disabled_reason
        result = self._update(url, body)
        return self.resource_class(self, result['cluster'], loaded=True,
                                   resp=result.request_ids)
