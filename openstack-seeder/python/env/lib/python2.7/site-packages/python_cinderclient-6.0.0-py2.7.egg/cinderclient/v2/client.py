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

import logging

from cinderclient import api_versions
from cinderclient import client
from cinderclient.v2 import availability_zones
from cinderclient.v2 import capabilities
from cinderclient.v2 import cgsnapshots
from cinderclient.v2 import consistencygroups
from cinderclient.v2 import limits
from cinderclient.v2 import pools
from cinderclient.v2 import qos_specs
from cinderclient.v2 import quota_classes
from cinderclient.v2 import quotas
from cinderclient.v2 import services
from cinderclient.v2 import volume_backups
from cinderclient.v2 import volume_backups_restore
from cinderclient.v2 import volume_encryption_types
from cinderclient.v2 import volume_snapshots
from cinderclient.v2 import volume_transfers
from cinderclient.v2 import volume_type_access
from cinderclient.v2 import volume_types
from cinderclient.v2 import volumes


class Client(object):
    """Top-level object to access the OpenStack Volume API.

    Create an instance with your creds::

        >>> client = Client(USERNAME, PASSWORD, PROJECT_ID, AUTH_URL)

    Then call methods on its managers::

        >>> client.volumes.list()
        ...
    """

    def __init__(self, username=None, api_key=None, project_id=None,
                 auth_url='', insecure=False, timeout=None, tenant_id=None,
                 proxy_tenant_id=None, proxy_token=None, region_name=None,
                 endpoint_type='publicURL', extensions=None,
                 service_type='volumev2', service_name=None,
                 volume_service_name=None, bypass_url=None, retries=0,
                 http_log_debug=False, cacert=None, auth_system='keystone',
                 auth_plugin=None, session=None, api_version=None,
                 logger=None, **kwargs):
        # FIXME(comstud): Rename the api_key argument above when we
        # know it's not being used as keyword argument
        password = api_key
        self.version = '2.0'
        self.limits = limits.LimitsManager(self)

        # extensions
        self.volumes = volumes.VolumeManager(self)
        self.volume_snapshots = volume_snapshots.SnapshotManager(self)
        self.volume_types = volume_types.VolumeTypeManager(self)
        self.volume_type_access = \
            volume_type_access.VolumeTypeAccessManager(self)
        self.volume_encryption_types = \
            volume_encryption_types.VolumeEncryptionTypeManager(self)
        self.qos_specs = qos_specs.QoSSpecsManager(self)
        self.quota_classes = quota_classes.QuotaClassSetManager(self)
        self.quotas = quotas.QuotaSetManager(self)
        self.backups = volume_backups.VolumeBackupManager(self)
        self.restores = volume_backups_restore.VolumeBackupRestoreManager(self)
        self.transfers = volume_transfers.VolumeTransferManager(self)
        self.services = services.ServiceManager(self)
        self.consistencygroups = consistencygroups.\
            ConsistencygroupManager(self)
        self.cgsnapshots = cgsnapshots.CgsnapshotManager(self)
        self.availability_zones = \
            availability_zones.AvailabilityZoneManager(self)
        self.pools = pools.PoolManager(self)
        self.capabilities = capabilities.CapabilitiesManager(self)
        self.api_version = api_version or api_versions.APIVersion(self.version)

        # Add in any extensions...
        if extensions:
            for extension in extensions:
                if extension.manager_class:
                    setattr(self, extension.name,
                            extension.manager_class(self))

        if not logger:
            logger = logging.getLogger(__name__)

        self.client = client._construct_http_client(
            username=username,
            password=password,
            project_id=project_id,
            auth_url=auth_url,
            insecure=insecure,
            timeout=timeout,
            tenant_id=tenant_id,
            proxy_tenant_id=tenant_id,
            proxy_token=proxy_token,
            region_name=region_name,
            endpoint_type=endpoint_type,
            service_type=service_type,
            service_name=service_name,
            volume_service_name=volume_service_name,
            bypass_url=bypass_url,
            retries=retries,
            http_log_debug=http_log_debug,
            cacert=cacert,
            auth_system=auth_system,
            auth_plugin=auth_plugin,
            session=session,
            api_version=self.api_version,
            logger=logger,
            **kwargs)

    def authenticate(self):
        """Authenticate against the server.

        Normally this is called automatically when you first access the API,
        but you can call this method to force authentication right now.

        Returns on success; raises :exc:`exceptions.Unauthorized` if the
        credentials are wrong.
        """
        self.client.authenticate()

    def get_volume_api_version_from_endpoint(self):
        return self.client.get_volume_api_version_from_endpoint()
