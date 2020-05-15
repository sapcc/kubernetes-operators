# Copyright 2014 Mirantis Inc.
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

import re
import traceback

from oslo_log import log
from tempest.lib.cli import base
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc

from manilaclient.common import constants
from manilaclient import config
from manilaclient.tests.functional import client
from manilaclient.tests.functional import utils

CONF = config.CONF
LOG = log.getLogger(__name__)


class handle_cleanup_exceptions(object):
    """Handle exceptions raised with cleanup operations.

    Always suppress errors when lib_exc.NotFound or lib_exc.Forbidden
    are raised.
    Suppress all other exceptions only in case config opt
    'suppress_errors_in_cleanup' is True.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if isinstance(exc_value, (lib_exc.NotFound, lib_exc.Forbidden)):
            return True
        elif CONF.suppress_errors_in_cleanup:
            LOG.error("Suppressed cleanup error: \n%s", traceback.format_exc())
            return True
        return False  # Don't suppress cleanup errors


class BaseTestCase(base.ClientTestBase):

    # Will be cleaned up after test suite run
    class_resources = []

    # Will be cleaned up after single test run
    method_resources = []

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.addCleanup(self.clear_resources)

    @classmethod
    def tearDownClass(cls):
        super(BaseTestCase, cls).tearDownClass()
        cls.clear_resources(cls.class_resources)

    @classmethod
    def clear_resources(cls, resources=None):
        """Deletes resources, that were created in test suites.

        This method tries to remove resources from resource list,
        if it is not found, assume it was deleted in test itself.
        It is expected, that all resources were added as LIFO
        due to restriction of deletion resources, that are in the chain.
        :param resources: dict with keys 'type','id','client' and 'deleted'
        """

        if resources is None:
            resources = cls.method_resources
        for res in resources:
            if "deleted" not in res:
                res["deleted"] = False
            if "client" not in res:
                res["client"] = cls.get_cleanup_client()
            if not(res["deleted"]):
                res_id = res["id"]
                client = res["client"]
                with handle_cleanup_exceptions():
                    # TODO(vponomaryov): add support for other resources
                    if res["type"] is "share_type":
                        client.delete_share_type(
                            res_id, microversion=res["microversion"])
                        client.wait_for_share_type_deletion(
                            res_id, microversion=res["microversion"])
                    elif res["type"] is "share_network":
                        client.delete_share_network(
                            res_id, microversion=res["microversion"])
                        client.wait_for_share_network_deletion(
                            res_id, microversion=res["microversion"])
                    elif res["type"] is "share":
                        client.delete_share(
                            res_id, microversion=res["microversion"])
                        client.wait_for_share_deletion(
                            res_id, microversion=res["microversion"])
                    elif res["type"] is "snapshot":
                        client.delete_snapshot(
                            res_id, microversion=res["microversion"])
                        client.wait_for_snapshot_deletion(
                            res_id, microversion=res["microversion"])
                    elif res["type"] is "share_replica":
                        client.delete_share_replica(
                            res_id, microversion=res["microversion"])
                        client.wait_for_share_replica_deletion(
                            res_id, microversion=res["microversion"])
                    else:
                        LOG.warning("Provided unsupported resource type for "
                                    "cleanup '%s'. Skipping.", res["type"])
                res["deleted"] = True

    @classmethod
    def get_admin_client(cls):
        manilaclient = client.ManilaCLIClient(
            username=CONF.admin_username,
            password=CONF.admin_password,
            tenant_name=CONF.admin_tenant_name,
            project_domain_name=CONF.admin_project_domain_name or None,
            project_domain_id=CONF.admin_project_domain_id or None,
            user_domain_name=CONF.admin_user_domain_name or None,
            user_domain_id=CONF.admin_user_domain_id or None,
            uri=CONF.admin_auth_url or CONF.auth_url,
            insecure=CONF.insecure,
            cli_dir=CONF.manila_exec_dir)
        # Set specific for admin project share network
        manilaclient.share_network = CONF.admin_share_network
        return manilaclient

    @classmethod
    def get_user_client(cls):
        manilaclient = client.ManilaCLIClient(
            username=CONF.username,
            password=CONF.password,
            tenant_name=CONF.tenant_name,
            project_domain_name=CONF.project_domain_name or None,
            project_domain_id=CONF.project_domain_id or None,
            user_domain_name=CONF.user_domain_name or None,
            user_domain_id=CONF.user_domain_id or None,
            uri=CONF.auth_url,
            insecure=CONF.insecure,
            cli_dir=CONF.manila_exec_dir)
        # Set specific for user project share network
        manilaclient.share_network = CONF.share_network
        return manilaclient

    @property
    def admin_client(self):
        if not hasattr(self, '_admin_client'):
            self._admin_client = self.get_admin_client()
        return self._admin_client

    @property
    def user_client(self):
        if not hasattr(self, '_user_client'):
            self._user_client = self.get_user_client()
        return self._user_client

    def _get_clients(self):
        return {'admin': self.admin_client, 'user': self.user_client}

    def skip_if_microversion_not_supported(self, microversion):
        if not utils.is_microversion_supported(microversion):
            raise self.skipException(
                "Microversion '%s' is not supported." % microversion)

    @classmethod
    def create_share_type(cls, name=None, driver_handles_share_servers=True,
                          snapshot_support=None,
                          create_share_from_snapshot=None,
                          revert_to_snapshot=None, mount_snapshot=None,
                          is_public=True, client=None, cleanup_in_class=True,
                          microversion=None, extra_specs=None,
                          description=None):
        if client is None:
            client = cls.get_admin_client()
        data = {
            "name": name,
            "driver_handles_share_servers": driver_handles_share_servers,
            "snapshot_support": snapshot_support,
            "is_public": is_public,
            "microversion": microversion,
            "extra_specs": extra_specs,
            "create_share_from_snapshot": create_share_from_snapshot,
            "revert_to_snapshot": revert_to_snapshot,
            "mount_snapshot": mount_snapshot,
        }
        if description:
            data["description"] = description
        share_type = client.create_share_type(**data)
        resource = {
            "type": "share_type",
            "id": share_type["ID"],
            "client": client,
            "microversion": microversion,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return share_type

    @classmethod
    def create_share_network(cls, name=None, description=None,
                             neutron_net_id=None,
                             neutron_subnet_id=None, client=None,
                             cleanup_in_class=True, microversion=None):
        if client is None:
            client = cls.get_admin_client()
        share_network = client.create_share_network(
            name=name,
            description=description,
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id,
            microversion=microversion,
        )
        resource = {
            "type": "share_network",
            "id": share_network["id"],
            "client": client,
            "microversion": microversion,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return share_network

    @classmethod
    def create_share(cls, share_protocol=None, size=None, share_network=None,
                     share_type=None, name=None, description=None,
                     public=False, snapshot=None, metadata=None,
                     client=None, cleanup_in_class=False,
                     wait_for_creation=True, microversion=None):
        client = client or cls.get_admin_client()
        data = {
            'share_protocol': share_protocol or client.share_protocol,
            'size': size or 1,
            'name': name,
            'description': description,
            'public': public,
            'snapshot': snapshot,
            'metadata': metadata,
            'microversion': microversion,
        }

        share_type = share_type or CONF.share_type
        share_network = share_network or cls._determine_share_network_to_use(
            client, share_type, microversion=microversion)

        data['share_type'] = share_type
        data['share_network'] = share_network
        share = client.create_share(**data)
        resource = {
            "type": "share",
            "id": share["id"],
            "client": client,
            "microversion": microversion,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        if wait_for_creation:
            client.wait_for_resource_status(share['id'],
                                            constants.STATUS_AVAILABLE)
        return share

    @classmethod
    def _determine_share_network_to_use(cls, client, share_type,
                                        microversion=None):
        """Determine what share network we need from the share type."""

        # Get share type, determine if we need the share network
        share_type = client.get_share_type(share_type,
                                           microversion=microversion)
        dhss_pattern = re.compile('driver_handles_share_servers : ([a-zA-Z]+)')
        dhss = dhss_pattern.search(share_type['required_extra_specs']).group(1)
        return client.share_network if dhss.lower() == 'true' else None

    @classmethod
    def create_security_service(cls, type='ldap', name=None, description=None,
                                dns_ip=None, ou=None, server=None, domain=None,
                                user=None, password=None, client=None,
                                cleanup_in_class=False, microversion=None):
        if client is None:
            client = cls.get_admin_client()
        data = {
            'type': type,
            'name': name,
            'description': description,
            'user': user,
            'password': password,
            'server': server,
            'domain': domain,
            'dns_ip': dns_ip,
            'ou': ou,
            'microversion': microversion,
        }
        ss = client.create_security_service(**data)
        resource = {
            "type": "share",
            "id": ss["id"],
            "client": client,
            "microversion": microversion,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return ss

    @classmethod
    def create_snapshot(cls, share, name=None, description=None,
                        force=False, client=None, wait_for_creation=True,
                        cleanup_in_class=False, microversion=None):
        if client is None:
            client = cls.get_admin_client()
        data = {
            'share': share,
            'name': name,
            'description': description,
            'force': force,
            'microversion': microversion,
        }
        snapshot = client.create_snapshot(**data)
        resource = {
            "type": "snapshot",
            "id": snapshot["id"],
            "client": client,
            "microversion": microversion,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        if wait_for_creation:
            client.wait_for_snapshot_status(snapshot['id'], 'available')
        return snapshot

    @classmethod
    def create_message(cls, client=None, wait_for_creation=True,
                       cleanup_in_class=False, microversion=None):
        """Trigger a 'no valid host' situation to generate a message."""
        if client is None:
            client = cls.get_admin_client()

        extra_specs = {
            'vendor_name': 'foobar',
        }
        share_type_name = data_utils.rand_name("share-type")
        cls.create_share_type(
            name=share_type_name, extra_specs=extra_specs,
            driver_handles_share_servers=False, client=client,
            cleanup_in_class=cleanup_in_class, microversion=microversion)

        share_name = data_utils.rand_name("share")
        share = cls.create_share(
            name=share_name, share_type=share_type_name,
            cleanup_in_class=cleanup_in_class, microversion=microversion,
            wait_for_creation=False, client=client)

        client.wait_for_resource_status(share['id'], constants.STATUS_ERROR)
        message = client.wait_for_message(share['id'])

        resource = {
            "type": "message",
            "id": message["ID"],
            "client": client,
            "microversion": microversion,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return message

    @classmethod
    def create_share_replica(cls, share_id, client=None,
                             wait_for_creation=True, cleanup_in_class=False,
                             microversion=None):
        client = client or cls.get_user_client()

        share_replica = client.create_share_replica(
            share_id, microversion=microversion)
        if wait_for_creation:
            share_replica = client.wait_for_share_replica_status(
                share_replica['id'])

        resource = {
            "type": "share_replica",
            "id": share_replica["id"],
            "client": client,
            "microversion": microversion,
        }
        if cleanup_in_class:
            cls.class_resources.insert(0, resource)
        else:
            cls.method_resources.insert(0, resource)
        return share_replica
