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
import time

from oslo_utils import strutils
import six
from tempest.lib.cli import base
from tempest.lib.cli import output_parser
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as tempest_lib_exc

from manilaclient.common import constants
from manilaclient import config
from manilaclient.tests.functional import exceptions
from manilaclient.tests.functional import utils

CONF = config.CONF
MESSAGE = 'message'
SHARE = 'share'
SHARE_TYPE = 'share_type'
SHARE_NETWORK = 'share_network'
SHARE_SERVER = 'share_server'
SNAPSHOT = 'snapshot'
SHARE_REPLICA = 'share_replica'


def not_found_wrapper(f):

    def wrapped_func(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except tempest_lib_exc.CommandFailed as e:
            for regexp in ('No (\w+) with a name or ID', 'not(.*){0,5}found'):
                if re.search(regexp, six.text_type(e.stderr)):
                    # Raise appropriate 'NotFound' error
                    raise tempest_lib_exc.NotFound()
            raise

    return wrapped_func


def forbidden_wrapper(f):

    def wrapped_func(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except tempest_lib_exc.CommandFailed as e:
            if re.search('HTTP 403', six.text_type(e.stderr)):
                # Raise appropriate 'Forbidden' error.
                raise tempest_lib_exc.Forbidden()
            raise

    return wrapped_func


class ManilaCLIClient(base.CLIClient):

    def __init__(self, *args, **kwargs):
        super(ManilaCLIClient, self).__init__(*args, **kwargs)
        if CONF.enable_protocols:
            self.share_protocol = CONF.enable_protocols[0]
        else:
            msg = "Configuration option 'enable_protocols' is not defined."
            raise exceptions.InvalidConfiguration(reason=msg)
        self.build_interval = CONF.build_interval
        self.build_timeout = CONF.build_timeout

    def manila(self, action, flags='', params='', fail_ok=False,
               endpoint_type='publicURL', merge_stderr=False,
               microversion=None):
        """Executes manila command for the given action.

        :param action: the cli command to run using manila
        :type action: string
        :param flags: any optional cli flags to use. For specifying
                      microversion, please, use 'microversion' param
        :type flags: string
        :param params: any optional positional args to use
        :type params: string
        :param fail_ok: if True an exception is not raised when the
                        cli return code is non-zero
        :type fail_ok: boolean
        :param endpoint_type: the type of endpoint for the service
        :type endpoint_type: string
        :param merge_stderr: if True the stderr buffer is merged into stdout
        :type merge_stderr: boolean
        :param microversion: API microversion to be used for request
        :type microversion: str
        """
        flags += ' --endpoint-type %s' % endpoint_type
        if not microversion:
            # NOTE(vponomaryov): use max API version from config
            microversion = CONF.max_api_microversion

        # NOTE(vponomaryov): it is possible that param 'flags' already
        # can contain '--os-share-api-version' key. If it is so and we
        # reached this part then value of 'microversion' param will be
        # used and existing one in 'flags' param will be ignored.
        flags += ' --os-share-api-version %s' % microversion
        return self.cmd_with_auth(
            'manila', action, flags, params, fail_ok, merge_stderr)

    def wait_for_resource_deletion(self, res_type, res_id, interval=3,
                                   timeout=180, microversion=None):
        """Resource deletion waiter.

        :param res_type: text -- type of resource. Supported only 'share_type'.
            Other types support is TODO.
        :param res_id: text -- ID of resource to use for deletion check
        :param interval: int -- interval between requests in seconds
        :param timeout: int -- total time in seconds to wait for deletion
        """
        # TODO(vponomaryov): add support for other resource types
        if res_type == SHARE_TYPE:
            func = self.is_share_type_deleted
        elif res_type == SHARE_NETWORK:
            func = self.is_share_network_deleted
        elif res_type == SHARE_SERVER:
            func = self.is_share_server_deleted
        elif res_type == SHARE:
            func = self.is_share_deleted
        elif res_type == SNAPSHOT:
            func = self.is_snapshot_deleted
        elif res_type == MESSAGE:
            func = self.is_message_deleted
        elif res_type == SHARE_REPLICA:
            func = self.is_share_replica_deleted
        else:
            raise exceptions.InvalidResource(message=res_type)

        end_loop_time = time.time() + timeout
        deleted = func(res_id, microversion=microversion)

        while not (deleted or time.time() > end_loop_time):
            time.sleep(interval)
            deleted = func(res_id, microversion=microversion)

        if not deleted:
            raise exceptions.ResourceReleaseFailed(
                res_type=res_type, res_id=res_id)

    def list_availability_zones(self, columns=None, microversion=None):
        """List availability zones.

        :param columns: comma separated string of columns.
            Example, "--columns id,name"
        :param microversion: API microversion that should be used.
        """
        cmd = 'availability-zone-list'
        if columns is not None:
            cmd += ' --columns ' + columns
        azs_raw = self.manila(cmd, microversion=microversion)
        azs = output_parser.listing(azs_raw)
        return azs

    # Share types

    def create_share_type(self, name=None, driver_handles_share_servers=True,
                          snapshot_support=None,
                          create_share_from_snapshot=None,
                          revert_to_snapshot=None, mount_snapshot=None,
                          is_public=True, microversion=None, extra_specs=None,
                          description=None):
        """Creates share type.

        :param name: text -- name of share type to use, if not set then
            autogenerated will be used
        :param description: text -- description of share type to use.
            Default is None.
        :param driver_handles_share_servers: bool/str -- boolean or its
            string alias. Default is True.
        :param snapshot_support: bool/str -- boolean or its
            string alias. Default is None.
        :param is_public: bool/str -- boolean or its string alias. Default is
            True.
        :param extra_specs: -- dictionary of extra specs Default is None.
        :param create_share_from_snapshot: -- boolean or its string
            alias. Default is None.
        :param revert_to_snapshot: -- boolean or its string alias. Default is
            None.
        :param mount_snapshot: -- boolean or its string alias. Default is None.
        """
        if name is None:
            name = data_utils.rand_name('manilaclient_functional_test')
        dhss = driver_handles_share_servers
        if not isinstance(dhss, six.string_types):
            dhss = six.text_type(dhss)
        if not isinstance(is_public, six.string_types):
            is_public = six.text_type(is_public)

        cmd = ('type-create %(name)s %(dhss)s --is-public %(is_public)s ') % {
            'name': name, 'dhss': dhss, 'is_public': is_public}

        if description is not None:
            cmd += " --description " + description

        if snapshot_support is not None:
            if not isinstance(snapshot_support, six.string_types):
                snapshot_support = six.text_type(snapshot_support)
            cmd += " --snapshot-support " + snapshot_support

        if create_share_from_snapshot is not None:
            if not isinstance(create_share_from_snapshot, six.string_types):
                create_share_from_snapshot = six.text_type(
                    create_share_from_snapshot)
            cmd += (" --create-share-from-snapshot-support " +
                    create_share_from_snapshot)

        if revert_to_snapshot is not None:
            if not isinstance(revert_to_snapshot, six.string_types):
                revert_to_snapshot = six.text_type(
                    revert_to_snapshot)
            cmd += (" --revert-to-snapshot-support " + revert_to_snapshot)

        if mount_snapshot is not None:
            if not isinstance(mount_snapshot, six.string_types):
                mount_snapshot = six.text_type(
                    mount_snapshot)
            cmd += (" --mount-snapshot-support " + mount_snapshot)

        if extra_specs is not None:
            extra_spec_str = ''
            for k, v in extra_specs.items():
                if not isinstance(v, six.string_types):
                    extra_specs[k] = six.text_type(v)
                extra_spec_str += "{}='{}' ".format(k, v)
            cmd += " --extra_specs " + extra_spec_str

        share_type_raw = self.manila(cmd, microversion=microversion)
        share_type = utils.details(share_type_raw)
        return share_type

    @not_found_wrapper
    def delete_share_type(self, share_type, microversion=None):
        """Deletes share type by its Name or ID."""
        return self.manila(
            'type-delete %s' % share_type, microversion=microversion)

    def list_share_types(self, list_all=True, columns=None, search_opts=None,
                         microversion=None):
        """List share types.

        :param list_all: bool -- whether to list all share types or only public
        :param search_opts: dict search_opts for filter search.
        :param columns: comma separated string of columns.
            Example, "--columns id,name"
        """
        cmd = 'type-list'
        if list_all:
            cmd += ' --all'
        if search_opts is not None:
            extra_specs = search_opts.get('extra_specs')
            if extra_specs:
                cmd += ' --extra_specs'
                for spec_key in extra_specs.keys():
                    cmd += ' ' + spec_key + '=' + extra_specs[spec_key]
        if columns is not None:
            cmd += ' --columns ' + columns
        share_types_raw = self.manila(cmd, microversion=microversion)
        share_types = output_parser.listing(share_types_raw)
        return share_types

    def get_share_type(self, share_type, microversion=None):
        """Get share type.

        :param share_type: str -- Name or ID of share type, or None to
                    retrieve default share type
        """
        share_types = self.list_share_types(True, microversion=microversion)
        for stype in share_types:
            if share_type is None and stype["is_default"] == 'YES':
                return stype
            elif share_type in (stype['ID'], stype['Name']):
                return stype
        raise tempest_lib_exc.NotFound()

    def is_share_type_deleted(self, share_type, microversion=None):
        """Says whether share type is deleted or not.

        :param share_type: text -- Name or ID of share type
        """
        # NOTE(vponomaryov): we use 'list' operation because there is no
        # 'get/show' operation for share-types available for CLI
        share_types = self.list_share_types(
            list_all=True, microversion=microversion)
        for list_element in share_types:
            if share_type in (list_element['ID'], list_element['Name']):
                return False
        return True

    def wait_for_share_type_deletion(self, share_type, microversion=None):
        """Wait for share type deletion by its Name or ID.

        :param share_type: text -- Name or ID of share type
        """
        self.wait_for_resource_deletion(
            SHARE_TYPE, res_id=share_type, interval=2, timeout=6,
            microversion=microversion)

    def get_project_id(self, name_or_id):
        identity_api_version = '3'
        flags = (
            "--os-username %(username)s "
            "--os-project-name %(project_name)s "
            "--os-password %(password)s "
            "--os-identity-api-version %(identity_api_version)s "
        ) % {
            "username": CONF.admin_username,
            "project_name": CONF.admin_tenant_name,
            "password": CONF.admin_password,
            "identity_api_version": identity_api_version,
        }

        if identity_api_version == "3":
            if CONF.admin_project_domain_name:
                flags += (
                    "--os-project-domain-name %s " %
                    CONF.admin_project_domain_name)
            elif CONF.admin_project_domain_id:
                flags += (
                    "--os-project-domain-id %s " %
                    CONF.admin_project_domain_id)

            if CONF.admin_user_domain_name:
                flags += (
                    "--os-user-domain-name %s " %
                    CONF.admin_user_domain_name)
            elif CONF.admin_user_domain_id:
                flags += (
                    "--os-user-domain-id %s " %
                    CONF.admin_user_domain_id)

        project_id = self.openstack(
            'project show -f value -c id %s' % name_or_id, flags=flags)
        return project_id.strip()

    @not_found_wrapper
    def add_share_type_access(self, share_type_name_or_id, project_id,
                              microversion=None):
        data = dict(st=share_type_name_or_id, project=project_id)
        self.manila('type-access-add %(st)s %(project)s' % data,
                    microversion=microversion)

    @not_found_wrapper
    def remove_share_type_access(self, share_type_name_or_id, project_id,
                                 microversion=None):
        data = dict(st=share_type_name_or_id, project=project_id)
        self.manila('type-access-remove %(st)s %(project)s' % data,
                    microversion=microversion)

    @not_found_wrapper
    def list_share_type_access(self, share_type_id, microversion=None):
        projects_raw = self.manila(
            'type-access-list %s' % share_type_id, microversion=microversion)
        projects = output_parser.listing(projects_raw)
        project_ids = [pr['Project_ID'] for pr in projects]
        return project_ids

    @not_found_wrapper
    def set_share_type_extra_specs(self, share_type_name_or_id, extra_specs,
                                   microversion=None):
        """Set key-value pair for share type."""
        if not (isinstance(extra_specs, dict) and extra_specs):
            raise exceptions.InvalidData(
                message='Provided invalid extra specs - %s' % extra_specs)
        cmd = 'type-key %s set ' % share_type_name_or_id
        for key, value in extra_specs.items():
            cmd += '%(key)s=%(value)s ' % {'key': key, 'value': value}
        return self.manila(cmd, microversion=microversion)

    @not_found_wrapper
    def unset_share_type_extra_specs(self, share_type_name_or_id,
                                     extra_specs_keys, microversion=None):
        """Unset key-value pair for share type."""
        if not (isinstance(extra_specs_keys, (list, tuple, set)) and
                extra_specs_keys):
            raise exceptions.InvalidData(
                message='Provided invalid extra specs - %s' % extra_specs_keys)
        cmd = 'type-key %s unset ' % share_type_name_or_id
        for key in extra_specs_keys:
            cmd += '%s ' % key
        return self.manila(cmd, microversion=microversion)

    def list_all_share_type_extra_specs(self, microversion=None):
        """List extra specs for all share types."""
        extra_specs_raw = self.manila(
            'extra-specs-list', microversion=microversion)
        extra_specs = utils.listing(extra_specs_raw)
        return extra_specs

    def list_share_type_extra_specs(self, share_type_name_or_id,
                                    microversion=None):
        """List extra specs for specific share type by its Name or ID."""
        all_share_types = self.list_all_share_type_extra_specs(
            microversion=microversion)
        for share_type in all_share_types:
            if share_type_name_or_id in (share_type['ID'], share_type['Name']):
                return share_type['all_extra_specs']
        raise exceptions.ShareTypeNotFound(share_type=share_type_name_or_id)

    # Share networks

    def create_share_network(self, name=None, description=None,
                             nova_net_id=None, neutron_net_id=None,
                             neutron_subnet_id=None, microversion=None):
        """Creates share network.

        :param name: text -- desired name of new share network
        :param description: text -- desired description of new share network
        :param nova_net_id: text -- ID of Nova network
        :param neutron_net_id: text -- ID of Neutron network
        :param neutron_subnet_id: text -- ID of Neutron subnet

        NOTE: 'nova_net_id' and 'neutron_net_id'/'neutron_subnet_id' are
            mutually exclusive.
        """
        params = self._combine_share_network_data(
            name=name,
            description=description,
            nova_net_id=nova_net_id,
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id)
        share_network_raw = self.manila(
            'share-network-create %s' % params, microversion=microversion)
        share_network = output_parser.details(share_network_raw)
        return share_network

    def _combine_share_network_data(self, name=None, description=None,
                                    nova_net_id=None, neutron_net_id=None,
                                    neutron_subnet_id=None):
        """Combines params for share network operations 'create' and 'update'.

        :returns: text -- set of CLI parameters
        """
        data = dict()
        if name is not None:
            data['--name'] = name
        if description is not None:
            data['--description'] = description
        if nova_net_id is not None:
            data['--nova_net_id'] = nova_net_id
        if neutron_net_id is not None:
            data['--neutron_net_id'] = neutron_net_id
        if neutron_subnet_id is not None:
            data['--neutron_subnet_id'] = neutron_subnet_id
        cmd = ''
        for key, value in data.items():
            cmd += "%(k)s=%(v)s " % dict(k=key, v=value)
        return cmd

    @not_found_wrapper
    def get_share_network(self, share_network, microversion=None):
        """Returns share network by its Name or ID."""
        share_network_raw = self.manila(
            'share-network-show %s' % share_network, microversion=microversion)
        share_network = output_parser.details(share_network_raw)
        return share_network

    @not_found_wrapper
    def update_share_network(self, share_network, name=None, description=None,
                             nova_net_id=None, neutron_net_id=None,
                             neutron_subnet_id=None, microversion=None):
        """Updates share-network by its name or ID.

        :param name: text -- new name for share network
        :param description: text -- new description for share network
        :param nova_net_id: text -- ID of some Nova network
        :param neutron_net_id: text -- ID of some Neutron network
        :param neutron_subnet_id: text -- ID of some Neutron subnet

        NOTE: 'nova_net_id' and 'neutron_net_id'/'neutron_subnet_id' are
            mutually exclusive.
        """
        sn_params = self._combine_share_network_data(
            name=name,
            description=description,
            nova_net_id=nova_net_id,
            neutron_net_id=neutron_net_id,
            neutron_subnet_id=neutron_subnet_id)
        share_network_raw = self.manila(
            'share-network-update %(sn)s %(params)s' % dict(
                sn=share_network, params=sn_params),
            microversion=microversion)
        share_network = output_parser.details(share_network_raw)
        return share_network

    @not_found_wrapper
    def delete_share_network(self, share_network, microversion=None):
        """Deletes share network by its Name or ID."""
        return self.manila('share-network-delete %s' % share_network,
                           microversion=microversion)

    @staticmethod
    def _stranslate_to_cli_optional_param(param):
        if len(param) < 1 or not isinstance(param, six.string_types):
            raise exceptions.InvalidData(
                'Provided wrong parameter for translation.')
        while not param[0:2] == '--':
            param = '-' + param
        return param.replace('_', '-')

    def list_share_networks(self, all_tenants=False, filters=None,
                            columns=None, microversion=None):
        """List share networks.

        :param all_tenants: bool -- whether to list share-networks that belong
            only to current project or for all projects.
        :param filters: dict -- filters for listing of share networks.
            Example, input:
                {'project_id': 'foo'}
                {'-project_id': 'foo'}
                {'--project_id': 'foo'}
                {'project-id': 'foo'}
            will be transformed to filter parameter "--project-id=foo"
         :param columns: comma separated string of columns.
            Example, "--columns id"
        """
        cmd = 'share-network-list '
        if columns is not None:
            cmd += ' --columns ' + columns
        if all_tenants:
            cmd += ' --all-tenants '
        if filters and isinstance(filters, dict):
            for k, v in filters.items():
                cmd += '%(k)s=%(v)s ' % {
                    'k': self._stranslate_to_cli_optional_param(k), 'v': v}
        share_networks_raw = self.manila(cmd, microversion=microversion)
        share_networks = utils.listing(share_networks_raw)
        return share_networks

    def is_share_network_deleted(self, share_network, microversion=None):
        """Says whether share network is deleted or not.

        :param share_network: text -- Name or ID of share network
        """
        share_types = self.list_share_networks(True, microversion=microversion)
        for list_element in share_types:
            if share_network in (list_element['id'], list_element['name']):
                return False
        return True

    def wait_for_share_network_deletion(self, share_network,
                                        microversion=None):
        """Wait for share network deletion by its Name or ID.

        :param share_network: text -- Name or ID of share network
        """
        self.wait_for_resource_deletion(
            SHARE_NETWORK, res_id=share_network, interval=2, timeout=6,
            microversion=microversion)

    # Shares

    def create_share(self, share_protocol, size, share_network=None,
                     share_type=None, name=None, description=None,
                     public=False, snapshot=None, metadata=None,
                     microversion=None):
        """Creates a share.

        :param share_protocol: str -- share protocol of a share.
        :param size: int/str -- desired size of a share.
        :param share_network: str -- Name or ID of share network to use.
        :param share_type: str -- Name or ID of share type to use.
        :param name: str -- desired name of new share.
        :param description: str -- desired description of new share.
        :param public: bool -- should a share be public or not.
            Default is False.
        :param snapshot: str -- Name or ID of a snapshot to use as source.
        :param metadata: dict -- key-value data to provide with share creation.
        :param microversion: str -- API microversion that should be used.
        """
        cmd = 'create %(share_protocol)s %(size)s ' % {
            'share_protocol': share_protocol, 'size': size}
        if share_network is not None:
            cmd += '--share-network %s ' % share_network
        if share_type is not None:
            cmd += '--share-type %s ' % share_type
        if name is None:
            name = data_utils.rand_name('autotest_share_name')
        cmd += '--name %s ' % name
        if description is None:
            description = data_utils.rand_name('autotest_share_description')
        cmd += '--description %s ' % description
        if public:
            cmd += '--public'
        if snapshot is not None:
            cmd += '--snapshot %s ' % snapshot
        if metadata:
            metadata_cli = ''
            for k, v in metadata.items():
                metadata_cli += '%(k)s=%(v)s ' % {'k': k, 'v': v}
            if metadata_cli:
                cmd += '--metadata %s ' % metadata_cli
        share_raw = self.manila(cmd, microversion=microversion)
        share = output_parser.details(share_raw)
        return share

    @not_found_wrapper
    def get_share(self, share, microversion=None):
        """Returns a share by its Name or ID."""
        share_raw = self.manila('show %s' % share, microversion=microversion)
        share = output_parser.details(share_raw)
        return share

    @not_found_wrapper
    def update_share(self, share, name=None, description=None,
                     is_public=False, microversion=None):
        """Updates a share.

        :param share: str -- name or ID of a share that should be updated.
        :param name: str -- desired name of new share.
        :param description: str -- desired description of new share.
        :param is_public: bool -- should a share be public or not.
            Default is False.
        """
        cmd = 'update %s ' % share
        if name:
            cmd += '--name %s ' % name
        if description:
            cmd += '--description %s ' % description
        is_public = strutils.bool_from_string(is_public, strict=True)
        cmd += '--is-public %s ' % is_public

        return self.manila(cmd, microversion=microversion)

    @not_found_wrapper
    @forbidden_wrapper
    def delete_share(self, shares, microversion=None):
        """Deletes share[s] by Names or IDs.

        :param shares: either str or list of str that can be either Name
            or ID of a share(s) that should be deleted.
        """
        if not isinstance(shares, list):
            shares = [shares]
        cmd = 'delete '
        for share in shares:
            cmd += '%s ' % share
        return self.manila(cmd, microversion=microversion)

    def list_shares(self, all_tenants=False, filters=None, columns=None,
                    is_public=False, microversion=None):
        """List shares.

        :param all_tenants: bool -- whether to list shares that belong
            only to current project or for all projects.
        :param filters: dict -- filters for listing of shares.
            Example, input:
                {'project_id': 'foo'}
                {-'project_id': 'foo'}
                {--'project_id': 'foo'}
                {'project-id': 'foo'}
            will be transformed to filter parameter "--project-id=foo"
        :param columns: comma separated string of columns.
            Example, "--columns Name,Size"
        :param is_public: bool -- should list public shares or not.
            Default is False.
        """
        cmd = 'list '
        if all_tenants:
            cmd += '--all-tenants '
        if is_public:
            cmd += '--public '
        if filters and isinstance(filters, dict):
            for k, v in filters.items():
                cmd += '%(k)s=%(v)s ' % {
                    'k': self._stranslate_to_cli_optional_param(k), 'v': v}
        if columns is not None:
            cmd += '--columns ' + columns
        shares_raw = self.manila(cmd, microversion=microversion)
        shares = utils.listing(shares_raw)
        return shares

    def list_share_instances(self, share_id=None, filters=None,
                             microversion=None):
        """List share instances.

        :param share_id: ID of a share to filter by.
        :param filters: dict -- filters for listing of shares.
            Example, input:
                {'project_id': 'foo'}
                {-'project_id': 'foo'}
                {--'project_id': 'foo'}
                {'project-id': 'foo'}
            will be transformed to filter parameter "--export-location=foo"
        :param microversion: API microversion to be used for request.
        """
        cmd = 'share-instance-list '
        if share_id:
            cmd += '--share-id %s' % share_id
        if filters and isinstance(filters, dict):
            for k, v in filters.items():
                cmd += '%(k)s=%(v)s ' % {
                    'k': self._stranslate_to_cli_optional_param(k), 'v': v}
        share_instances_raw = self.manila(cmd, microversion=microversion)
        share_instances = utils.listing(share_instances_raw)
        return share_instances

    def is_share_deleted(self, share, microversion=None):
        """Says whether share is deleted or not.

        :param share: str -- Name or ID of share
        """
        try:
            self.get_share(share, microversion=microversion)
            return False
        except tempest_lib_exc.NotFound:
            return True

    def wait_for_share_deletion(self, share, microversion=None):
        """Wait for share deletion by its Name or ID.

        :param share: str -- Name or ID of share
        """
        self.wait_for_resource_deletion(
            SHARE, res_id=share, interval=5, timeout=300,
            microversion=microversion)

    def wait_for_resource_status(self, resource_id, status, microversion=None,
                                 resource_type="share"):
        """Waits for a share to reach a given status."""
        get_func = getattr(self, 'get_' + resource_type)
        body = get_func(resource_id, microversion=microversion)
        share_status = body['status']
        start = int(time.time())

        while share_status != status:
            time.sleep(self.build_interval)
            body = get_func(resource_id, microversion=microversion)
            share_status = body['status']

            if share_status == status:
                return
            elif 'error' in share_status.lower():
                raise exceptions.ShareBuildErrorException(share=resource_id)

            if int(time.time()) - start >= self.build_timeout:
                message = ("Resource %(resource_id)s failed to reach "
                           "%(status)s  status within the required time "
                           "(%(build_timeout)s)." %
                           {"resource_id": resource_id, "status": status,
                            "build_timeout": self.build_timeout})
                raise tempest_lib_exc.TimeoutException(message)

    def wait_for_migration_task_state(self, share_id, dest_host,
                                      task_state_to_wait, microversion=None):
        """Waits for a share to migrate to a certain host."""
        statuses = ((task_state_to_wait,)
                    if not isinstance(task_state_to_wait, (tuple, list, set))
                    else task_state_to_wait)
        share = self.get_share(share_id, microversion=microversion)
        start = int(time.time())
        while share['task_state'] not in statuses:
            time.sleep(self.build_interval)
            share = self.get_share(share_id, microversion=microversion)
            if share['task_state'] in statuses:
                break
            elif share['task_state'] == constants.TASK_STATE_MIGRATION_ERROR:
                raise exceptions.ShareMigrationException(
                    share_id=share['id'], src=share['host'], dest=dest_host)
            elif int(time.time()) - start >= self.build_timeout:
                message = ('Share %(share_id)s failed to reach a status in'
                           '%(status)s when migrating from host %(src)s to '
                           'host %(dest)s within the required time '
                           '%(timeout)s.' % {
                               'src': share['host'],
                               'dest': dest_host,
                               'share_id': share['id'],
                               'timeout': self.build_timeout,
                               'status': six.text_type(statuses),
                           })
                raise tempest_lib_exc.TimeoutException(message)
        return share

    @not_found_wrapper
    def _set_share_metadata(self, share, data, update_all=False,
                            microversion=None):
        """Sets a share metadata.

        :param share: str -- Name or ID of a share.
        :param data: dict -- key-value pairs to set as metadata.
        :param update_all: bool -- if set True then all keys except provided
            will be deleted.
        """
        if not (isinstance(data, dict) and data):
            msg = ('Provided invalid data for setting of share metadata - '
                   '%s' % data)
            raise exceptions.InvalidData(message=msg)
        if update_all:
            cmd = 'metadata-update-all %s ' % share
        else:
            cmd = 'metadata %s set ' % share
        for k, v in data.items():
            cmd += '%(k)s=%(v)s ' % {'k': k, 'v': v}
        return self.manila(cmd, microversion=microversion)

    def update_all_share_metadata(self, share, data, microversion=None):
        metadata_raw = self._set_share_metadata(
            share, data, True, microversion=microversion)
        metadata = output_parser.details(metadata_raw)
        return metadata

    def set_share_metadata(self, share, data, microversion=None):
        return self._set_share_metadata(
            share, data, False, microversion=microversion)

    @not_found_wrapper
    def unset_share_metadata(self, share, keys, microversion=None):
        """Unsets some share metadata by keys.

        :param share: str -- Name or ID of a share
        :param keys: str/list -- key or list of keys to unset.
        """
        if not (isinstance(keys, list) and keys):
            msg = ('Provided invalid data for unsetting of share metadata - '
                   '%s' % keys)
            raise exceptions.InvalidData(message=msg)
        cmd = 'metadata %s unset ' % share
        for key in keys:
            cmd += '%s ' % key
        return self.manila(cmd, microversion=microversion)

    @not_found_wrapper
    def get_share_metadata(self, share, microversion=None):
        """Returns list of all share metadata.

        :param share: str -- Name or ID of a share.
        """
        metadata_raw = self.manila(
            'metadata-show %s' % share, microversion=microversion)
        metadata = output_parser.details(metadata_raw)
        return metadata

    def create_snapshot(self, share, name=None, description=None,
                        force=False, microversion=None):
        """Creates a snapshot."""
        cmd = 'snapshot-create %(share)s ' % {'share': share}
        if name is None:
            name = data_utils.rand_name('autotest_snapshot_name')
        cmd += '--name %s ' % name
        if description is None:
            description = data_utils.rand_name('autotest_snapshot_description')
        cmd += '--description %s ' % description
        if force:
            cmd += '--force %s' % force
        snapshot_raw = self.manila(cmd, microversion=microversion)
        snapshot = output_parser.details(snapshot_raw)
        return snapshot

    @not_found_wrapper
    def get_snapshot(self, snapshot, microversion=None):
        """Retrieves a snapshot by its Name or ID."""
        snapshot_raw = self.manila('snapshot-show %s' % snapshot,
                                   microversion=microversion)
        snapshot = output_parser.details(snapshot_raw)
        return snapshot

    @not_found_wrapper
    def list_snapshot_export_locations(self, snapshot, columns=None,
                                       microversion=None):
        """List snapshot export locations.

        :param snapshot: str -- Name or ID of a snapshot.
        :param columns: str -- comma separated string of columns.
            Example, "--columns uuid,path".
        :param microversion: API microversion to be used for request.
        """
        cmd = "snapshot-export-location-list %s" % snapshot
        if columns is not None:
            cmd += " --columns " + columns
        export_locations_raw = self.manila(cmd, microversion=microversion)
        export_locations = utils.listing(export_locations_raw)
        return export_locations

    @not_found_wrapper
    @forbidden_wrapper
    def list_snapshot_instance_export_locations(self, snapshot_instance,
                                                columns=None,
                                                microversion=None):
        """List snapshot instance export locations.

        :param snapshot_instance: str -- Name or ID of a snapshot instance.
        :param columns: str -- comma separated string of columns.
            Example, "--columns uuid,path".
        :param microversion: API microversion to be used for request.
        """
        cmd = "snapshot-instance-export-location-list %s" % snapshot_instance
        if columns is not None:
            cmd += " --columns " + columns
        export_locations_raw = self.manila(cmd, microversion=microversion)
        export_locations = utils.listing(export_locations_raw)
        return export_locations

    @not_found_wrapper
    @forbidden_wrapper
    def delete_snapshot(self, snapshot, microversion=None):
        """Deletes snapshot by Names or IDs."""
        return self.manila(
            "snapshot-delete %s" % snapshot, microversion=microversion)

    def list_snapshot_instances(self, snapshot_id=None, columns=None,
                                detailed=None, microversion=None):
        """List snapshot instances."""
        cmd = 'snapshot-instance-list '
        if snapshot_id:
            cmd += '--snapshot %s' % snapshot_id
        if columns is not None:
            cmd += ' --columns ' + columns
        if detailed:
            cmd += ' --detailed True '
        snapshot_instances_raw = self.manila(cmd, microversion=microversion)
        snapshot_instances = utils.listing(snapshot_instances_raw)
        return snapshot_instances

    def get_snapshot_instance(self, id=None, microversion=None):
        """Get snapshot instance."""
        cmd = 'snapshot-instance-show %s ' % id
        snapshot_instance_raw = self.manila(cmd, microversion=microversion)
        snapshot_instance = output_parser.details(snapshot_instance_raw)
        return snapshot_instance

    def reset_snapshot_instance(self, id=None, state=None, microversion=None):
        """Reset snapshot instance status."""
        cmd = 'snapshot-instance-reset-state %s ' % id
        if state:
            cmd += '--state %s' % state
        snapshot_instance_raw = self.manila(cmd, microversion=microversion)
        snapshot_instance = utils.listing(snapshot_instance_raw)
        return snapshot_instance

    def is_snapshot_deleted(self, snapshot, microversion=None):
        """Indicates whether snapshot is deleted or not.

        :param snapshot: str -- Name or ID of snapshot
        """
        try:
            self.get_snapshot(snapshot, microversion=microversion)
            return False
        except tempest_lib_exc.NotFound:
            return True

    def wait_for_snapshot_deletion(self, snapshot, microversion=None):
        """Wait for snapshot deletion by its Name or ID.

        :param snapshot: str -- Name or ID of snapshot
        """
        self.wait_for_resource_deletion(
            SNAPSHOT, res_id=snapshot, interval=5, timeout=300,
            microversion=microversion)

    def wait_for_snapshot_status(self, snapshot, status, microversion=None):
        """Waits for a snapshot to reach a given status."""
        body = self.get_snapshot(snapshot, microversion=microversion)
        snapshot_name = body['name']
        snapshot_status = body['status']
        start = int(time.time())

        while snapshot_status != status:
            time.sleep(self.build_interval)
            body = self.get_snapshot(snapshot, microversion=microversion)
            snapshot_status = body['status']

            if snapshot_status == status:
                return
            elif 'error' in snapshot_status.lower():
                raise exceptions.SnapshotBuildErrorException(snapshot=snapshot)

            if int(time.time()) - start >= self.build_timeout:
                message = (
                    "Snapshot %(snapshot_name)s failed to reach %(status)s "
                    "status within the required time (%(timeout)s s)." % {
                        "snapshot_name": snapshot_name, "status": status,
                        "timeout": self.build_timeout})
                raise tempest_lib_exc.TimeoutException(message)

    @not_found_wrapper
    def list_access(self, entity_id, columns=None, microversion=None,
                    is_snapshot=False, metadata=None):
        """Returns list of access rules for a share.

        :param entity_id: str -- Name or ID of a share or snapshot.
        :param columns: comma separated string of columns.
            Example, "--columns access_type,access_to"
        :param is_snapshot: Boolean value to determine if should list
            access of a share or snapshot.
        """
        if is_snapshot:
            cmd = 'snapshot-access-list %s ' % entity_id
        else:
            cmd = 'access-list %s ' % entity_id
        if columns is not None:
            cmd += ' --columns ' + columns
        if metadata:
            metadata_cli = ''
            for k, v in metadata.items():
                metadata_cli += '%(k)s=%(v)s ' % {'k': k, 'v': v}
            if metadata_cli:
                cmd += ' --metadata %s ' % metadata_cli
        access_list_raw = self.manila(cmd, microversion=microversion)
        return output_parser.listing(access_list_raw)

    @not_found_wrapper
    def get_access(self, share_id, access_id, microversion=None,
                   is_snapshot=False):
        for access in self.list_access(share_id, microversion=microversion,
                                       is_snapshot=is_snapshot):
            if access['id'] == access_id:
                return access
        raise tempest_lib_exc.NotFound()

    @not_found_wrapper
    def access_show(self, access_id, microversion=None):
        raw_access = self.manila("access-show %s" % access_id,
                                 microversion=microversion)
        return output_parser.details(raw_access)

    @not_found_wrapper
    def access_set_metadata(self, access_id, metadata, microversion=None):
        if not (isinstance(metadata, dict) and metadata):
            msg = ('Provided invalid metadata for setting of access rule'
                   ' metadata - %s' % metadata)
            raise exceptions.InvalidData(message=msg)
        cmd = "access-metadata %s set " % access_id
        for k, v in metadata.items():
            cmd += '%(k)s=%(v)s ' % {'k': k, 'v': v}
        return self.manila(cmd, microversion=microversion)

    @not_found_wrapper
    def access_unset_metadata(self, access_id, keys, microversion=None):
        if not (isinstance(keys, (list, tuple, set)) and keys):
            raise exceptions.InvalidData(
                message='Provided invalid keys - %s' % keys)
        cmd = 'access-metadata %s unset ' % access_id
        for key in keys:
            cmd += '%s ' % key
        return self.manila(cmd, microversion=microversion)

    @not_found_wrapper
    def snapshot_access_allow(self, snapshot_id, access_type, access_to,
                              microversion=None):
        raw_access = self.manila(
            'snapshot-access-allow %(id)s %(type)s %(access_to)s' % {
                'id': snapshot_id,
                'type': access_type,
                'access_to': access_to,
            },
            microversion=microversion)
        return output_parser.details(raw_access)

    @not_found_wrapper
    def snapshot_access_deny(self, snapshot_id, access_id, microversion=None):
        return self.manila(
            'snapshot-access-deny %(share_id)s %(access_id)s' % {
                'share_id': snapshot_id,
                'access_id': access_id,
            },
            microversion=microversion)

    @not_found_wrapper
    def access_allow(self, share_id, access_type, access_to, access_level,
                     metadata=None, microversion=None):
        cmd = ('access-allow  --access-level %(level)s %(id)s %(type)s '
               '%(access_to)s' % {
                   'level': access_level,
                   'id': share_id,
                   'type': access_type,
                   'access_to': access_to})
        if metadata:
            metadata_cli = ''
            for k, v in metadata.items():
                metadata_cli += '%(k)s=%(v)s ' % {'k': k, 'v': v}
            if metadata_cli:
                cmd += ' --metadata %s ' % metadata_cli
        raw_access = self.manila(cmd, microversion=microversion)
        return output_parser.details(raw_access)

    @not_found_wrapper
    def access_deny(self, share_id, access_id, microversion=None):
        return self.manila(
            'access-deny %(share_id)s %(access_id)s' % {
                'share_id': share_id,
                'access_id': access_id,
            },
            microversion=microversion)

    def wait_for_access_rule_status(self, share_id, access_id, state='active',
                                    microversion=None, is_snapshot=False):
        access = self.get_access(
            share_id, access_id, microversion=microversion,
            is_snapshot=is_snapshot)

        start = int(time.time())
        while access['state'] != state:
            time.sleep(self.build_interval)
            access = self.get_access(
                share_id, access_id, microversion=microversion,
                is_snapshot=is_snapshot)

            if access['state'] == state:
                return
            elif access['state'] == 'error':
                raise exceptions.AccessRuleCreateErrorException(
                    access=access_id)

            if int(time.time()) - start >= self.build_timeout:
                message = (
                    "Access rule %(access)s failed to reach %(state)s state "
                    "within the required time (%(build_timeout)s s)." % {
                        "access": access_id, "state": state,
                        "build_timeout": self.build_timeout})
                raise tempest_lib_exc.TimeoutException(message)

    def wait_for_access_rule_deletion(self, share_id, access_id,
                                      microversion=None, is_snapshot=False):
        try:
            access = self.get_access(
                share_id, access_id, microversion=microversion,
                is_snapshot=is_snapshot)
        except tempest_lib_exc.NotFound:
            return

        start = int(time.time())
        while True:
            time.sleep(self.build_interval)
            try:
                access = self.get_access(
                    share_id, access_id, microversion=microversion,
                    is_snapshot=is_snapshot)
            except tempest_lib_exc.NotFound:
                return

            if access['state'] == 'error':
                raise exceptions.AccessRuleDeleteErrorException(
                    access=access_id)

            if int(time.time()) - start >= self.build_timeout:
                message = (
                    "Access rule %(access)s failed to reach deleted state "
                    "within the required time (%(timeout)s s)." %
                    {"access": access_id, "timeout": self.build_timeout})
                raise tempest_lib_exc.TimeoutException(message)

    def reset_task_state(self, share_id, state, version=None):
        state = '--task_state %s' % state if state else ''
        return self.manila('reset-task-state %(state)s %(share)s' % {
            'state': state,
            'share': share_id,
        }, microversion=version)

    def migration_start(self, share_id, dest_host, writable, nondisruptive,
                        preserve_metadata, preserve_snapshots,
                        force_host_assisted_migration, new_share_network=None,
                        new_share_type=None):
        cmd = ('migration-start %(share)s %(host)s '
               '--writable %(writable)s --nondisruptive %(nondisruptive)s '
               '--preserve-metadata %(preserve_metadata)s '
               '--preserve-snapshots %(preserve_snapshots)s') % {
            'share': share_id,
            'host': dest_host,
            'writable': writable,
            'nondisruptive': nondisruptive,
            'preserve_metadata': preserve_metadata,
            'preserve_snapshots': preserve_snapshots,
        }
        if force_host_assisted_migration:
            cmd += (' --force-host-assisted-migration %s'
                    % force_host_assisted_migration)
        if new_share_network:
            cmd += ' --new-share-network %s' % new_share_network
        if new_share_type:
            cmd += ' --new-share-type %s' % new_share_type
        return self.manila(cmd)

    def migration_complete(self, share_id):
        return self.manila('migration-complete %s' % share_id)

    def migration_cancel(self, share_id):
        return self.manila('migration-cancel %s' % share_id)

    def migration_get_progress(self, share_id):
        result = self.manila('migration-get-progress %s' % share_id)
        return output_parser.details(result)

    def pool_list(self, detail=False):
        cmd = 'pool-list'
        if detail:
            cmd += ' --column name,host,backend,pool,capabilities'
        response = self.manila(cmd)
        return output_parser.listing(response)

    def create_security_service(self, type='ldap', name=None, description=None,
                                dns_ip=None, ou=None, server=None, domain=None,
                                user=None, password=None, microversion=None):
        """Creates security service.

        :param type: security service type (ldap, kerberos or active_directory)
        :param name: desired name of new security service.
        :param description: desired description of new security service.
        :param dns_ip: DNS IP address inside tenant's network.
        :param ou: security service organizational unit
        :param server: security service IP address or hostname.
        :param domain: security service domain.
        :param user: user of the new security service.
        :param password: password used by user.
        """

        cmd = 'security-service-create %s ' % type
        cmd += self. _combine_security_service_data(
            name=name,
            description=description,
            dns_ip=dns_ip,
            ou=ou,
            server=server,
            domain=domain,
            user=user,
            password=password)

        ss_raw = self.manila(cmd, microversion=microversion)
        security_service = output_parser.details(ss_raw)
        return security_service

    @not_found_wrapper
    def update_security_service(self, security_service, name=None,
                                description=None, dns_ip=None, ou=None,
                                server=None, domain=None, user=None,
                                password=None, microversion=None):
        cmd = 'security-service-update %s ' % security_service
        cmd += self. _combine_security_service_data(
            name=name,
            description=description,
            dns_ip=dns_ip,
            ou=ou,
            server=server,
            domain=domain,
            user=user,
            password=password)
        return output_parser.details(
            self.manila(cmd, microversion=microversion))

    def _combine_security_service_data(self, name=None, description=None,
                                       dns_ip=None, ou=None, server=None,
                                       domain=None, user=None, password=None):
        data = ''
        if name is not None:
            data += '--name %s ' % name
        if description is not None:
            data += '--description %s ' % description
        if dns_ip is not None:
            data += '--dns-ip %s ' % dns_ip
        if ou is not None:
            data += '--ou %s ' % ou
        if server is not None:
            data += '--server %s ' % server
        if domain is not None:
            data += '--domain %s ' % domain
        if user is not None:
            data += '--user %s ' % user
        if password is not None:
            data += '--password %s ' % password
        return data

    @not_found_wrapper
    def list_share_export_locations(self, share, columns=None,
                                    microversion=None):
        """List share export locations.

        :param share: str -- Name or ID of a share.
        :param columns: str -- comma separated string of columns.
            Example, "--columns uuid,path".
        :param microversion: API microversion to be used for request.
        """
        cmd = "share-export-location-list %s" % share
        if columns is not None:
            cmd += " --columns " + columns
        export_locations_raw = self.manila(cmd, microversion=microversion)
        export_locations = utils.listing(export_locations_raw)
        return export_locations

    @not_found_wrapper
    def get_snapshot_export_location(self, snapshot, export_location_uuid,
                                     microversion=None):
        """Returns an export location by snapshot and its UUID.

        :param snapshot: str -- Name or ID of a snapshot.
        :param export_location_uuid: str -- UUID of an export location.
        :param microversion: API microversion to be used for request.
        """
        snapshot_raw = self.manila(
            'snapshot-export-location-show %(snapshot)s %(el_uuid)s' % {
                'snapshot': snapshot,
                'el_uuid': export_location_uuid,
            },
            microversion=microversion)
        snapshot = output_parser.details(snapshot_raw)
        return snapshot

    @not_found_wrapper
    def get_snapshot_instance_export_location(
            self, snapshot, export_location_uuid, microversion=None):
        """Returns an export location by snapshot instance and its UUID.

        :param snapshot: str -- Name or ID of a snapshot instance.
        :param export_location_uuid: str -- UUID of an export location.
        :param microversion: API microversion to be used for request.
        """
        snapshot_raw = self.manila(
            'snapshot-instance-export-location-show %(snapshot)s %(el_uuid)s'
            % {'snapshot': snapshot, 'el_uuid': export_location_uuid},
            microversion=microversion)
        snapshot = output_parser.details(snapshot_raw)
        return snapshot

    @not_found_wrapper
    def get_share_export_location(self, share, export_location_uuid,
                                  microversion=None):
        """Returns an export location by share and its UUID.

        :param share: str -- Name or ID of a share.
        :param export_location_uuid: str -- UUID of an export location.
        :param microversion: API microversion to be used for request.
        """
        share_raw = self.manila(
            'share-export-location-show %(share)s %(el_uuid)s' % {
                'share': share,
                'el_uuid': export_location_uuid,
            },
            microversion=microversion)
        share = output_parser.details(share_raw)
        return share

    @not_found_wrapper
    @forbidden_wrapper
    def list_share_instance_export_locations(self, share_instance,
                                             columns=None, microversion=None):
        """List share instance export locations.

        :param share_instance: str -- Name or ID of a share instance.
        :param columns: str -- comma separated string of columns.
            Example, "--columns uuid,path".
        :param microversion: API microversion to be used for request.
        """
        cmd = "share-instance-export-location-list %s" % share_instance
        if columns is not None:
            cmd += " --columns " + columns
        export_locations_raw = self.manila(cmd, microversion=microversion)
        export_locations = utils.listing(export_locations_raw)
        return export_locations

    @not_found_wrapper
    @forbidden_wrapper
    def get_share_instance_export_location(self, share_instance,
                                           export_location_uuid,
                                           microversion=None):
        """Returns an export location by share instance and its UUID.

        :param share_instance: str -- Name or ID of a share instance.
        :param export_location_uuid: str -- UUID of an export location.
        :param microversion: API microversion to be used for request.
        """
        share_raw = self.manila(
            'share-instance-export-location-show '
            '%(share_instance)s %(el_uuid)s' % {
                'share_instance': share_instance,
                'el_uuid': export_location_uuid,
            },
            microversion=microversion)
        share = output_parser.details(share_raw)
        return share

    # Share servers

    @not_found_wrapper
    def get_share_server(self, share_server, microversion=None):
        """Returns share server by its Name or ID."""
        share_server_raw = self.manila(
            'share-server-show %s' % share_server, microversion=microversion)
        share_server = output_parser.details(share_server_raw)
        return share_server

    def list_share_servers(self, filters=None, columns=None,
                           microversion=None):
        """List share servers.

        :param filters: dict -- filters for listing of share servers.
            Example, input:
                {'project_id': 'foo'}
                {'-project_id': 'foo'}
                {'--project_id': 'foo'}
                {'project-id': 'foo'}
            will be transformed to filter parameter "--project-id=foo"
         :param columns: comma separated string of columns.
            Example, "--columns id"
        """
        cmd = 'share-server-list '
        if columns is not None:
            cmd += ' --columns ' + columns
        if filters and isinstance(filters, dict):
            for k, v in filters.items():
                cmd += '%(k)s=%(v)s ' % {
                    'k': self._stranslate_to_cli_optional_param(k), 'v': v}
        share_servers_raw = self.manila(cmd, microversion=microversion)
        share_servers = utils.listing(share_servers_raw)
        return share_servers

    @not_found_wrapper
    def delete_share_server(self, share_server, microversion=None):
        """Deletes share server by its Name or ID."""
        return self.manila('share-server-delete %s' % share_server,
                           microversion=microversion)

    def is_share_server_deleted(self, share_server_id, microversion=None):
        """Says whether share server is deleted or not.

        :param share_server: text -- ID of the share server
        """
        servers = self.list_share_servers(microversion=microversion)
        for list_element in servers:
            if share_server_id == list_element['Id']:
                return False
        return True

    def wait_for_share_server_deletion(self, share_server, microversion=None):
        """Wait for share server deletion by its Name or ID.

        :param share_server: text -- Name or ID of share server
        """
        self.wait_for_resource_deletion(
            SHARE_SERVER, res_id=share_server, interval=3, timeout=60,
            microversion=microversion)

    def unmanage_share(self, server_id):
        return self.manila('unmanage %s ' % server_id)

    def unmanage_server(self, share_server_id):
        return self.manila('share-server-unmanage %s ' % share_server_id)

    def share_server_manage(self, host, share_network, identifier,
                            driver_options=None):
        if driver_options:
            command = ('share-server-manage %s %s %s %s' %
                       (host, share_network, identifier, driver_options))
        else:
            command = ('share-server-manage %s %s %s' % (host, share_network,
                       identifier))
        managed_share_server_raw = self.manila(command)
        managed_share_server = output_parser.details(managed_share_server_raw)
        return managed_share_server['id']

    def manage_share(self, host, protocol, export_location, share_server):
        managed_share_raw = self.manila(
            'manage %s %s %s --share-server-id %s' % (host, protocol,
                                                      export_location,
                                                      share_server))
        managed_share = output_parser.details(managed_share_raw)
        return managed_share['id']

    # user messages

    def wait_for_message(self, resource_id):
        """Waits until a message for a resource with given id exists"""
        start = int(time.time())
        message = None

        while not message:
            time.sleep(self.build_interval)
            for msg in self.list_messages():
                if msg['Resource ID'] == resource_id:
                    return msg

            if int(time.time()) - start >= self.build_timeout:
                message = ('No message for resource with id %s was created in'
                           ' the required time (%s s).' %
                           (resource_id, self.build_timeout))
                raise tempest_lib_exc.TimeoutException(message)

    def list_messages(self, columns=None, microversion=None):
        """List messages.

        :param columns: str -- comma separated string of columns.
            Example, "--columns id,resource_id".
        :param microversion: API microversion to be used for request.
        """
        cmd = "message-list"
        if columns is not None:
            cmd += " --columns " + columns
        messages_raw = self.manila(cmd, microversion=microversion)
        messages = utils.listing(messages_raw)
        return messages

    @not_found_wrapper
    def get_message(self, message, microversion=None):
        """Returns share server by its Name or ID."""
        message_raw = self.manila(
            'message-show %s' % message, microversion=microversion)
        message = output_parser.details(message_raw)
        return message

    @not_found_wrapper
    def delete_message(self, message, microversion=None):
        """Deletes message by its ID."""
        return self.manila('message-delete %s' % message,
                           microversion=microversion)

    def is_message_deleted(self, message, microversion=None):
        """Indicates whether message is deleted or not.

        :param message: str -- ID of message
        """
        try:
            self.get_message(message, microversion=microversion)
            return False
        except tempest_lib_exc.NotFound:
            return True

    def wait_for_message_deletion(self, message, microversion=None):
        """Wait for message deletion by its ID.

        :param message: text -- ID of message
        """
        self.wait_for_resource_deletion(
            MESSAGE, res_id=message, interval=3, timeout=60,
            microversion=microversion)

    # Share replicas

    def create_share_replica(self, share, microversion=None):
        """Create a share replica.

        :param share: str -- Name or ID of a share to create a replica of
        """
        cmd = "share-replica-create %s" % share
        replica = self.manila(cmd, microversion=microversion)
        return output_parser.details(replica)

    @not_found_wrapper
    def get_share_replica(self, replica, microversion=None):
        cmd = "share-replica-show %s" % replica
        replica = self.manila(cmd, microversion=microversion)
        return output_parser.details(replica)

    @not_found_wrapper
    @forbidden_wrapper
    def delete_share_replica(self, share_replica, microversion=None):
        """Deletes share replica by ID."""
        return self.manila(
            "share-replica-delete %s" % share_replica,
            microversion=microversion)

    def is_share_replica_deleted(self, replica, microversion=None):
        """Indicates whether a share replica is deleted or not.

        :param replica: str -- ID of share replica
        """
        try:
            self.get_share_replica(replica, microversion=microversion)
            return False
        except tempest_lib_exc.NotFound:
            return True

    def wait_for_share_replica_deletion(self, replica, microversion=None):
        """Wait for share replica deletion by its ID.

        :param replica: text -- ID of share replica
        """
        self.wait_for_resource_deletion(
            SHARE_REPLICA, res_id=replica, interval=3, timeout=60,
            microversion=microversion)

    def wait_for_share_replica_status(self, share_replica,
                                      status="available",
                                      microversion=None):
        """Waits for a share replica to reach a given status."""
        replica = self.get_share_replica(share_replica,
                                         microversion=microversion)
        share_replica_status = replica['status']
        start = int(time.time())

        while share_replica_status != status:
            time.sleep(self.build_interval)
            replica = self.get_share_replica(share_replica,
                                             microversion=microversion)
            share_replica_status = replica['status']

            if share_replica_status == status:
                return replica
            elif 'error' in share_replica_status.lower():
                raise exceptions.ShareReplicaBuildErrorException(
                    replica=share_replica)

            if int(time.time()) - start >= self.build_timeout:
                message = (
                    "Share replica %(id)s failed to reach %(status)s "
                    "status within the required time "
                    "(%(build_timeout)s s)." % {
                        "id": share_replica, "status": status,
                        "build_timeout": self.build_timeout})
                raise tempest_lib_exc.TimeoutException(message)
        return replica

    @not_found_wrapper
    @forbidden_wrapper
    def list_share_replica_export_locations(self, share_replica,
                                            columns=None, microversion=None):
        """List share replica export locations.

        :param share_replica: str -- ID of share replica.
        :param columns: str -- comma separated string of columns.
            Example, "--columns id,path".
        :param microversion: API microversion to be used for request.
        """
        cmd = "share-replica-export-location-list %s" % share_replica
        if columns is not None:
            cmd += " --columns " + columns
        export_locations_raw = self.manila(cmd, microversion=microversion)
        export_locations = utils.listing(export_locations_raw)
        return export_locations

    @not_found_wrapper
    @forbidden_wrapper
    def get_share_replica_export_location(self, share_replica,
                                          export_location_uuid,
                                          microversion=None):
        """Returns an export location by share replica and export location ID.

        :param share_replica: str -- ID of share replica.
        :param export_location_uuid: str -- UUID of an export location.
        :param microversion: API microversion to be used for request.
        """
        export_raw = self.manila(
            'share-replica-export-location-show '
            '%(share_replica)s %(el_uuid)s' % {
                'share_replica': share_replica,
                'el_uuid': export_location_uuid,
            },
            microversion=microversion)
        export = output_parser.details(export_raw)
        return export
