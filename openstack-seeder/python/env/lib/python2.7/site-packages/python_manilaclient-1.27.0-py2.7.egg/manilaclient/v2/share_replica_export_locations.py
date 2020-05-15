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


class ShareReplicaExportLocation(common_base.Resource):
    """Resource class for a share replica export location."""

    def __repr__(self):
        return "<ShareReplicaExportLocation: %s>" % self.id

    def __getitem__(self, key):
        return self._info[key]


class ShareReplicaExportLocationManager(base.ManagerWithFind):
    """Manage :class:`ShareInstanceExportLocation` resources."""
    resource_class = ShareReplicaExportLocation

    @api_versions.wraps("2.47")
    @api_versions.experimental_api
    def list(self, share_replica, search_opts=None):
        """List all share replica export locations."""
        share_replica_id = common_base.getid(share_replica)
        return self._list(
            "/share-replicas/%s/export-locations" % share_replica_id,
            "export_locations")

    @api_versions.wraps("2.47")
    @api_versions.experimental_api
    def get(self, share_replica, export_location):
        """Get a share replica export location."""
        share_replica_id = common_base.getid(share_replica)
        export_location_id = common_base.getid(export_location)
        return self._get(
            ("/share-replicas/%(share_replica_id)s/export-locations/"
             "%(export_location_id)s") % {
                 "share_replica_id": share_replica_id,
                 "export_location_id": export_location_id,
            },
            "export_location")
