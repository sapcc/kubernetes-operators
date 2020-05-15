# Copyright 2016 Mirantis, Inc.
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

RESOURCE_PATH_LEGACY = '/os-availability-zone'
RESOURCE_PATH = '/availability-zones'
RESOURCE_NAME = 'availability_zones'


class AvailabilityZone(common_base.Resource):

    def __repr__(self):
        return "<AvailabilityZone: %s>" % self.id


class AvailabilityZoneManager(base.Manager):
    """Manage :class:`Service` resources."""
    resource_class = AvailabilityZone

    @api_versions.wraps("1.0", "2.6")
    def list(self):
        return self._list(RESOURCE_PATH_LEGACY, RESOURCE_NAME)

    @api_versions.wraps("2.7")  # noqa
    def list(self):
        return self._list(RESOURCE_PATH, RESOURCE_NAME)
