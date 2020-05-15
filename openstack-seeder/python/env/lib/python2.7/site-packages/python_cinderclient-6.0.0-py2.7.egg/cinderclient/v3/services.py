# Copyright (c) 2013 OpenStack Foundation
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
service interface
"""

from cinderclient import api_versions
from cinderclient import base
from cinderclient.v2 import services

Service = services.Service


class LogLevel(base.Resource):
    def __repr__(self):
        return '<LogLevel: binary=%s host=%s prefix=%s level=%s>' % (
            self.binary, self.host, self.prefix, self.level)


class ServiceManager(services.ServiceManager):
    @api_versions.wraps("3.0")
    def server_api_version(self):
        """Returns the API Version supported by the server.

        :return: Returns response obj for a server that supports microversions.
                 Returns an empty list for Liberty and prior Cinder servers.
        """

        try:
            return self._get_with_base_url("", response_key='versions')
        except LookupError:
            return []

    @api_versions.wraps("3.32")
    def set_log_levels(self, level, binary, server, prefix):
        """Set log level for services."""
        body = {'level': level, 'binary': binary, 'server': server,
                'prefix': prefix}
        return self._update("/os-services/set-log", body)

    @api_versions.wraps("3.32")
    def get_log_levels(self, binary, server, prefix):
        """Get log levels for services."""
        body = {'binary': binary, 'server': server, 'prefix': prefix}
        response = self._update("/os-services/get-log", body)

        log_levels = []
        for entry in response['log_levels']:
            entry_levels = sorted(entry['levels'].items(), key=lambda x: x[0])
            for prefix, level in entry_levels:
                log_dict = {'binary': entry['binary'], 'host': entry['host'],
                            'prefix': prefix, 'level': level}
                log_levels.append(LogLevel(self, log_dict, loaded=True))
        return log_levels
