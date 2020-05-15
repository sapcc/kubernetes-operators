# Copyright (c) 2017 Hitachi Data Systems
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


class ShareSnapshotExportLocation(common_base.Resource):
    """Represent an export location snapshot of a snapshot."""

    def __repr__(self):
        return "<ShareSnapshotExportLocation: %s>" % self.id

    def __getitem__(self, key):
        return self._info[key]


class ShareSnapshotExportLocationManager(base.ManagerWithFind):
    """Manage :class:`ShareSnapshotExportLocation` resources."""
    resource_class = ShareSnapshotExportLocation

    @api_versions.wraps("2.32")
    def list(self, snapshot=None, search_opts=None):
        return self._list("/snapshots/%s/export-locations" %
                          common_base.getid(snapshot),
                          'share_snapshot_export_locations')

    @api_versions.wraps("2.32")
    def get(self, export_location, snapshot=None):
        params = {
            "snapshot_id": common_base.getid(snapshot),
            "export_location_id": common_base.getid(export_location),
        }

        return self._get("/snapshots/%(snapshot_id)s/export-locations/"
                         "%(export_location_id)s" % params,
                         "share_snapshot_export_location")
