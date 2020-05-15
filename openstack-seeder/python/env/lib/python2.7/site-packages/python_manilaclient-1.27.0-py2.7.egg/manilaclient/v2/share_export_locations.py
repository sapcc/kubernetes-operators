# Copyright 2015 Mirantis inc.
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


class ShareExportLocation(common_base.Resource):
    """Resource class for a share export location."""

    def __repr__(self):
        return "<ShareExportLocation: %s>" % self.id

    def __getitem__(self, key):
        return self._info[key]


class ShareExportLocationManager(base.ManagerWithFind):
    """Manage :class:`ShareExportLocation` resources."""
    resource_class = ShareExportLocation

    @api_versions.wraps("2.9")
    def list(self, share, search_opts=None):
        """List all share export locations."""
        share_id = common_base.getid(share)
        return self._list("/shares/%s/export_locations" % share_id,
                          "export_locations")

    @api_versions.wraps("2.9")
    def get(self, share, export_location):
        """Get a share export location."""
        share_id = common_base.getid(share)
        export_location_id = common_base.getid(export_location)
        return self._get(
            "/shares/%(share_id)s/export_locations/%(export_location_id)s" % {
                "share_id": share_id,
                "export_location_id": export_location_id}, "export_location")
