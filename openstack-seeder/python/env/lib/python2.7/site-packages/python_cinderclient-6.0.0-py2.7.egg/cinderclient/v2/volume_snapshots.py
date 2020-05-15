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

"""Volume snapshot interface (v2 extension)."""

from cinderclient import api_versions
from cinderclient.v3 import volume_snapshots


class Snapshot(volume_snapshots.Snapshot):
    def list_manageable(self, host, detailed=True, marker=None, limit=None,
                        offset=None, sort=None):
        return self.manager.list_manageable(host, detailed=detailed,
                                            marker=marker, limit=limit,
                                            offset=offset, sort=sort)


class SnapshotManager(volume_snapshots.SnapshotManager):
    resource_class = Snapshot

    @api_versions.wraps("2.0")
    def list_manageable(self, host, detailed=True, marker=None, limit=None,
                        offset=None, sort=None):
        url = self._build_list_url("os-snapshot-manage", detailed=detailed,
                                   search_opts={'host': host}, marker=marker,
                                   limit=limit, offset=offset, sort=sort)
        return self._list(url, "manageable-snapshots")
