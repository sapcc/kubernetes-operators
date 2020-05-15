# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Author: Endre Karlson <endre.karlson@hp.com>
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
from oslo_utils import uuidutils
import six

from designateclient.v2.base import V2Controller
from designateclient.v2 import utils as v2_utils


class RecordSetController(V2Controller):
    def _canonicalize_record_name(self, zone, name):
        zone_info = None

        # If we get a zone name we'll need to get the ID of it before POST.
        if isinstance(zone, six.string_types) and not \
                uuidutils.is_uuid_like(zone):
                zone_info = self.client.zones.get(zone)
        elif isinstance(zone, dict):
            zone_info = zone

        # We where given a name like "www" vs www.i.io., attempt to fix it on
        # the behalf of the actor.
        if not name.endswith("."):
            if not isinstance(zone_info, dict):
                zone_info = self.client.zones.get(zone)

            name = "%s.%s" % (name, zone_info["name"])

        return name, zone_info

    def create(self, zone, name, type_, records, description=None,
               ttl=None):
        name, zone_info = self._canonicalize_record_name(zone, name)

        data = {
            'name': name,
            'type': type_,
            'records': records
        }

        if ttl is not None:
            data['ttl'] = ttl

        if description is not None:
            data['description'] = description

        if zone_info is not None:
            zone_id = zone_info["id"]
        else:
            zone_id = zone

        url = '/zones/%s/recordsets' % zone_id
        return self._post(url, data=data)

    def list(self, zone, criterion=None, marker=None, limit=None):
        zone = v2_utils.resolve_by_name(self.client.zones.list, zone)

        url = self.build_url(
            '/zones/%s/recordsets' % zone,
            criterion, marker, limit)

        return self._get(url, response_key='recordsets')

    def list_all_zones(self, criterion=None, marker=None, limit=None):

        url = self.build_url('/recordsets', criterion, marker, limit)

        return self._get(url, response_key='recordsets')

    def get(self, zone, recordset):
        zone = v2_utils.resolve_by_name(self.client.zones.list, zone)
        recordset = v2_utils.resolve_by_name(self.list, recordset, zone)

        url = self.build_url('/zones/%s/recordsets/%s' % (
                             zone, recordset))

        return self._get(url)

    def update(self, zone, recordset, values):
        zone = v2_utils.resolve_by_name(self.client.zones.list, zone)
        recordset = v2_utils.resolve_by_name(self.list, recordset, zone)

        url = '/zones/%s/recordsets/%s' % (zone, recordset)

        return self._put(url, data=values)

    def delete(self, zone, recordset):
        zone = v2_utils.resolve_by_name(self.client.zones.list, zone)
        recordset = v2_utils.resolve_by_name(self.list, recordset, zone)

        url = '/zones/%s/recordsets/%s' % (zone, recordset)

        return self._delete(url)
