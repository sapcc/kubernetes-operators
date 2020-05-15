# Copyright 2013 OpenStack Foundation
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

RESOURCE_PATH_LEGACY = '/os-quota-sets'
RESOURCE_PATH = '/quota-sets'


class QuotaSet(common_base.Resource):

    @property
    def id(self):
        """Needed by Resource to self-refresh and be indexed."""
        return self.tenant_id

    def update(self, *args, **kwargs):
        self.manager.update(self.tenant_id, *args, **kwargs)


class QuotaSetManager(base.ManagerWithFind):
    resource_class = QuotaSet

    def _check_user_id_and_share_type_args(self, user_id, share_type):
        if user_id and share_type:
            raise ValueError(
                "'user_id' and 'share_type' values are mutually exclusive. "
                "one or both should be unset.")

    def _do_get(self, tenant_id, user_id=None, share_type=None, detail=False,
                resource_path=RESOURCE_PATH):
        self._check_user_id_and_share_type_args(user_id, share_type)
        if hasattr(tenant_id, 'tenant_id'):
            tenant_id = tenant_id.tenant_id

        if detail:
            query = '/detail'
        else:
            query = ''

        if user_id and share_type:
            query = '%s?user_id=%s&share_type=%s' % (
                query, user_id, share_type)
        elif user_id:
            query = '%s?user_id=%s' % (query, user_id)
        elif share_type:
            query = '%s?share_type=%s' % (query, share_type)
        data = {
            "resource_path": resource_path,
            "tenant_id": tenant_id,
        }

        url = ("%(resource_path)s/%(tenant_id)s" + query) % data
        return self._get(url, "quota_set")

    @api_versions.wraps("1.0", "2.6")
    def get(self, tenant_id, user_id=None, detail=False):
        return self._do_get(tenant_id, user_id,
                            resource_path=RESOURCE_PATH_LEGACY)

    @api_versions.wraps("2.7", "2.24")  # noqa
    def get(self, tenant_id, user_id=None, detail=False):
        return self._do_get(tenant_id, user_id,
                            resource_path=RESOURCE_PATH)

    @api_versions.wraps("2.25", "2.38")  # noqa
    def get(self, tenant_id, user_id=None, detail=False):
        return self._do_get(tenant_id, user_id, detail=detail,
                            resource_path=RESOURCE_PATH)

    @api_versions.wraps("2.39")  # noqa
    def get(self, tenant_id, user_id=None, share_type=None, detail=False):
        return self._do_get(
            tenant_id, user_id, share_type=share_type, detail=detail,
            resource_path=RESOURCE_PATH)

    def _do_update(self, tenant_id, shares=None, snapshots=None,
                   gigabytes=None, snapshot_gigabytes=None,
                   share_networks=None,
                   force=None, user_id=None, share_type=None,
                   share_groups=None, share_group_snapshots=None,
                   resource_path=RESOURCE_PATH):
        self._check_user_id_and_share_type_args(user_id, share_type)
        body = {
            'quota_set': {
                'tenant_id': tenant_id,
                'shares': shares,
                'snapshots': snapshots,
                'gigabytes': gigabytes,
                'snapshot_gigabytes': snapshot_gigabytes,
                'share_networks': share_networks,
                'share_groups': share_groups,
                'share_group_snapshots': share_group_snapshots,
                'force': force,
            },
        }

        for key in list(body['quota_set']):
            if body['quota_set'][key] is None:
                body['quota_set'].pop(key)
        data = {
            "resource_path": resource_path,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "st": share_type,
        }
        if user_id:
            url = '%(resource_path)s/%(tenant_id)s?user_id=%(user_id)s' % data
        elif share_type:
            url = '%(resource_path)s/%(tenant_id)s?share_type=%(st)s' % data
        else:
            url = "%(resource_path)s/%(tenant_id)s" % data

        return self._update(url, body, 'quota_set')

    @api_versions.wraps("1.0", "2.6")
    def update(self, tenant_id, shares=None, snapshots=None, gigabytes=None,
               snapshot_gigabytes=None, share_networks=None, force=None,
               user_id=None):
        return self._do_update(
            tenant_id, shares, snapshots, gigabytes, snapshot_gigabytes,
            share_networks, force, user_id, resource_path=RESOURCE_PATH_LEGACY,
        )

    @api_versions.wraps("2.7", "2.38")  # noqa
    def update(self, tenant_id, shares=None, snapshots=None, gigabytes=None,
               snapshot_gigabytes=None, share_networks=None, force=None,
               user_id=None):
        return self._do_update(
            tenant_id, shares, snapshots, gigabytes, snapshot_gigabytes,
            share_networks, force, user_id, resource_path=RESOURCE_PATH,
        )

    @api_versions.wraps("2.39", "2.39")  # noqa
    def update(self, tenant_id, user_id=None, share_type=None,
               shares=None, snapshots=None, gigabytes=None,
               snapshot_gigabytes=None, share_networks=None, force=None):
        if share_type and share_networks:
            raise ValueError(
                "'share_networks' quota can be set only for project or user, "
                "not share type.")
        return self._do_update(
            tenant_id, shares, snapshots, gigabytes, snapshot_gigabytes,
            share_networks, force, user_id,
            share_type=share_type,
            resource_path=RESOURCE_PATH,
        )

    @api_versions.wraps("2.40")  # noqa
    def update(self, tenant_id, user_id=None, share_type=None,
               shares=None, snapshots=None, gigabytes=None,
               snapshot_gigabytes=None, share_networks=None,
               share_groups=None, share_group_snapshots=None,
               force=None):
        if share_type and share_networks:
            raise ValueError(
                "'share_networks' quota can be set only for project or user, "
                "not share type.")
        return self._do_update(
            tenant_id, shares, snapshots, gigabytes, snapshot_gigabytes,
            share_networks, force, user_id,
            share_type=share_type,
            share_groups=share_groups,
            share_group_snapshots=share_group_snapshots,
            resource_path=RESOURCE_PATH,
        )

    @api_versions.wraps("1.0", "2.6")
    def defaults(self, tenant_id):
        return self._get(
            "%(resource_path)s/%(tenant_id)s/defaults" % {
                "resource_path": RESOURCE_PATH_LEGACY, "tenant_id": tenant_id},
            "quota_set")

    @api_versions.wraps("2.7")  # noqa
    def defaults(self, tenant_id):
        return self._get(
            "%(resource_path)s/%(tenant_id)s/defaults" % {
                "resource_path": RESOURCE_PATH, "tenant_id": tenant_id},
            "quota_set")

    def _do_delete(self, tenant_id, user_id=None, share_type=None,
                   resource_path=RESOURCE_PATH):
        self._check_user_id_and_share_type_args(user_id, share_type)
        data = {
            "resource_path": resource_path,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "st": share_type,
        }
        if user_id:
            url = '%(resource_path)s/%(tenant_id)s?user_id=%(user_id)s' % data
        elif share_type:
            url = '%(resource_path)s/%(tenant_id)s?share_type=%(st)s' % data
        else:
            url = '%(resource_path)s/%(tenant_id)s' % data
        self._delete(url)

    @api_versions.wraps("1.0", "2.6")
    def delete(self, tenant_id, user_id=None):
        return self._do_delete(
            tenant_id, user_id, resource_path=RESOURCE_PATH_LEGACY)

    @api_versions.wraps("2.7", "2.38")  # noqa
    def delete(self, tenant_id, user_id=None):
        return self._do_delete(tenant_id, user_id, resource_path=RESOURCE_PATH)

    @api_versions.wraps("2.39")  # noqa
    def delete(self, tenant_id, user_id=None, share_type=None):
        return self._do_delete(
            tenant_id, user_id, share_type, resource_path=RESOURCE_PATH)
