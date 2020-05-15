# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
#
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

import json

from designateclient import client
from designateclient import utils
from designateclient import warlock


Server = warlock.model_factory(utils.load_schema('v1', 'server'))


class ServersController(client.CrudController):
    def list(self):
        """
        Retrieve a list of servers

        :returns: A list of :class:`Server`
        """
        response = self.client.get('/servers')

        return [Server(i) for i in response.json()['servers']]

    def get(self, server_id):
        """
        Retrieve a server

        :param server_id: Server Identifier
        :returns: :class:`Server`
        """
        response = self.client.get('/servers/%s' % server_id)

        return Server(response.json())

    def create(self, server):
        """
        Create a server

        :param server: A :class:`Server` to create
        :returns: :class:`Server`
        """
        response = self.client.post('/servers', data=json.dumps(server))

        return Server(response.json())

    def update(self, server):
        """
        Update a server

        :param server: A :class:`Server` to update
        :returns: :class:`Server`
        """
        response = self.client.put('/servers/%s' % server.id,
                                   data=json.dumps(server.changes))

        return Server(response.json())

    def delete(self, server):
        """
        Delete a server

        :param server: A :class:`Server`, or Server Identifier to delete
        """
        if isinstance(server, Server):
            self.client.delete('/servers/%s' % server.id)
        else:
            self.client.delete('/servers/%s' % server)
