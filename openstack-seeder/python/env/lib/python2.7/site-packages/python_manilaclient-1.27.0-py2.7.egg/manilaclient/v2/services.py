# Copyright 2014 OpenStack Foundation
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

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common.apiclient import base as common_base

RESOURCE_PATH_LEGACY = '/os-services'
RESOURCE_PATH = '/services'
RESOURCE_NAME = 'services'


class Service(common_base.Resource):

    def __repr__(self):
        return "<Service: %s>" % self.id

    def server_api_version(self, **kwargs):
        """Get api version."""
        return self.manager.api_version(self, kwargs)


class ServiceManager(base.Manager):
    """Manage :class:`Service` resources."""
    resource_class = Service

    def _do_list(self, search_opts=None, resource_path=RESOURCE_PATH):
        """Get a list of all services.

        :rtype: list of :class:`Service`
        """
        query_string = self._build_query_string(search_opts)
        return self._list(resource_path + query_string, RESOURCE_NAME)

    @api_versions.wraps("1.0", "2.6")
    def list(self, search_opts=None):
        return self._do_list(
            search_opts=search_opts, resource_path=RESOURCE_PATH_LEGACY)

    @api_versions.wraps("2.7")  # noqa
    def list(self, search_opts=None):
        return self._do_list(
            search_opts=search_opts, resource_path=RESOURCE_PATH)

    def _do_enable(self, host, binary, resource_path=RESOURCE_PATH):
        """Enable the service specified by hostname and binary."""
        body = {"host": host, "binary": binary}
        return self._update("%s/enable" % resource_path, body)

    @api_versions.wraps("1.0", "2.6")
    def enable(self, host, binary):
        return self._do_enable(host, binary, RESOURCE_PATH_LEGACY)

    @api_versions.wraps("2.7")  # noqa
    def enable(self, host, binary):
        return self._do_enable(host, binary, RESOURCE_PATH)

    def _do_disable(self, host, binary, resource_path=RESOURCE_PATH):
        """Disable the service specified by hostname and binary."""
        body = {"host": host, "binary": binary}
        return self._update("%s/disable" % resource_path, body)

    @api_versions.wraps("1.0", "2.6")
    def disable(self, host, binary):
        return self._do_disable(host, binary, RESOURCE_PATH_LEGACY)

    @api_versions.wraps("2.7")  # noqa
    def disable(self, host, binary):
        return self._do_disable(host, binary, RESOURCE_PATH)

    def server_api_version(self, url_append=""):
        """Returns the API Version supported by the server.

        :param url_append: String to append to url to obtain specific version
        :return: Returns response obj for a server that supports microversions.
                 Returns an empty list for Kilo and prior Manila servers.
        """
        try:
            return self._get_with_base_url(url_append, 'versions')
        except LookupError:
            return []
