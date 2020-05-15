# Copyright (C) 2013 Hewlett-Packard Development Company, L.P.
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

"""Volume transfer interface (v3 extension)."""

from cinderclient import base
from cinderclient.v2 import volume_transfers


class VolumeTransferManager(volume_transfers.VolumeTransferManager):
    def create(self, volume_id, name=None, no_snapshots=False):
        """Creates a volume transfer.

        :param volume_id: The ID of the volume to transfer.
        :param name: The name of the transfer.
        :param no_snapshots: Transfer volumes without snapshots.
        :rtype: :class:`VolumeTransfer`
        """
        body = {'transfer': {'volume_id': volume_id,
                             'name': name}}
        if self.api_version.matches('3.55'):
            body['transfer']['no_snapshots'] = no_snapshots
            return self._create('/volume-transfers', body, 'transfer')

        return self._create('/os-volume-transfer', body, 'transfer')

    def accept(self, transfer_id, auth_key):
        """Accept a volume transfer.

        :param transfer_id: The ID of the transfer to accept.
        :param auth_key: The auth_key of the transfer.
        :rtype: :class:`VolumeTransfer`
        """
        body = {'accept': {'auth_key': auth_key}}
        if self.api_version.matches('3.55'):
            return self._create('/volume-transfers/%s/accept' % transfer_id,
                                body, 'transfer')

        return self._create('/os-volume-transfer/%s/accept' % transfer_id,
                            body, 'transfer')

    def get(self, transfer_id):
        """Show details of a volume transfer.

        :param transfer_id: The ID of the volume transfer to display.
        :rtype: :class:`VolumeTransfer`
        """
        if self.api_version.matches('3.55'):
            return self._get("/volume-transfers/%s" % transfer_id, "transfer")

        return self._get("/os-volume-transfer/%s" % transfer_id, "transfer")

    def list(self, detailed=True, search_opts=None, sort=None):
        """Get a list of all volume transfer.

        :param detailed: Get detailed object information.
        :param search_opts: Filtering options.
        :param sort: Sort information
        :rtype: list of :class:`VolumeTransfer`
        """
        resource_type = 'os-volume-transfer'
        if self.api_version.matches('3.55'):
            resource_type = 'volume-transfers'

        url = self._build_list_url(resource_type, detailed=detailed,
                                   search_opts=search_opts,
                                   sort=sort)
        return self._list(url, 'transfers')

    def delete(self, transfer_id):
        """Delete a volume transfer.

        :param transfer_id: The :class:`VolumeTransfer` to delete.
        """
        if self.api_version.matches('3.55'):
            return self._delete(
                "/volume-transfers/%s" % base.getid(transfer_id))

        return self._delete("/os-volume-transfer/%s" % base.getid(transfer_id))
