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

from __future__ import print_function


import os
import sys
import time

from oslo_utils import strutils
import six

from manilaclient import api_versions
from manilaclient.common.apiclient import utils as apiclient_utils
from manilaclient.common import cliutils
from manilaclient.common import constants
from manilaclient import exceptions
from manilaclient.v2 import quotas


def _poll_for_status(poll_fn, obj_id, action, final_ok_states,
                     poll_period=5, show_progress=True):
    """Block while action is performed, periodically printing progress."""
    def print_progress(progress):
        if show_progress:
            msg = ('\rInstance %(action)s... %(progress)s%% complete'
                   % dict(action=action, progress=progress))
        else:
            msg = '\rInstance %(action)s...' % dict(action=action)

        sys.stdout.write(msg)
        sys.stdout.flush()

    print()
    while True:
        obj = poll_fn(obj_id)
        status = obj.status.lower()
        progress = getattr(obj, 'progress', None) or 0
        if status in final_ok_states:
            print_progress(100)
            print("\nFinished")
            break
        elif status == "error":
            print("\nError %(action)s instance" % {'action': action})
            break
        else:
            print_progress(progress)
            time.sleep(poll_period)


def _find_share(cs, share):
    """Get a share by ID."""
    return apiclient_utils.find_resource(cs.shares, share)


def _transform_export_locations_to_string_view(export_locations):
    export_locations_string_view = ''
    replica_export_location_ignored_keys = (
        'replica_state', 'availability_zone', 'share_replica_id')
    for el in export_locations:
        if hasattr(el, '_info'):
            export_locations_dict = el._info
        else:
            export_locations_dict = el
        for k, v in export_locations_dict.items():
            # NOTE(gouthamr): We don't want to show replica related info
            # twice in the output, so ignore those.
            if k not in replica_export_location_ignored_keys:
                export_locations_string_view += '\n%(k)s = %(v)s' % {
                    'k': k, 'v': v}
    return export_locations_string_view


@api_versions.wraps("1.0", "2.8")
def _print_share(cs, share):
    info = share._info.copy()
    info.pop('links', None)

    # NOTE(vponomaryov): remove deprecated single field 'export_location' and
    # leave only list field 'export_locations'. Also, transform the latter to
    # text with new line separators to make it pretty in CLI.
    # It will look like following:
    # +-------------------+--------------------------------------------+
    # | Property          | Value                                      |
    # +-------------------+--------------------------------------------+
    # | status            | available                                  |
    # | export_locations  | 1.2.3.4:/f/o/o                             |
    # |                   | 5.6.7.8:/b/a/r                             |
    # |                   | 9.10.11.12:/q/u/u/z                        |
    # | id                | d778d2ee-b6bb-4c5f-9f5d-6f3057d549b1       |
    # | size              | 1                                          |
    # | share_proto       | NFS                                        |
    # +-------------------+--------------------------------------------+
    if info.get('export_locations'):
        info.pop('export_location', None)
        info['export_locations'] = "\n".join(info['export_locations'])

    # No need to print both volume_type and share_type to CLI
    if 'volume_type' in info and 'share_type' in info:
        info.pop('volume_type', None)

    cliutils.print_dict(info)


@api_versions.wraps("2.9")  # noqa
def _print_share(cs, share):
    info = share._info.copy()
    info.pop('links', None)

    # NOTE(vponomaryov): remove deprecated single field 'export_location' and
    # leave only list field 'export_locations'. Also, transform the latter to
    # text with new line separators to make it pretty in CLI.
    # It will look like following:
    # +-------------------+--------------------------------------------+
    # | Property          | Value                                      |
    # +-------------------+--------------------------------------------+
    # | status            | available                                  |
    # | export_locations  |                                            |
    # |                   | uuid = FOO-UUID                            |
    # |                   | path = 5.6.7.8:/foo/export/location/path   |
    # |                   |                                            |
    # |                   | uuid = BAR-UUID                            |
    # |                   | path = 5.6.7.8:/bar/export/location/path   |
    # |                   |                                            |
    # | id                | d778d2ee-b6bb-4c5f-9f5d-6f3057d549b1       |
    # | size              | 1                                          |
    # | share_proto       | NFS                                        |
    # +-------------------+--------------------------------------------+
    if info.get('export_locations'):
        info['export_locations'] = (
            _transform_export_locations_to_string_view(
                info['export_locations']))

    # No need to print both volume_type and share_type to CLI
    if 'volume_type' in info and 'share_type' in info:
        info.pop('volume_type', None)

    cliutils.print_dict(info)


def _find_share_instance(cs, instance):
    """Get a share instance by ID."""
    return apiclient_utils.find_resource(cs.share_instances, instance)


def _print_type_show(stype, default_share_type=None):

    if hasattr(stype, 'is_default'):
        is_default = 'YES' if stype.is_default else 'NO'
    elif default_share_type:
        is_default = 'YES' if stype.id == default_share_type.id else 'NO'
    else:
        is_default = 'NO'

    stype_dict = {
        'id': stype.id,
        'name': stype.name,
        'visibility': _is_share_type_public(stype),
        'is_default': is_default,
        'description': None,
        'required_extra_specs': _print_type_required_extra_specs(stype),
        'optional_extra_specs': _print_type_optional_extra_specs(stype),
    }
    cliutils.print_dict(stype_dict)


@api_versions.wraps("1.0", "2.8")
def _print_share_instance(cs, instance):
    info = instance._info.copy()
    info.pop('links', None)
    cliutils.print_dict(info)


@api_versions.wraps("2.9")  # noqa
def _print_share_instance(cs, instance):
    info = instance._info.copy()
    info.pop('links', None)
    if info.get('export_locations'):
        info['export_locations'] = (
            _transform_export_locations_to_string_view(
                info['export_locations']))
    cliutils.print_dict(info)


def _find_share_replica(cs, replica):
    """Get a replica by ID."""
    return apiclient_utils.find_resource(cs.share_replicas, replica)


@api_versions.wraps("2.11", "2.46")
def _print_share_replica(cs, replica):
    info = replica._info.copy()
    info.pop('links', None)
    cliutils.print_dict(info)


@api_versions.wraps("2.47")  # noqa
def _print_share_replica(cs, replica):
    info = replica._info.copy()
    info.pop('links', None)
    if info.get('export_locations'):
        info['export_locations'] = (
            _transform_export_locations_to_string_view(
                info['export_locations']))
    cliutils.print_dict(info)


@api_versions.experimental_api
@api_versions.wraps("2.31")
def _find_share_group(cs, share_group):
    """Get a share group ID."""
    return apiclient_utils.find_resource(cs.share_groups, share_group)


def _print_share_group(cs, share_group):
    info = share_group._info.copy()
    info.pop('links', None)

    if info.get('share_types'):
        info['share_types'] = "\n".join(info['share_types'])

    cliutils.print_dict(info)


@api_versions.experimental_api
@api_versions.wraps("2.31")
def _find_share_group_snapshot(cs, share_group_snapshot):
    """Get a share group snapshot by name or ID."""
    return apiclient_utils.find_resource(
        cs.share_group_snapshots, share_group_snapshot)


def _print_share_group_snapshot(cs, share_group_snapshot):
    info = share_group_snapshot._info.copy()
    info.pop('links', None)
    info.pop('members', None)
    cliutils.print_dict(info)


def _print_share_group_snapshot_members(cs, share_group_snapshot):
    info = share_group_snapshot._info.copy()
    cliutils.print_dict(info.get('members', {}))


def _find_share_snapshot(cs, snapshot):
    """Get a snapshot by ID."""
    return apiclient_utils.find_resource(cs.share_snapshots, snapshot)


def _print_share_snapshot(cs, snapshot):
    info = snapshot._info.copy()
    info.pop('links', None)

    if info.get('export_locations'):
        info['export_locations'] = (
            _transform_export_locations_to_string_view(
                info['export_locations']))

    cliutils.print_dict(info)


def _quota_set_pretty_show(quotas):
    """Convert quotas object to dict and display."""

    new_quotas = {}
    for quota_k, quota_v in sorted(quotas.to_dict().items()):
        if isinstance(quota_v, dict):
            quota_v = '\n'.join(
                ['%s = %s' % (k, v) for k, v in sorted(quota_v.items())])
        new_quotas[quota_k] = quota_v

    cliutils.print_dict(new_quotas)


def _find_share_snapshot_instance(cs, snapshot_instance):
    """Get a share snapshot instance by ID."""
    return apiclient_utils.find_resource(
        cs.share_snapshot_instances, snapshot_instance)


def _find_share_network(cs, share_network):
    """Get a share network by ID or name."""
    return apiclient_utils.find_resource(cs.share_networks, share_network)


def _find_security_service(cs, security_service):
    """Get a security service by ID or name."""
    return apiclient_utils.find_resource(cs.security_services,
                                         security_service)


def _find_share_server(cs, share_server):
    """Get a share server by ID."""
    return apiclient_utils.find_resource(cs.share_servers, share_server)


def _find_message(cs, message):
    """Get a message by ID."""
    return apiclient_utils.find_resource(cs.messages, message)


def _translate_keys(collection, convert):
    for item in collection:
        keys = item.__dict__
        for from_key, to_key in convert:
            if from_key in keys and to_key not in keys:
                setattr(item, to_key, item._info[from_key])


def _extract_metadata(args):
    return _extract_key_value_options(args, 'metadata')


def _extract_extra_specs(args):
    return _extract_key_value_options(args, 'extra_specs')


def _extract_group_specs(args):
    return _extract_key_value_options(args, 'group_specs')


def _extract_key_value_options(args, option_name):
    result_dict = {}
    duplicate_options = []

    options = getattr(args, option_name, None)

    if options:
        for option in options:
            # unset doesn't require a val, so we have the if/else
            if '=' in option:
                (key, value) = option.split('=', 1)
            else:
                key = option
                value = None

            if key not in result_dict:
                result_dict[key] = value
            else:
                duplicate_options.append(key)

        if len(duplicate_options) > 0:
            duplicate_str = ', '.join(duplicate_options)
            msg = "Following options were duplicated: %s" % duplicate_str
            raise exceptions.CommandError(msg)
    return result_dict


def _split_columns(columns, title=True):
    if title:
        list_of_keys = list(map(lambda x: x.strip().title(),
                                columns.split(",")))
    else:
        list_of_keys = list(map(lambda x: x.strip().lower(),
                                columns.split(",")))
    return list_of_keys


@api_versions.wraps("2.0")
def do_api_version(cs, args):
    """Display the API version information."""
    columns = ['ID', 'Status', 'Version', 'Min_version']
    column_labels = ['ID', 'Status', 'Version', 'Minimum Version']
    response = cs.services.server_api_version()
    cliutils.print_list(response, columns, field_labels=column_labels)


def do_endpoints(cs, args):
    """Discover endpoints that get returned from the authenticate services."""
    catalog = cs.keystone_client.service_catalog.catalog
    for e in catalog.get('serviceCatalog', catalog.get('catalog')):
        cliutils.print_dict(e['endpoints'][0], e['name'])


def do_credentials(cs, args):
    """Show user credentials returned from auth."""
    catalog = cs.keystone_client.service_catalog.catalog
    cliutils.print_dict(catalog['user'], "User Credentials")
    if not catalog['version'] == 'v3':
        data = catalog['token']
    else:
        data = {
            'issued_at': catalog['issued_at'],
            'expires': catalog['expires_at'],
            'id': catalog['auth_token'],
            'audit_ids': catalog['audit_ids'],
            'tenant': catalog['project'],
        }
    cliutils.print_dict(data, "Token")

_quota_resources = [
    'shares',
    'snapshots',
    'gigabytes',
    'snapshot_gigabytes',
    'share_networks',
]


def _quota_update(manager, identifier, args):
    updates = {}
    for resource in _quota_resources:
        val = getattr(args, resource, None)
        if val is not None:
            updates[resource] = val

    if updates:
        # default value of force is None to make sure this client
        # will be compatible with old nova server
        force_update = getattr(args, 'force', None)
        user_id = getattr(args, 'user', None)
        if isinstance(manager, quotas.QuotaSetManager):
            manager.update(identifier, force=force_update, user_id=user_id,
                           **updates)
        else:
            manager.update(identifier, **updates)


@cliutils.arg(
    '--tenant-id',
    metavar='<tenant-id>',
    default=None,
    help='ID of tenant to list the quotas for.')
@cliutils.arg(
    '--user-id',
    metavar='<user-id>',
    default=None,
    help="ID of user to list the quotas for. Optional. "
         "Mutually exclusive with '--share-type'.")
@cliutils.arg(
    '--share-type',
    '--share_type',
    metavar='<share-type>',
    type=str,
    default=None,
    action='single_alias',
    help="UUID or name of a share type to set the quotas for. Optional. "
         "Mutually exclusive with '--user-id'. "
         "Available only for microversion >= 2.39")
@cliutils.arg(
    '--detail',
    action='store_true',
    help='Optional flag to indicate whether to show quota in detail. '
         'Default false, available only for microversion >= 2.25.')
@api_versions.wraps("1.0")
def do_quota_show(cs, args):
    """List the quotas for a tenant/user."""
    project = args.tenant_id or cs.keystone_client.project_id
    kwargs = {
        "tenant_id": project,
        "user_id": args.user_id,
        "detail": args.detail,
    }
    if args.share_type is not None:
        if cs.api_version < api_versions.APIVersion("2.39"):
            raise exceptions.CommandError(
                "'share type' quotas are available only starting with "
                "'2.39' API microversion.")
        kwargs["share_type"] = args.share_type
    _quota_set_pretty_show(cs.quotas.get(**kwargs))


@cliutils.arg(
    '--tenant-id',
    metavar='<tenant-id>',
    default=None,
    help='ID of tenant to list the default quotas for.')
def do_quota_defaults(cs, args):
    """List the default quotas for a tenant."""
    project = args.tenant_id or cs.keystone_client.project_id
    _quota_set_pretty_show(cs.quotas.defaults(project))


@cliutils.arg(
    'tenant_id',
    metavar='<tenant_id>',
    help='UUID of tenant to set the quotas for.')
@cliutils.arg(
    '--user-id',
    metavar='<user-id>',
    default=None,
    help="ID of a user to set the quotas for. Optional. "
         "Mutually exclusive with '--share-type'.")
@cliutils.arg(
    '--shares',
    metavar='<shares>',
    type=int,
    default=None,
    help='New value for the "shares" quota.')
@cliutils.arg(
    '--snapshots',
    metavar='<snapshots>',
    type=int,
    default=None,
    help='New value for the "snapshots" quota.')
@cliutils.arg(
    '--gigabytes',
    metavar='<gigabytes>',
    type=int,
    default=None,
    help='New value for the "gigabytes" quota.')
@cliutils.arg(
    '--snapshot-gigabytes',
    '--snapshot_gigabytes',  # alias
    metavar='<snapshot_gigabytes>',
    type=int,
    default=None,
    action='single_alias',
    help='New value for the "snapshot_gigabytes" quota.')
@cliutils.arg(
    '--share-networks',
    '--share_networks',
    metavar='<share-networks>',
    type=int,
    default=None,
    action='single_alias',
    help='New value for the "share_networks" quota.')
@cliutils.arg(
    '--share-groups', '--share_groups', '--groups',
    metavar='<share_groups>',
    type=int,
    default=None,
    action='single_alias',
    help='New value for the "share_groups" quota.')
@cliutils.arg(
    '--share-group-snapshots', '--share_group_snapshots',
    '--group-snapshots', '--group_snapshots',
    metavar='<share_group_snapshots>',
    type=int,
    default=None,
    action='single_alias',
    help='New value for the "share_group_snapshots" quota.')
@cliutils.arg(
    '--share-type',
    '--share_type',
    metavar='<share-type>',
    type=str,
    default=None,
    action='single_alias',
    help="UUID or name of a share type to set the quotas for. Optional. "
         "Mutually exclusive with '--user-id'. "
         "Available only for microversion >= 2.39")
@cliutils.arg(
    '--force',
    dest='force',
    action="store_true",
    default=None,
    help='Whether force update the quota even if the already used '
         'and reserved exceeds the new quota.')
@api_versions.wraps("1.0")
def do_quota_update(cs, args):
    """Update the quotas for a project/user and/or share type (Admin only)."""
    kwargs = {
        "tenant_id": args.tenant_id,
        "user_id": args.user_id,
        "shares": args.shares,
        "gigabytes": args.gigabytes,
        "snapshots": args.snapshots,
        "snapshot_gigabytes": args.snapshot_gigabytes,
        "share_networks": args.share_networks,
        "force": args.force,
    }
    if args.share_type is not None:
        if cs.api_version < api_versions.APIVersion("2.39"):
            raise exceptions.CommandError(
                "'share type' quotas are available only starting with "
                "'2.39' API microversion.")
        kwargs["share_type"] = args.share_type
    if args.share_groups is not None or args.share_group_snapshots is not None:
        if cs.api_version < api_versions.APIVersion("2.40"):
            raise exceptions.CommandError(
                "'share group' quotas are available only starting with "
                "'2.40' API microversion.")
        elif args.share_type is not None:
            raise exceptions.CommandError(
                "Share type quotas handle only 'shares', 'gigabytes', "
                "'snapshots' and 'snapshot_gigabytes' resources.")
        kwargs["share_groups"] = args.share_groups
        kwargs["share_group_snapshots"] = args.share_group_snapshots
    cs.quotas.update(**kwargs)


@cliutils.arg(
    '--tenant-id',
    metavar='<tenant-id>',
    help='ID of tenant to delete quota for.')
@cliutils.arg(
    '--user-id',
    metavar='<user-id>',
    help="ID of user to delete quota for. Optional."
         "Mutually exclusive with '--share-type'.")
@cliutils.arg(
    '--share-type',
    '--share_type',
    metavar='<share-type>',
    type=str,
    default=None,
    action='single_alias',
    help="UUID or name of a share type to set the quotas for. Optional. "
         "Mutually exclusive with '--user-id'. "
         "Available only for microversion >= 2.39")
@api_versions.wraps("1.0")
def do_quota_delete(cs, args):
    """Delete quota for a tenant/user or tenant/share-type.

    The quota will revert back to default (Admin only).
    """
    project_id = args.tenant_id or cs.keystone_client.project_id
    kwargs = {
        "tenant_id": project_id,
        "user_id": args.user_id,
    }
    if args.share_type is not None:
        if cs.api_version < api_versions.APIVersion("2.39"):
            raise exceptions.CommandError(
                "'share type' quotas are available only starting with "
                "'2.39' API microversion.")
        kwargs["share_type"] = args.share_type

    cs.quotas.delete(**kwargs)


@cliutils.arg(
    'class_name',
    metavar='<class>',
    help='Name of quota class to list the quotas for.')
def do_quota_class_show(cs, args):
    """List the quotas for a quota class."""

    _quota_set_pretty_show(cs.quota_classes.get(args.class_name))


@cliutils.arg(
    'class_name',
    metavar='<class-name>',
    help='Name of quota class to set the quotas for.')
@cliutils.arg(
    '--shares',
    metavar='<shares>',
    type=int,
    default=None,
    help='New value for the "shares" quota.')
@cliutils.arg(
    '--snapshots',
    metavar='<snapshots>',
    type=int,
    default=None,
    help='New value for the "snapshots" quota.')
@cliutils.arg(
    '--gigabytes',
    metavar='<gigabytes>',
    type=int,
    default=None,
    help='New value for the "gigabytes" quota.')
@cliutils.arg(
    '--snapshot-gigabytes',
    '--snapshot_gigabytes',  # alias
    metavar='<snapshot_gigabytes>',
    type=int,
    default=None,
    action='single_alias',
    help='New value for the "snapshot_gigabytes" quota.')
@cliutils.arg(
    '--share-networks',
    '--share_networks',  # alias
    metavar='<share-networks>',
    type=int,
    default=None,
    action='single_alias',
    help='New value for the "share_networks" quota.')
def do_quota_class_update(cs, args):
    """Update the quotas for a quota class (Admin only)."""

    _quota_update(cs.quota_classes, args.class_name, args)


def do_absolute_limits(cs, args):
    """Print a list of absolute limits for a user."""
    limits = cs.limits.get().absolute
    columns = ['Name', 'Value']
    cliutils.print_list(limits, columns)


@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "verb,uri,value".')
def do_rate_limits(cs, args):
    """Print a list of rate limits for a user."""
    limits = cs.limits.get().rate
    columns = ['Verb', 'URI', 'Value', 'Remain', 'Unit', 'Next_Available']

    if args.columns is not None:
        columns = _split_columns(columns=args.columns)

    cliutils.print_list(limits, columns)


@cliutils.arg(
    'share_protocol',
    metavar='<share_protocol>',
    type=str,
    help='Share protocol (NFS, CIFS, CephFS, GlusterFS, HDFS or MAPRFS).')
@cliutils.arg(
    'size',
    metavar='<size>',
    type=int,
    help='Share size in GiB.')
@cliutils.arg(
    '--snapshot-id',
    '--snapshot_id',
    metavar='<snapshot-id>',
    action='single_alias',
    help='Optional snapshot ID to create the share from. (Default=None)',
    default=None)
@cliutils.arg(
    '--name',
    metavar='<name>',
    help='Optional share name. (Default=None)',
    default=None)
@cliutils.arg(
    '--metadata',
    type=str,
    nargs='*',
    metavar='<key=value>',
    help='Metadata key=value pairs (Optional, Default=None).',
    default=None)
@cliutils.arg(
    '--share-network',
    '--share_network',
    metavar='<network-info>',
    action='single_alias',
    help='Optional network info ID or name.',
    default=None)
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional share description. (Default=None)',
    default=None)
@cliutils.arg(
    '--share-type', '--share_type', '--volume-type', '--volume_type',
    metavar='<share-type>',
    default=None,
    action='single_alias',
    help='Optional share type. Use of optional volume type is deprecated. '
         '(Default=None)')
@cliutils.arg(
    '--public',
    dest='public',
    action='store_true',
    default=False,
    help="Level of visibility for share. Defines whether other tenants are "
         "able to see it or not. (Default=False)")
@cliutils.arg(
    '--availability-zone', '--availability_zone', '--az',
    metavar='<availability-zone>',
    default=None,
    action='single_alias',
    help='Availability zone in which share should be created.')
@cliutils.arg(
    '--share-group', '--share_group', '--group',
    metavar='<share-group>',
    action='single_alias',
    help='Optional share group name or ID in which to create the share '
         '(Experimental, Default=None).',
    default=None)
@cliutils.service_type('sharev2')
def do_create(cs, args):
    """Creates a new share (NFS, CIFS, CephFS, GlusterFS, HDFS or MAPRFS)."""

    share_metadata = None
    if args.metadata is not None:
        share_metadata = _extract_metadata(args)

    share_group = None
    if args.share_group:
        share_group = _find_share_group(cs, args.share_group).id

    share_network = None
    if args.share_network:
        share_network = _find_share_network(cs, args.share_network)
    share = cs.shares.create(args.share_protocol, args.size, args.snapshot_id,
                             args.name, args.description,
                             metadata=share_metadata,
                             share_network=share_network,
                             share_type=args.share_type,
                             is_public=args.public,
                             availability_zone=args.availability_zone,
                             share_group_id=share_group)
    _print_share(cs, share)


@api_versions.wraps("2.29")
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of share to migrate.')
@cliutils.arg(
    'host',
    metavar='<host@backend#pool>',
    help="Destination host where share will be migrated to. Use the "
         "format 'host@backend#pool'.")
@cliutils.arg(
    '--force_host_assisted_migration',
    '--force-host-assisted-migration',
    metavar='<True|False>',
    choices=['True', 'False'],
    action='single_alias',
    required=False,
    default=False,
    help="Enforces the use of the host-assisted migration approach, "
         "which bypasses driver optimizations. Default=False.")
@cliutils.arg(
    '--preserve-metadata',
    '--preserve_metadata',
    action='single_alias',
    metavar='<True|False>',
    choices=['True', 'False'],
    required=True,
    help="Enforces migration to preserve all file metadata when moving its "
         "contents. If set to True, host-assisted migration will not be "
         "attempted.")
@cliutils.arg(
    '--preserve-snapshots',
    '--preserve_snapshots',
    action='single_alias',
    metavar='<True|False>',
    choices=['True', 'False'],
    required=True,
    help="Enforces migration of the share snapshots to the destination. If "
         "set to True, host-assisted migration will not be attempted.")
@cliutils.arg(
    '--writable',
    metavar='<True|False>',
    choices=['True', 'False'],
    required=True,
    help="Enforces migration to keep the share writable while contents are "
         "being moved. If set to True, host-assisted migration will not be "
         "attempted.")
@cliutils.arg(
    '--nondisruptive',
    metavar='<True|False>',
    choices=['True', 'False'],
    required=True,
    help="Enforces migration to be nondisruptive. If set to True, "
         "host-assisted migration will not be attempted.")
@cliutils.arg(
    '--new_share_network',
    '--new-share-network',
    metavar='<new_share_network>',
    action='single_alias',
    required=False,
    help='Specify the new share network for the share. Do not specify this '
         'parameter if the migrating share has to be retained within its '
         'current share network.',
    default=None)
@cliutils.arg(
    '--new_share_type',
    '--new-share-type',
    metavar='<new_share_type>',
    required=False,
    action='single_alias',
    help='Specify the new share type for the share. Do not specify this '
         'parameter if the migrating share has to be retained with its '
         'current share type.',
    default=None)
def do_migration_start(cs, args):
    """Migrates share to a new host (Admin only, Experimental)."""
    share = _find_share(cs, args.share)
    new_share_net_id = None
    if args.new_share_network:
        share_net = _find_share_network(cs, args.new_share_network)
        new_share_net_id = share_net.id if share_net else None
    new_share_type_id = None
    if args.new_share_type:
        share_type = _find_share_type(cs, args.new_share_type)
        new_share_type_id = share_type.id if share_type else None
    share.migration_start(args.host, args.force_host_assisted_migration,
                          args.preserve_metadata, args.writable,
                          args.nondisruptive, args.preserve_snapshots,
                          new_share_net_id, new_share_type_id)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of share to complete migration.')
@api_versions.wraps("2.22")
def do_migration_complete(cs, args):
    """Completes migration for a given share (Admin only, Experimental)."""
    share = _find_share(cs, args.share)
    share.migration_complete()


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of share to cancel migration.')
@api_versions.wraps("2.22")
def do_migration_cancel(cs, args):
    """Cancels migration of a given share when copying

    (Admin only, Experimental).
    """
    share = _find_share(cs, args.share)
    share.migration_cancel()


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to modify.')
@cliutils.arg(
    '--task-state',
    '--task_state',
    '--state',
    metavar='<task_state>',
    default='None',
    action='single_alias',
    required=False,
    help=('Indicate which task state to assign the share. Options include '
          'migration_starting, migration_in_progress, migration_completing, '
          'migration_success, migration_error, migration_cancelled, '
          'migration_driver_in_progress, migration_driver_phase1_done, '
          'data_copying_starting, data_copying_in_progress, '
          'data_copying_completing, data_copying_completed, '
          'data_copying_cancelled, data_copying_error. If no value is '
          'provided, None will be used.'))
@api_versions.wraps("2.22")
def do_reset_task_state(cs, args):
    """Explicitly update the task state of a share

    (Admin only, Experimental).
    """
    state = args.task_state
    if args.task_state == 'None':
        state = None
    share = _find_share(cs, args.share)
    share.reset_task_state(state)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to get share migration progress '
         'information.')
@api_versions.wraps("2.22")
def do_migration_get_progress(cs, args):
    """Gets migration progress of a given share when copying

    (Admin only, Experimental).
    """
    share = _find_share(cs, args.share)
    result = share.migration_get_progress()
    # NOTE(ganso): result[0] is response code, result[1] is dict body
    cliutils.print_dict(result[1])


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to update metadata on.')
@cliutils.arg(
    'action',
    metavar='<action>',
    choices=['set', 'unset'],
    help="Actions: 'set' or 'unset'.")
@cliutils.arg(
    'metadata',
    metavar='<key=value>',
    nargs='+',
    default=[],
    help='Metadata to set or unset (key is only necessary on unset).')
def do_metadata(cs, args):
    """Set or delete metadata on a share."""
    share = _find_share(cs, args.share)
    metadata = _extract_metadata(args)

    if args.action == 'set':
        cs.shares.set_metadata(share, metadata)
    elif args.action == 'unset':
        cs.shares.delete_metadata(share, sorted(list(metadata), reverse=True))


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share.')
def do_metadata_show(cs, args):
    """Show metadata of given share."""
    share = _find_share(cs, args.share)
    metadata = cs.shares.get_metadata(share)._info
    cliutils.print_dict(metadata, 'Property')


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to update metadata on.')
@cliutils.arg(
    'metadata',
    metavar='<key=value>',
    nargs='+',
    default=[],
    help='Metadata entry or entries to update.')
def do_metadata_update_all(cs, args):
    """Update all metadata of a share."""
    share = _find_share(cs, args.share)
    metadata = _extract_metadata(args)
    metadata = share.update_all_metadata(metadata)._info['metadata']
    cliutils.print_dict(metadata, 'Property')


@api_versions.wraps("2.9")
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,host,status".')
def do_share_export_location_list(cs, args):
    """List export locations of a given share."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = [
            'ID',
            'Path',
            'Preferred',
        ]
    share = _find_share(cs, args.share)
    export_locations = cs.share_export_locations.list(share)
    cliutils.print_list(export_locations, list_of_keys)


@api_versions.wraps("2.9")
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share.')
@cliutils.arg(
    'export_location',
    metavar='<export_location>',
    help='ID of the share export location.')
def do_share_export_location_show(cs, args):
    """Show export location of the share."""
    share = _find_share(cs, args.share)
    export_location = cs.share_export_locations.get(
        share, args.export_location)
    view_data = export_location._info.copy()
    cliutils.print_dict(view_data)


@cliutils.arg(
    'service_host',
    metavar='<service_host>',
    type=str,
    help='manage-share service host: some.host@driver#pool.')
@cliutils.arg(
    'protocol',
    metavar='<protocol>',
    type=str,
    help='Protocol of the share to manage, such as NFS or CIFS.')
@cliutils.arg(
    'export_path',
    metavar='<export_path>',
    type=str,
    help='Share export path, NFS share such as: 10.0.0.1:/example_path, '
         'CIFS share such as: \\\\10.0.0.1\\example_cifs_share.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    help='Optional share name. (Default=None)',
    default=None)
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional share description. (Default=None)',
    default=None)
@cliutils.arg(
    '--share_type', '--share-type',
    metavar='<share-type>',
    default=None,
    action='single_alias',
    help='Optional share type assigned to share. (Default=None)')
@cliutils.arg(
    '--driver_options', '--driver-options',
    type=str,
    nargs='*',
    metavar='<key=value>',
    action='single_alias',
    help='Driver option key=value pairs (Optional, Default=None).',
    default=None)
@cliutils.arg(
    '--public',
    dest='public',
    action='store_true',
    default=False,
    help="Level of visibility for share. Defines whether other tenants are "
         "able to see it or not. Available only for microversion >= 2.8. "
         "(Default=False)")
@cliutils.arg(
    '--share_server_id', '--share-server-id',
    metavar='<share-server-id>',
    default=None,
    action='single_alias',
    help="Share server associated with share when using a share type with "
         "'driver_handles_share_servers' extra_spec set to True. Available "
         "only for microversion >= 2.49. (Default=None)")
def do_manage(cs, args):
    """Manage share not handled by Manila (Admin only)."""
    driver_options = _extract_key_value_options(args, 'driver_options')
    if cs.api_version.matches(api_versions.APIVersion("2.49"),
                              api_versions.APIVersion()):
        share = cs.shares.manage(
            args.service_host, args.protocol, args.export_path,
            driver_options=driver_options, share_type=args.share_type,
            name=args.name, description=args.description,
            is_public=args.public, share_server_id=args.share_server_id)
    else:
        if args.share_server_id:
            raise exceptions.CommandError("Invalid parameter "
                                          "--share_server_id specified. This"
                                          " parameter is only supported on"
                                          " microversion 2.49 or newer.")
        share = cs.shares.manage(
            args.service_host, args.protocol, args.export_path,
            driver_options=driver_options, share_type=args.share_type,
            name=args.name, description=args.description,
            is_public=args.public)

    _print_share(cs, share)


@api_versions.wraps("2.49")
@cliutils.arg(
    'host',
    metavar='<host>',
    type=str,
    help='Backend name as "<node_hostname>@<backend_name>".')
@cliutils.arg(
    'share_network',
    metavar='<share_network>',
    help="Share network where share server has network allocations in.")
@cliutils.arg(
    'identifier',
    metavar='<identifier>',
    type=str,
    help='A driver-specific share server identifier required by the driver to '
         'manage the share server.')
@cliutils.arg(
    '--driver_options', '--driver-options',
    type=str,
    nargs='*',
    metavar='<key=value>',
    action='single_alias',
    help='One or more driver-specific key=value pairs that may be necessary to'
         ' manage the share server (Optional, Default=None).',
    default=None)
def do_share_server_manage(cs, args):
    """Manage share server not handled by Manila (Admin only)."""
    driver_options = _extract_key_value_options(args, 'driver_options')

    share_network = _find_share_network(cs, args.share_network)

    share_server = cs.share_servers.manage(
        args.host, share_network.id, args.identifier,
        driver_options=driver_options)

    cliutils.print_dict(share_server._info)


@cliutils.arg(
    'share_server_id',
    metavar='<share_server_id>',
    help='ID of the share server to modify.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default=constants.STATUS_ACTIVE,
    help=('Indicate which state to assign the share server. Options include '
          'active, error, creating, deleting, managing, unmanaging, '
          'manage_error and unmanage_error. If no state is provided, active '
          'will be used.'))
@api_versions.wraps("2.49")
def do_share_server_reset_state(cs, args):
    """Explicitly update the state of a share server (Admin only)."""
    cs.share_servers.reset_state(args.share_server_id, args.state)


@api_versions.wraps("2.12")
@cliutils.arg(
    'share',
    metavar='<share>',
    type=str,
    help='Name or ID of the share.')
@cliutils.arg(
    'provider_location',
    metavar='<provider_location>',
    type=str,
    help='Provider location of the snapshot on the backend.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    help='Optional snapshot name (Default=None).',
    default=None)
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional snapshot description (Default=None).',
    default=None)
@cliutils.arg(
    '--driver_options', '--driver-options',
    type=str,
    nargs='*',
    metavar='<key=value>',
    action='single_alias',
    help='Optional driver options as key=value pairs (Default=None).',
    default=None)
def do_snapshot_manage(cs, args):
    """Manage share snapshot not handled by Manila (Admin only)."""
    share_ref = _find_share(cs, args.share)

    driver_options = _extract_key_value_options(args, 'driver_options')

    share_snapshot = cs.share_snapshots.manage(
        share_ref, args.provider_location,
        driver_options=driver_options,
        name=args.name, description=args.description
    )

    _print_share_snapshot(cs, share_snapshot)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share(s).')
def do_unmanage(cs, args):
    """Unmanage share (Admin only)."""
    share_ref = _find_share(cs, args.share)
    share_ref.unmanage()


@api_versions.wraps("2.49")
@cliutils.arg(
    'share_server',
    metavar='<share_server>',
    nargs='+',
    help='ID of the share server(s).')
@cliutils.arg(
    '--force',
    dest='force',
    action="store_true",
    required=False,
    default=False,
    help="Enforces the unmanage share server operation, even if the back-end "
         "driver does not support it.")
def do_share_server_unmanage(cs, args):
    """Unmanage share server (Admin only)."""
    failure_count = 0
    for server in args.share_server:
        try:
            cs.share_servers.unmanage(server, args.force)
        except Exception as e:
            failure_count += 1
            print("Unmanage for share server %s failed: %s" % (server, e),
                  file=sys.stderr)

    if failure_count == len(args.share_server):
        raise exceptions.CommandError("Unable to unmanage any of the "
                                      "specified share servers.")


@api_versions.wraps("2.12")
@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    nargs='+',
    help='Name or ID of the snapshot(s).')
def do_snapshot_unmanage(cs, args):
    """Unmanage one or more share snapshots (Admin only)."""
    failure_count = 0
    for snapshot in args.snapshot:
        try:
            snapshot_ref = _find_share_snapshot(cs, snapshot)
            snapshot_ref.unmanage_snapshot()
        except Exception as e:
            failure_count += 1
            print("Unmanage for share snapshot %s failed: %s" % (snapshot, e),
                  file=sys.stderr)

    if failure_count == len(args.snapshot):
        raise exceptions.CommandError("Unable to unmanage any of the "
                                      "specified snapshots.")


@api_versions.wraps("2.27")
@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the snapshot to restore. The snapshot must be the '
         'most recent one known to manila.')
def do_revert_to_snapshot(cs, args):
    """Revert a share to the specified snapshot."""
    snapshot = _find_share_snapshot(cs, args.snapshot)
    share = _find_share(cs, snapshot.share_id)
    share.revert_to_snapshot(snapshot)


@cliutils.arg(
    'share',
    metavar='<share>',
    nargs='+',
    help='Name or ID of the share(s).')
@cliutils.arg(
    '--share-group', '--share_group', '--group',
    metavar='<share-group>',
    action='single_alias',
    help='Optional share group name or ID which contains the share '
         '(Experimental, Default=None).',
    default=None)
@cliutils.service_type('sharev2')
def do_delete(cs, args):
    """Remove one or more shares."""
    failure_count = 0

    for share in args.share:
        try:
            share_ref = _find_share(cs, share)
            if args.share_group:
                share_group_id = _find_share_group(cs, args.share_group).id
                share_ref.delete(share_group_id=share_group_id)
            else:
                share_ref.delete()
        except Exception as e:
            failure_count += 1
            print("Delete for share %s failed: %s" % (share, e),
                  file=sys.stderr)

    if failure_count == len(args.share):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "shares.")


@cliutils.arg(
    'share',
    metavar='<share>',
    nargs='+',
    help='Name or ID of the share(s) to force delete.')
def do_force_delete(cs, args):
    """Attempt force-delete of share, regardless of state (Admin only)."""
    failure_count = 0
    for share in args.share:
        try:
            _find_share(cs, share).force_delete()
        except Exception as e:
            failure_count += 1
            print("Delete for share %s failed: %s" % (share, e),
                  file=sys.stderr)
    if failure_count == len(args.share):
        raise exceptions.CommandError("Unable to force delete any of "
                                      "specified shares.")


@api_versions.wraps("1.0", "2.8")
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the NAS share.')
def do_show(cs, args):
    """Show details about a NAS share."""
    share = _find_share(cs, args.share)
    _print_share(cs, share)


@api_versions.wraps("2.9")  # noqa
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the NAS share.')
def do_show(cs, args):
    """Show details about a NAS share."""
    share = _find_share(cs, args.share)
    export_locations = cs.share_export_locations.list(share)
    share._info['export_locations'] = export_locations
    _print_share(cs, share)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the NAS share to modify.')
@cliutils.arg(
    'access_type',
    metavar='<access_type>',
    help='Access rule type (only "ip", "user"(user or group), "cert" or '
         '"cephx" are supported).')
@cliutils.arg(
    'access_to',
    metavar='<access_to>',
    help='Value that defines access.')
@cliutils.arg(
    '--access-level',
    '--access_level',  # alias
    metavar='<access_level>',
    type=str,
    default=None,
    choices=['rw', 'ro'],
    action='single_alias',
    help='Share access level ("rw" and "ro" access levels are supported). '
         'Defaults to rw.')
@cliutils.arg(
    '--metadata',
    type=str,
    nargs='*',
    metavar='<key=value>',
    help='Space Separated list of key=value pairs of metadata items. '
         'OPTIONAL: Default=None. Available only for microversion >= 2.45.',
    default=None)
def do_access_allow(cs, args):
    """Allow access to a given share."""
    access_metadata = None
    if cs.api_version.matches(api_versions.APIVersion("2.45"),
                              api_versions.APIVersion()):
        access_metadata = _extract_metadata(args)
    elif getattr(args, 'metadata'):
        raise exceptions.CommandError(
            "Adding metadata to access rules is supported only beyond "
            "API version 2.45")

    share = _find_share(cs, args.share)
    access = share.allow(args.access_type, args.access_to, args.access_level,
                         access_metadata)
    cliutils.print_dict(access)


@api_versions.wraps("2.45")
@cliutils.arg(
    'access_id',
    metavar='<access_id>',
    help='ID of the NAS share access rule.')
def do_access_show(cs, args):
    """Show details about a NAS share access rule."""
    access = cs.share_access_rules.get(args.access_id)
    view_data = access._info.copy()
    cliutils.print_dict(view_data)


@api_versions.wraps("2.45")
@cliutils.arg(
    'access_id',
    metavar='<access_id>',
    help='ID of the NAS share access rule.')
@cliutils.arg(
    'action',
    metavar='<action>',
    choices=['set', 'unset'],
    help="Actions: 'set' or 'unset'.")
@cliutils.arg(
    'metadata',
    metavar='<key=value>',
    nargs='+',
    default=[],
    help='Space separated key=value pairs of metadata items to set. '
         'To unset only keys are required. ')
def do_access_metadata(cs, args):
    """Set or delete metadata on a share access rule."""
    share_access = cs.share_access_rules.get(args.access_id)
    metadata = _extract_metadata(args)

    if args.action == 'set':
        cs.share_access_rules.set_metadata(share_access, metadata)
    elif args.action == 'unset':
        cs.share_access_rules.unset_metadata(
            share_access, sorted(list(metadata), reverse=True))


@api_versions.wraps("2.32")
@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the share snapshot to allow access to.')
@cliutils.arg(
    'access_type',
    metavar='<access_type>',
    help='Access rule type (only "ip", "user"(user or group), "cert" or '
         '"cephx" are supported).')
@cliutils.arg(
    'access_to',
    metavar='<access_to>',
    help='Value that defines access.')
def do_snapshot_access_allow(cs, args):
    """Allow read only access to a snapshot."""
    share_snapshot = _find_share_snapshot(cs, args.snapshot)
    access = share_snapshot.allow(args.access_type, args.access_to)
    cliutils.print_dict(access)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the NAS share to modify.')
@cliutils.arg(
    'id',
    metavar='<id>',
    help='ID of the access rule to be deleted.')
def do_access_deny(cs, args):
    """Deny access to a share."""
    share = _find_share(cs, args.share)
    share.deny(args.id)


@api_versions.wraps("2.32")
@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the share snapshot to deny access to.')
@cliutils.arg(
    'id',
    metavar='<id>',
    nargs='+',
    help='ID(s) of the access rule(s) to be deleted.')
def do_snapshot_access_deny(cs, args):
    """Deny access to a snapshot."""
    failure_count = 0
    snapshot = _find_share_snapshot(cs, args.snapshot)
    for access_id in args.id:
        try:
            snapshot.deny(access_id)
        except Exception as e:
            failure_count += 1
            print("Failed to remove rule %(access)s: %(reason)s."
                  % {'access': access_id, 'reason': e},
                  file=sys.stderr)

    if failure_count == len(args.id):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "snapshot rules.")


@api_versions.wraps("1.0", "2.20")
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "access_type,access_to".')
def do_access_list(cs, args):
    """Show access list for share."""
    list_of_keys = [
        'id', 'access_type', 'access_to', 'access_level', 'state',
    ]

    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)

    share = _find_share(cs, args.share)
    access_list = share.access_list()
    cliutils.print_list(access_list, list_of_keys)


@api_versions.wraps("2.21")  # noqa
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "access_type,access_to".')
def do_access_list(cs, args):
    """Show access list for share."""
    list_of_keys = [
        'id', 'access_type', 'access_to', 'access_level', 'state',
        'access_key'
    ]

    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)

    share = _find_share(cs, args.share)
    access_list = share.access_list()
    cliutils.print_list(access_list, list_of_keys)


@api_versions.wraps("2.33")  # noqa
@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "access_type,access_to".')
@cliutils.arg(
    '--metadata',
    type=str,
    nargs='*',
    metavar='<key=value>',
    help='Filters results by a metadata key and value. OPTIONAL: '
         'Default=None. Available only for microversion >= 2.45',
    default=None)
def do_access_list(cs, args):
    """Show access list for share."""
    list_of_keys = [
        'id', 'access_type', 'access_to', 'access_level', 'state',
        'access_key', 'created_at', 'updated_at',
    ]

    share = _find_share(cs, args.share)
    if cs.api_version < api_versions.APIVersion("2.45"):
        if getattr(args, 'metadata'):
            raise exceptions.CommandError(
                "Filtering access rules by metadata is supported only beyond "
                "API version 2.45")
        access_list = share.access_list()
    else:
        access_list = cs.share_access_rules.access_list(
            share, {'metadata': _extract_metadata(args)})
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    cliutils.print_list(access_list, list_of_keys)


@api_versions.wraps("2.32")
@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the share snapshot to list access of.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "access_type,access_to".')
def do_snapshot_access_list(cs, args):
    """Show access list for a snapshot."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = ['id', 'access_type', 'access_to', 'state']

    snapshot = _find_share_snapshot(cs, args.snapshot)
    access_list = snapshot.access_list()
    cliutils.print_list(access_list, list_of_keys)


@cliutils.arg(
    '--all-tenants',
    dest='all_tenants',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help='Display information from all tenants (Admin only).')
@cliutils.arg(
    '--name',
    metavar='<name>',
    type=six.text_type,
    default=None,
    help='Filter results by name.')
@cliutils.arg(
    '--description',
    metavar='<description>',
    type=six.text_type,
    default=None,
    help='Filter results by description. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--name~',
    metavar='<name~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share name pattern. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--description~',
    metavar='<description~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share description pattern. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--status',
    metavar='<status>',
    type=str,
    default=None,
    help='Filter results by status.')
@cliutils.arg(
    '--share-server-id',
    '--share-server_id', '--share_server-id', '--share_server_id',  # aliases
    metavar='<share_server_id>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by share server ID (Admin only).')
@cliutils.arg(
    '--metadata',
    type=str,
    nargs='*',
    metavar='<key=value>',
    help='Filters results by a metadata key and value. OPTIONAL: '
         'Default=None.',
    default=None)
@cliutils.arg(
    '--extra-specs',
    '--extra_specs',  # alias
    type=str,
    nargs='*',
    metavar='<key=value>',
    action='single_alias',
    help='Filters results by a extra specs key and value of share type that '
         'was used for share creation. OPTIONAL: Default=None.',
    default=None)
@cliutils.arg(
    '--share-type', '--volume-type',
    '--share_type', '--share-type-id', '--volume-type-id',  # aliases
    '--share-type_id', '--share_type-id', '--share_type_id',  # aliases
    '--volume_type', '--volume_type_id',
    metavar='<share_type>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by a share type id or name that was used for share '
         'creation.')
@cliutils.arg(
    '--limit',
    metavar='<limit>',
    type=int,
    default=None,
    help='Maximum number of shares to return. OPTIONAL: Default=None.')
@cliutils.arg(
    '--offset',
    metavar='<offset>',
    type=int,
    default=None,
    help='Set offset to define start point of share listing. '
         'OPTIONAL: Default=None.')
@cliutils.arg(
    '--sort-key',
    '--sort_key',  # alias
    metavar='<sort_key>',
    type=str,
    default=None,
    action='single_alias',
    help='Key to be sorted, available keys are %(keys)s. '
         'OPTIONAL: Default=None.' % {'keys': constants.SHARE_SORT_KEY_VALUES})
@cliutils.arg(
    '--sort-dir',
    '--sort_dir',  # alias
    metavar='<sort_dir>',
    type=str,
    default=None,
    action='single_alias',
    help='Sort direction, available values are %(values)s. '
         'OPTIONAL: Default=None.' % {'values': constants.SORT_DIR_VALUES})
@cliutils.arg(
    '--snapshot',
    metavar='<snapshot>',
    type=str,
    default=None,
    help='Filer results by snapshot name or id, that was used for share.')
@cliutils.arg(
    '--host',
    metavar='<host>',
    default=None,
    help='Filter results by host.')
@cliutils.arg(
    '--share-network',
    '--share_network',  # alias
    metavar='<share_network>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by share-network name or id.')
@cliutils.arg(
    '--project-id',
    '--project_id',  # alias
    metavar='<project_id>',
    type=str,
    default=None,
    action='single_alias',
    help="Filter results by project id. Useful with set key '--all-tenants'.")
@cliutils.arg(
    '--public',
    dest='public',
    action='store_true',
    default=False,
    help="Add public shares from all tenants to result. (Default=False)")
@cliutils.arg(
    '--share-group', '--share_group', '--group',
    metavar='<share_group>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by share group name or ID (Experimental, '
         'Default=None).')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "export_location,is public".')
@cliutils.arg(
    '--export-location', '--export_location',
    metavar='<export_location>',
    type=str,
    default=None,
    action='single_alias',
    help='ID or path of the share export location. '
         'Available only for microversion >= 2.35.')
@cliutils.arg(
    '--count',
    dest='count',
    metavar='<True|False>',
    choices=['True', 'False'],
    default=False,
    help='Display total number of shares to return. '
         'Available only for microversion >= 2.42.')
@cliutils.service_type('sharev2')
def do_list(cs, args):
    """List NAS shares with filters."""

    columns = args.columns
    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))
    if columns is not None:
        list_of_keys = _split_columns(columns=columns)
    else:
        list_of_keys = [
            'ID', 'Name', 'Size', 'Share Proto', 'Status', 'Is Public',
            'Share Type Name', 'Host', 'Availability Zone'
        ]
        if all_tenants or args.public:
            list_of_keys.append('Project ID')

    empty_obj = type('Empty', (object,), {'id': None})
    share_type = (_find_share_type(cs, args.share_type)
                  if args.share_type else empty_obj)

    snapshot = (_find_share_snapshot(cs, args.snapshot)
                if args.snapshot else empty_obj)

    share_network = (_find_share_network(cs, args.share_network)
                     if args.share_network else empty_obj)

    share_group = None
    if args.share_group:
        share_group = _find_share_group(cs, args.share_group)

    search_opts = {
        'offset': args.offset,
        'limit': args.limit,
        'all_tenants': all_tenants,
        'name': args.name,
        'status': args.status,
        'host': args.host,
        'share_network_id': share_network.id,
        'snapshot_id': snapshot.id,
        'share_type_id': share_type.id,
        'metadata': _extract_metadata(args),
        'extra_specs': _extract_extra_specs(args),
        'share_server_id': args.share_server_id,
        'project_id': args.project_id,
        'is_public': args.public,
    }
    if cs.api_version.matches(api_versions.APIVersion("2.36"),
                              api_versions.APIVersion()):
        search_opts['name~'] = getattr(args, 'name~')
        search_opts['description~'] = getattr(args, 'description~')
        search_opts['description'] = getattr(args, 'description')
    elif (getattr(args, 'name~') or getattr(args, 'description~') or
          getattr(args, 'description')):
        raise exceptions.CommandError(
            "Pattern based filtering (name~, description~ and description)"
            " is only available with manila API version >= 2.36")

    if cs.api_version.matches(api_versions.APIVersion("2.35"),
                              api_versions.APIVersion()):
        search_opts['export_location'] = args.export_location
    elif args.export_location:
        raise exceptions.CommandError(
            "Filtering by export location is only "
            "available with manila API version >= 2.35")

    if (args.count and
            cs.api_version.matches(
                api_versions.APIVersion(), api_versions.APIVersion("2.41"))):
        raise exceptions.CommandError(
            "Display total number of shares is only "
            "available with manila API version >= 2.42")

    if share_group:
        search_opts['share_group_id'] = share_group.id

    total_count = 0
    if strutils.bool_from_string(args.count, strict=True):
        search_opts['with_count'] = args.count
        shares, total_count = cs.shares.list(
            search_opts=search_opts, sort_key=args.sort_key,
            sort_dir=args.sort_dir,
        )
    else:
        shares = cs.shares.list(
            search_opts=search_opts, sort_key=args.sort_key,
            sort_dir=args.sort_dir,
        )
    # NOTE(vponomaryov): usage of 'export_location' and
    # 'export_locations' columns may cause scaling issue using API 2.9+ and
    # when lots of shares are returned.
    if (shares and columns is not None and 'export_location' in columns and
            not hasattr(shares[0], 'export_location')):
        # NOTE(vponomaryov): we will get here only using API 2.9+
        for share in shares:
            els_objs = cs.share_export_locations.list(share)
            els = [el.to_dict()['path'] for el in els_objs]
            setattr(share, 'export_locations', els)
            setattr(share, 'export_location', els[0] if els else None)
    cliutils.print_list(shares, list_of_keys, sortby_index=None)
    if args.count:
        print("Shares in total: %s" % total_count)


@cliutils.arg(
    '--share-id',
    '--share_id',  # alias
    metavar='<share_id>',
    default=None,
    action='single_alias',
    help='Filter results by share ID.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,host,status".')
@cliutils.arg(
    '--export-location', '--export_location',
    metavar='<export_location>',
    type=str,
    default=None,
    action='single_alias',
    help='ID or path of the share instance export location. '
         'Available only for microversion >= 2.35.')
@api_versions.wraps("2.3")
def do_share_instance_list(cs, args):
    """List share instances (Admin only)."""
    share = _find_share(cs, args.share_id) if args.share_id else None

    list_of_keys = [
        'ID', 'Share ID', 'Host', 'Status', 'Availability Zone',
        'Share Network ID', 'Share Server ID', 'Share Type ID',
    ]

    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)

    if share:
        instances = cs.shares.list_instances(share)
    else:
        if cs.api_version.matches(
                api_versions.APIVersion("2.35"), api_versions.APIVersion()):
            instances = cs.share_instances.list(args.export_location)
        else:
            if args.export_location:
                raise exceptions.CommandError(
                    "Filtering by export location is only "
                    "available with manila API version >= 2.35")
            instances = cs.share_instances.list()

    cliutils.print_list(instances, list_of_keys)


@api_versions.wraps("2.3", "2.8")
@cliutils.arg(
    'instance',
    metavar='<instance>',
    help='Name or ID of the share instance.')
def do_share_instance_show(cs, args):
    """Show details about a share instance."""
    instance = _find_share_instance(cs, args.instance)
    _print_share_instance(cs, instance)


@api_versions.wraps("2.9")  # noqa
@cliutils.arg(
    'instance',
    metavar='<instance>',
    help='Name or ID of the share instance.')
def do_share_instance_show(cs, args):
    """Show details about a share instance (Admin only)."""
    instance = _find_share_instance(cs, args.instance)
    export_locations = cs.share_instance_export_locations.list(instance)
    instance._info['export_locations'] = export_locations
    _print_share_instance(cs, instance)


@cliutils.arg(
    'instance',
    metavar='<instance>',
    nargs='+',
    help='Name or ID of the instance(s) to force delete.')
@api_versions.wraps("2.3")
def do_share_instance_force_delete(cs, args):
    """Force-delete the share instance, regardless of state (Admin only)."""
    failure_count = 0
    for instance in args.instance:
        try:
            _find_share_instance(cs, instance).force_delete()
        except Exception as e:
            failure_count += 1
            print("Delete for share instance %s failed: %s" % (instance, e),
                  file=sys.stderr)
    if failure_count == len(args.instance):
        raise exceptions.CommandError("Unable to force delete any of "
                                      "specified share instances.")


@cliutils.arg(
    'instance',
    metavar='<instance>',
    help='Name or ID of the share instance to modify.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default='available',
    help=('Indicate which state to assign the instance. Options include '
          'available, error, creating, deleting, error_deleting, migrating,'
          'migrating_to. If no state is provided, available will be used.'))
@api_versions.wraps("2.3")
def do_share_instance_reset_state(cs, args):
    """Explicitly update the state of a share instance (Admin only)."""
    instance = _find_share_instance(cs, args.instance)
    instance.reset_state(args.state)


@api_versions.wraps("2.9")
@cliutils.arg(
    'instance',
    metavar='<instance>',
    help='Name or ID of the share instance.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,host,status".')
def do_share_instance_export_location_list(cs, args):
    """List export locations of a given share instance."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = [
            'ID',
            'Path',
            'Is Admin only',
            'Preferred',
        ]
    instance = _find_share_instance(cs, args.instance)
    export_locations = cs.share_instance_export_locations.list(instance)
    cliutils.print_list(export_locations, list_of_keys)


@api_versions.wraps("2.9")
@cliutils.arg(
    'instance',
    metavar='<instance>',
    help='Name or ID of the share instance.')
@cliutils.arg(
    'export_location',
    metavar='<export_location>',
    help='ID of the share instance export location.')
def do_share_instance_export_location_show(cs, args):
    """Show export location for the share instance."""
    instance = _find_share_instance(cs, args.instance)
    export_location = cs.share_instance_export_locations.get(
        instance, args.export_location)
    view_data = export_location._info.copy()
    cliutils.print_dict(view_data)


@cliutils.arg(
    '--all-tenants',
    dest='all_tenants',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help='Display information from all tenants (Admin only).')
@cliutils.arg(
    '--name',
    metavar='<name>',
    type=six.text_type,
    default=None,
    help='Filter results by name.')
@cliutils.arg(
    '--description',
    metavar='<description>',
    type=six.text_type,
    default=None,
    help='Filter results by description. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--status',
    metavar='<status>',
    default=None,
    help='Filter results by status.')
@cliutils.arg(
    '--share-id',
    '--share_id',  # alias
    metavar='<share_id>',
    default=None,
    action='single_alias',
    help='Filter results by source share ID.')
@cliutils.arg(
    '--usage',
    dest='usage',
    metavar='any|used|unused',
    nargs='?',
    type=str,
    const='any',
    default=None,
    choices=['any', 'used', 'unused', ],
    help='Either filter or not snapshots by its usage. OPTIONAL: Default=any.')
@cliutils.arg(
    '--limit',
    metavar='<limit>',
    type=int,
    default=None,
    help='Maximum number of share snapshots to return. '
         'OPTIONAL: Default=None.')
@cliutils.arg(
    '--offset',
    metavar='<offset>',
    type=int,
    default=None,
    help='Set offset to define start point of share snapshots listing. '
         'OPTIONAL: Default=None.')
@cliutils.arg(
    '--sort-key',
    '--sort_key',  # alias
    metavar='<sort_key>',
    type=str,
    default=None,
    action='single_alias',
    help='Key to be sorted, available keys are %(keys)s. '
         'Default=None.' % {'keys': constants.SNAPSHOT_SORT_KEY_VALUES})
@cliutils.arg(
    '--sort-dir',
    '--sort_dir',  # alias
    metavar='<sort_dir>',
    type=str,
    default=None,
    action='single_alias',
    help='Sort direction, available values are %(values)s. '
         'OPTIONAL: Default=None.' % {'values': constants.SORT_DIR_VALUES})
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
@cliutils.arg(
    '--name~',
    metavar='<name~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share snapshot name pattern. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--description~',
    metavar='<description~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share snapshot description pattern. '
         'Available only for microversion >= 2.36.')
def do_snapshot_list(cs, args):
    """List all the snapshots."""
    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = [
            'ID', 'Share ID', 'Status', 'Name', 'Share Size',
        ]
        if all_tenants:
            list_of_keys.append('Project ID')

    empty_obj = type('Empty', (object,), {'id': None})
    share = _find_share(cs, args.share_id) if args.share_id else empty_obj
    search_opts = {
        'offset': args.offset,
        'limit': args.limit,
        'all_tenants': all_tenants,
        'name': args.name,
        'status': args.status,
        'share_id': share.id,
        'usage': args.usage,
    }
    if cs.api_version.matches(api_versions.APIVersion("2.36"),
                              api_versions.APIVersion()):
        search_opts['name~'] = getattr(args, 'name~')
        search_opts['description~'] = getattr(args, 'description~')
        search_opts['description'] = getattr(args, 'description')
    elif (getattr(args, 'name~') or getattr(args, 'description~') or
          getattr(args, 'description')):
        raise exceptions.CommandError(
            "Pattern based filtering (name~, description~ and description)"
            " is only available with manila API version >= 2.36")

    snapshots = cs.share_snapshots.list(
        search_opts=search_opts,
        sort_key=args.sort_key,
        sort_dir=args.sort_dir,
    )
    cliutils.print_list(snapshots, list_of_keys, sortby_index=None)


@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the snapshot.')
def do_snapshot_show(cs, args):
    """Show details about a snapshot."""
    snapshot = _find_share_snapshot(cs, args.snapshot)
    export_locations = cs.share_snapshot_export_locations.list(
        snapshot=snapshot)
    snapshot._info['export_locations'] = export_locations
    _print_share_snapshot(cs, snapshot)


@api_versions.wraps("2.32")
@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the snapshot.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,path".')
def do_snapshot_export_location_list(cs, args):
    """List export locations of a given snapshot."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = [
            'ID',
            'Path',
        ]
    snapshot = _find_share_snapshot(cs, args.snapshot)
    export_locations = cs.share_snapshot_export_locations.list(
        snapshot)
    cliutils.print_list(export_locations, list_of_keys)


@api_versions.wraps("2.32")
@cliutils.arg(
    'instance',
    metavar='<instance>',
    help='Name or ID of the snapshot instance.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,path,is_admin_only".')
def do_snapshot_instance_export_location_list(cs, args):
    """List export locations of a given snapshot instance."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = [
            'ID',
            'Path',
            'Is Admin only',
        ]
    instance = _find_share_snapshot_instance(cs, args.instance)
    export_locations = cs.share_snapshot_instance_export_locations.list(
        instance)
    cliutils.print_list(export_locations, list_of_keys)


@api_versions.wraps("2.32")
@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the snapshot.')
@cliutils.arg(
    'export_location',
    metavar='<export_location>',
    help='ID of the share snapshot export location.')
def do_snapshot_export_location_show(cs, args):
    """Show export location of the share snapshot."""
    snapshot = _find_share_snapshot(cs, args.snapshot)
    export_location = cs.share_snapshot_export_locations.get(
        args.export_location, snapshot)
    view_data = export_location._info.copy()
    cliutils.print_dict(view_data)


@api_versions.wraps("2.32")
@cliutils.arg(
    'snapshot_instance',
    metavar='<snapshot_instance>',
    help='ID of the share snapshot instance.')
@cliutils.arg(
    'export_location',
    metavar='<export_location>',
    help='ID of the share snapshot instance export location.')
def do_snapshot_instance_export_location_show(cs, args):
    """Show export location of the share instance snapshot."""
    snapshot_instance = _find_share_snapshot_instance(cs,
                                                      args.snapshot_instance)
    export_location = cs.share_snapshot_instance_export_locations.get(
        args.export_location, snapshot_instance)

    view_data = export_location._info.copy()
    cliutils.print_dict(view_data)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to snapshot.')
@cliutils.arg(
    '--force',
    metavar='<True|False>',
    help='Optional flag to indicate whether '
    'to snapshot a share even if it\'s busy. '
    '(Default=False)',
    default=False)
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help='Optional snapshot name. (Default=None)')
@cliutils.arg(
    '--description',
    metavar='<description>',
    default=None,
    help='Optional snapshot description. (Default=None)')
def do_snapshot_create(cs, args):
    """Add a new snapshot."""
    share = _find_share(cs, args.share)
    snapshot = cs.share_snapshots.create(share,
                                         args.force,
                                         args.name,
                                         args.description)
    _print_share_snapshot(cs, snapshot)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to rename.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help='New name for the share.')
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional share description. (Default=None)',
    default=None)
@cliutils.arg(
    '--is-public',
    '--is_public',  # alias
    metavar='<is_public>',
    default=None,
    type=str,
    action="single_alias",
    help='Public share is visible for all tenants.')
def do_update(cs, args):
    """Rename a share."""
    kwargs = {}

    if args.name is not None:
        kwargs['display_name'] = args.name
    if args.description is not None:
        kwargs['display_description'] = args.description
    if args.is_public is not None:
        kwargs['is_public'] = strutils.bool_from_string(args.is_public,
                                                        strict=True)
    if not kwargs:
        msg = "Must supply name, description or is_public value."
        raise exceptions.CommandError(msg)
    _find_share(cs, args.share).update(**kwargs)


@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the snapshot to rename.')
@cliutils.arg(
    'name',
    nargs='?',
    metavar='<name>',
    help='New name for the snapshot.')
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional snapshot description. (Default=None)',
    default=None)
def do_snapshot_rename(cs, args):
    """Rename a snapshot."""
    kwargs = {}

    if args.name is not None:
        kwargs['display_name'] = args.name
    if args.description is not None:
        kwargs['display_description'] = args.description
    if not kwargs:
        msg = "Must supply either name or description."
        raise exceptions.CommandError(msg)
    _find_share_snapshot(cs, args.snapshot).update(**kwargs)


@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    nargs='+',
    help='Name or ID of the snapshot(s) to delete.')
def do_snapshot_delete(cs, args):
    """Remove one or more snapshots."""
    failure_count = 0

    for snapshot in args.snapshot:
        try:
            snapshot_ref = _find_share_snapshot(
                cs, snapshot)
            cs.share_snapshots.delete(snapshot_ref)
        except Exception as e:
            failure_count += 1
            print("Delete for snapshot %s failed: %s" % (
                snapshot, e), file=sys.stderr)

    if failure_count == len(args.snapshot):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "snapshots.")


@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    nargs='+',
    help='Name or ID of the snapshot(s) to force delete.')
def do_snapshot_force_delete(cs, args):
    """Attempt force-deletion of one or more snapshots.

    Regardless of the state (Admin only).
    """
    failure_count = 0

    for snapshot in args.snapshot:
        try:
            snapshot_ref = _find_share_snapshot(
                cs, snapshot)
            cs.share_snapshots.force_delete(snapshot_ref)
        except Exception as e:
            failure_count += 1
            print("Delete for snapshot %s failed: %s" % (
                snapshot, e), file=sys.stderr)

    if failure_count == len(args.snapshot):
        raise exceptions.CommandError("Unable to force delete any of the "
                                      "specified snapshots.")


@cliutils.arg(
    'snapshot',
    metavar='<snapshot>',
    help='Name or ID of the snapshot to modify.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default='available',
    help=('Indicate which state to assign the snapshot. '
          'Options include available, error, creating, deleting, '
          'error_deleting. If no state is provided, '
          'available will be used.'))
def do_snapshot_reset_state(cs, args):
    """Explicitly update the state of a snapshot (Admin only)."""
    snapshot = _find_share_snapshot(cs, args.snapshot)
    snapshot.reset_state(args.state)


@api_versions.wraps("2.19")
@cliutils.arg(
    '--snapshot',
    metavar='<snapshot>',
    default=None,
    help='Filter results by share snapshot ID.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id".')
@cliutils.arg(
    '--detailed',
    metavar='<detailed>',
    default=False,
    help='Show detailed information about snapshot instances.'
         ' (Default=False)')
def do_snapshot_instance_list(cs, args):
    """List share snapshot instances."""
    snapshot = (_find_share_snapshot(cs, args.snapshot)
                if args.snapshot else None)
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    elif args.detailed:
        list_of_keys = ['ID', 'Snapshot ID', 'Status', 'Created_at',
                        'Updated_at', 'Share_id', 'Share_instance_id',
                        'Progress', 'Provider_location']
    else:
        list_of_keys = ['ID', 'Snapshot ID', 'Status']

    instances = cs.share_snapshot_instances.list(
        detailed=args.detailed, snapshot=snapshot)

    cliutils.print_list(instances, list_of_keys)


@api_versions.wraps("2.19")
@cliutils.arg(
    'snapshot_instance',
    metavar='<snapshot_instance>',
    help='ID of the share snapshot instance.')
def do_snapshot_instance_show(cs, args):
    """Show details about a share snapshot instance."""
    snapshot_instance = _find_share_snapshot_instance(
        cs, args.snapshot_instance)
    export_locations = (
        cs.share_snapshot_instance_export_locations.list(snapshot_instance))
    snapshot_instance._info['export_locations'] = export_locations
    _print_share_snapshot(cs, snapshot_instance)


@cliutils.arg(
    'snapshot_instance',
    metavar='<snapshot_instance>',
    help='ID of the snapshot instance to modify.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default='available',
    help=('Indicate which state to assign the snapshot instance. '
          'Options include available, error, creating, deleting, '
          'error_deleting. If no state is provided, available '
          'will be used.'))
@api_versions.wraps("2.19")
def do_snapshot_instance_reset_state(cs, args):
    """Explicitly update the state of a share snapshot instance."""
    snapshot_instance = _find_share_snapshot_instance(
        cs, args.snapshot_instance)
    snapshot_instance.reset_state(args.state)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to modify.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default='available',
    help=('Indicate which state to assign the share. Options include '
          'available, error, creating, deleting, error_deleting. If no '
          'state is provided, available will be used.'))
def do_reset_state(cs, args):
    """Explicitly update the state of a share (Admin only)."""
    share = _find_share(cs, args.share)
    share.reset_state(args.state)


@api_versions.wraps("1.0", "2.25")
@cliutils.arg(
    '--nova-net-id',
    '--nova-net_id', '--nova_net_id', '--nova_net-id',  # aliases
    metavar='<nova-net-id>',
    default=None,
    action='single_alias',
    help="Nova net ID. Used to set up network for share servers. This "
         "option is deprecated and will be rejected in newer releases "
         "of OpenStack Manila.")
@cliutils.arg(
    '--neutron-net-id',
    '--neutron-net_id', '--neutron_net_id', '--neutron_net-id',
    metavar='<neutron-net-id>',
    default=None,
    action='single_alias',
    help="Neutron network ID. Used to set up network for share servers.")
@cliutils.arg(
    '--neutron-subnet-id',
    '--neutron-subnet_id', '--neutron_subnet_id', '--neutron_subnet-id',
    metavar='<neutron-subnet-id>',
    default=None,
    action='single_alias',
    help="Neutron subnet ID. Used to set up network for share servers. "
         "This subnet should belong to specified neutron network.")
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help="Share network name.")
@cliutils.arg(
    '--description',
    metavar='<description>',
    default=None,
    help="Share network description.")
def do_share_network_create(cs, args):
    """Create description for network used by the tenant."""
    values = {
        'neutron_net_id': args.neutron_net_id,
        'neutron_subnet_id': args.neutron_subnet_id,
        'nova_net_id': args.nova_net_id,
        'name': args.name,
        'description': args.description,
    }
    share_network = cs.share_networks.create(**values)
    info = share_network._info.copy()
    cliutils.print_dict(info)


@api_versions.wraps("2.26")  # noqa
@cliutils.arg(
    '--neutron-net-id',
    '--neutron-net_id', '--neutron_net_id', '--neutron_net-id',
    metavar='<neutron-net-id>',
    default=None,
    action='single_alias',
    help="Neutron network ID. Used to set up network for share servers.")
@cliutils.arg(
    '--neutron-subnet-id',
    '--neutron-subnet_id', '--neutron_subnet_id', '--neutron_subnet-id',
    metavar='<neutron-subnet-id>',
    default=None,
    action='single_alias',
    help="Neutron subnet ID. Used to set up network for share servers. "
         "This subnet should belong to specified neutron network.")
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help="Share network name.")
@cliutils.arg(
    '--description',
    metavar='<description>',
    default=None,
    help="Share network description.")
def do_share_network_create(cs, args):
    """Create description for network used by the tenant."""
    values = {
        'neutron_net_id': args.neutron_net_id,
        'neutron_subnet_id': args.neutron_subnet_id,
        'name': args.name,
        'description': args.description,
    }
    share_network = cs.share_networks.create(**values)
    info = share_network._info.copy()
    cliutils.print_dict(info)


@api_versions.wraps("1.0", "2.25")
@cliutils.arg(
    'share_network',
    metavar='<share-network>',
    help='Name or ID of share network to update.')
@cliutils.arg(
    '--nova-net-id',
    '--nova-net_id', '--nova_net_id', '--nova_net-id',  # aliases
    metavar='<nova-net-id>',
    default=None,
    action='single_alias',
    help="Nova net ID. Used to set up network for share servers. This "
         "option is deprecated and will be rejected in newer releases "
         "of OpenStack Manila.")
@cliutils.arg(
    '--neutron-net-id',
    '--neutron-net_id', '--neutron_net_id', '--neutron_net-id',
    metavar='<neutron-net-id>',
    default=None,
    action='single_alias',
    help="Neutron network ID. Used to set up network for share servers.")
@cliutils.arg(
    '--neutron-subnet-id',
    '--neutron-subnet_id', '--neutron_subnet_id', '--neutron_subnet-id',
    metavar='<neutron-subnet-id>',
    default=None,
    action='single_alias',
    help="Neutron subnet ID. Used to set up network for share servers. "
         "This subnet should belong to specified neutron network.")
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help="Share network name.")
@cliutils.arg(
    '--description',
    metavar='<description>',
    default=None,
    help="Share network description.")
def do_share_network_update(cs, args):
    """Update share network data."""
    values = {
        'neutron_net_id': args.neutron_net_id,
        'neutron_subnet_id': args.neutron_subnet_id,
        'nova_net_id': args.nova_net_id,
        'name': args.name,
        'description': args.description,
    }
    share_network = _find_share_network(
        cs, args.share_network).update(**values)
    info = share_network._info.copy()
    cliutils.print_dict(info)


@api_versions.wraps("2.26")  # noqa
@cliutils.arg(
    'share_network',
    metavar='<share-network>',
    help='Name or ID of share network to update.')
@cliutils.arg(
    '--neutron-net-id',
    '--neutron-net_id', '--neutron_net_id', '--neutron_net-id',
    metavar='<neutron-net-id>',
    default=None,
    action='single_alias',
    help="Neutron network ID. Used to set up network for share servers. This "
         "option is deprecated and will be rejected in newer releases of "
         "OpenStack Manila.")
@cliutils.arg(
    '--neutron-subnet-id',
    '--neutron-subnet_id', '--neutron_subnet_id', '--neutron_subnet-id',
    metavar='<neutron-subnet-id>',
    default=None,
    action='single_alias',
    help="Neutron subnet ID. Used to set up network for share servers. "
         "This subnet should belong to specified neutron network.")
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help="Share network name.")
@cliutils.arg(
    '--description',
    metavar='<description>',
    default=None,
    help="Share network description.")
def do_share_network_update(cs, args):
    """Update share network data."""
    values = {
        'neutron_net_id': args.neutron_net_id,
        'neutron_subnet_id': args.neutron_subnet_id,
        'name': args.name,
        'description': args.description,
    }
    share_network = _find_share_network(
        cs, args.share_network).update(**values)
    info = share_network._info.copy()
    cliutils.print_dict(info)


@cliutils.arg(
    'share_network',
    metavar='<share-network>',
    help='Name or ID of the share network to show.')
def do_share_network_show(cs, args):
    """Get a description for network used by the tenant."""
    share_network = _find_share_network(cs, args.share_network)
    info = share_network._info.copy()
    cliutils.print_dict(info)


@api_versions.wraps("1.0", "2.25")
@cliutils.arg(
    '--all-tenants',
    dest='all_tenants',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help='Display information from all tenants (Admin only).')
@cliutils.arg(
    '--project-id',
    '--project_id',  # alias
    metavar='<project_id>',
    action='single_alias',
    default=None,
    help='Filter results by project ID.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help='Filter results by name.')
@cliutils.arg(
    '--created-since',
    '--created_since',  # alias
    metavar='<created_since>',
    action='single_alias',
    default=None,
    help='''Return only share networks created since given date. '''
         '''The date is in the format 'yyyy-mm-dd'.''')
@cliutils.arg(
    '--created-before',
    '--created_before',  # alias
    metavar='<created_before>',
    action='single_alias',
    default=None,
    help='''Return only share networks created until given date. '''
         '''The date is in the format 'yyyy-mm-dd'.''')
@cliutils.arg(
    '--security-service',
    '--security_service',  # alias
    metavar='<security_service>',
    action='single_alias',
    default=None,
    help='Filter results by attached security service.')
@cliutils.arg(
    '--nova-net-id',
    '--nova_net_id', '--nova_net-id', '--nova-net_id',  # aliases
    metavar='<nova_net_id>',
    action='single_alias',
    default=None,
    help='Filter results by Nova net ID. This option is deprecated and will '
         'be rejected in newer releases of OpenStack Manila.')
@cliutils.arg(
    '--neutron-net-id',
    '--neutron_net_id', '--neutron_net-id', '--neutron-net_id',  # aliases
    metavar='<neutron_net_id>',
    action='single_alias',
    default=None,
    help='Filter results by neutron net ID.')
@cliutils.arg(
    '--neutron-subnet-id',
    '--neutron_subnet_id', '--neutron-subnet_id',  # aliases
    '--neutron_subnet-id',  # alias
    metavar='<neutron_subnet_id>',
    action='single_alias',
    default=None,
    help='Filter results by neutron subnet ID.')
@cliutils.arg(
    '--network-type',
    '--network_type',  # alias
    metavar='<network_type>',
    action='single_alias',
    default=None,
    help='Filter results by network type.')
@cliutils.arg(
    '--segmentation-id',
    '--segmentation_id',  # alias
    metavar='<segmentation_id>',
    type=int,
    action='single_alias',
    default=None,
    help='Filter results by segmentation ID.')
@cliutils.arg(
    '--cidr',
    metavar='<cidr>',
    default=None,
    help='Filter results by CIDR.')
@cliutils.arg(
    '--ip-version',
    '--ip_version',  # alias
    metavar='<ip_version>',
    type=int,
    action='single_alias',
    default=None,
    help='Filter results by IP version.')
@cliutils.arg(
    '--offset',
    metavar='<offset>',
    type=int,
    default=None,
    help='Start position of share networks listing.')
@cliutils.arg(
    '--limit',
    metavar='<limit>',
    type=int,
    default=None,
    help='Number of share networks to return per request.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id".')
def do_share_network_list(cs, args):
    """Get a list of network info."""
    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'project_id': args.project_id,
        'name': args.name,
        'created_since': args.created_since,
        'created_before': args.created_before,
        'nova_net_id': args.nova_net_id,
        'neutron_net_id': args.neutron_net_id,
        'neutron_subnet_id': args.neutron_subnet_id,
        'network_type': args.network_type,
        'segmentation_id': args.segmentation_id,
        'cidr': args.cidr,
        'ip_version': args.ip_version,
        'offset': args.offset,
        'limit': args.limit,
    }
    if args.security_service:
        search_opts['security_service_id'] = _find_security_service(
            cs, args.security_service).id
    share_networks = cs.share_networks.list(search_opts=search_opts)
    fields = ['id', 'name']

    if args.columns is not None:
        fields = _split_columns(columns=args.columns)

    cliutils.print_list(share_networks, fields=fields)


@api_versions.wraps("2.26")  # noqa
@cliutils.arg(
    '--all-tenants',
    dest='all_tenants',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help='Display information from all tenants (Admin only).')
@cliutils.arg(
    '--project-id',
    '--project_id',  # alias
    metavar='<project_id>',
    action='single_alias',
    default=None,
    help='Filter results by project ID.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    type=six.text_type,
    default=None,
    help='Filter results by name.')
@cliutils.arg(
    '--description',
    metavar='<description>',
    type=six.text_type,
    default=None,
    help='Filter results by description. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--created-since',
    '--created_since',  # alias
    metavar='<created_since>',
    action='single_alias',
    default=None,
    help='''Return only share networks created since given date. '''
         '''The date is in the format 'yyyy-mm-dd'.''')
@cliutils.arg(
    '--created-before',
    '--created_before',  # alias
    metavar='<created_before>',
    action='single_alias',
    default=None,
    help='''Return only share networks created until given date. '''
         '''The date is in the format 'yyyy-mm-dd'.''')
@cliutils.arg(
    '--security-service',
    '--security_service',  # alias
    metavar='<security_service>',
    action='single_alias',
    default=None,
    help='Filter results by attached security service.')
@cliutils.arg(
    '--neutron-net-id',
    '--neutron_net_id', '--neutron_net-id', '--neutron-net_id',  # aliases
    metavar='<neutron_net_id>',
    action='single_alias',
    default=None,
    help='Filter results by neutron net ID.')
@cliutils.arg(
    '--neutron-subnet-id',
    '--neutron_subnet_id', '--neutron-subnet_id',  # aliases
    '--neutron_subnet-id',  # alias
    metavar='<neutron_subnet_id>',
    action='single_alias',
    default=None,
    help='Filter results by neutron subnet ID.')
@cliutils.arg(
    '--network-type',
    '--network_type',  # alias
    metavar='<network_type>',
    action='single_alias',
    default=None,
    help='Filter results by network type.')
@cliutils.arg(
    '--segmentation-id',
    '--segmentation_id',  # alias
    metavar='<segmentation_id>',
    type=int,
    action='single_alias',
    default=None,
    help='Filter results by segmentation ID.')
@cliutils.arg(
    '--cidr',
    metavar='<cidr>',
    default=None,
    help='Filter results by CIDR.')
@cliutils.arg(
    '--ip-version',
    '--ip_version',  # alias
    metavar='<ip_version>',
    type=int,
    action='single_alias',
    default=None,
    help='Filter results by IP version.')
@cliutils.arg(
    '--offset',
    metavar='<offset>',
    type=int,
    default=None,
    help='Start position of share networks listing.')
@cliutils.arg(
    '--limit',
    metavar='<limit>',
    type=int,
    default=None,
    help='Number of share networks to return per request.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id".')
@cliutils.arg(
    '--name~',
    metavar='<name~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share network name pattern. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--description~',
    metavar='<description~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share network description pattern. '
         'Available only for microversion >= 2.36.')
def do_share_network_list(cs, args):
    """Get a list of network info."""
    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'project_id': args.project_id,
        'name': args.name,
        'created_since': args.created_since,
        'created_before': args.created_before,
        'neutron_net_id': args.neutron_net_id,
        'neutron_subnet_id': args.neutron_subnet_id,
        'network_type': args.network_type,
        'segmentation_id': args.segmentation_id,
        'cidr': args.cidr,
        'ip_version': args.ip_version,
        'offset': args.offset,
        'limit': args.limit,
    }
    if cs.api_version.matches(api_versions.APIVersion("2.36"),
                              api_versions.APIVersion()):
        search_opts['name~'] = getattr(args, 'name~')
        search_opts['description~'] = getattr(args, 'description~')
        search_opts['description'] = getattr(args, 'description')
    elif (getattr(args, 'name~') or getattr(args, 'description~') or
          getattr(args, 'description')):
        raise exceptions.CommandError(
            "Pattern based filtering (name~, description~ and description)"
            " is only available with manila API version >= 2.36")

    if args.security_service:
        search_opts['security_service_id'] = _find_security_service(
            cs, args.security_service).id
    share_networks = cs.share_networks.list(search_opts=search_opts)
    fields = ['id', 'name']

    if args.columns is not None:
        fields = _split_columns(columns=args.columns)

    cliutils.print_list(share_networks, fields=fields)


@cliutils.arg(
    'share_network',
    metavar='<share-network>',
    help='Share network name or ID.')
@cliutils.arg(
    'security_service',
    metavar='<security-service>',
    help='Security service name or ID to associate with.')
def do_share_network_security_service_add(cs, args):
    """Associate security service with share network."""
    share_network = _find_share_network(cs, args.share_network)
    security_service = _find_security_service(cs, args.security_service)
    cs.share_networks.add_security_service(share_network, security_service)


@cliutils.arg(
    'share_network',
    metavar='<share-network>',
    help='Share network name or ID.')
@cliutils.arg(
    'security_service',
    metavar='<security-service>',
    help='Security service name or ID to dissociate.')
def do_share_network_security_service_remove(cs, args):
    """Dissociate security service from share network."""
    share_network = _find_share_network(cs, args.share_network)
    security_service = _find_security_service(cs, args.security_service)
    cs.share_networks.remove_security_service(share_network, security_service)


@cliutils.arg(
    'share_network',
    metavar='<share-network>',
    help='Share network name or ID.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
def do_share_network_security_service_list(cs, args):
    """Get list of security services associated with a given share network."""
    share_network = _find_share_network(cs, args.share_network)
    search_opts = {
        'share_network_id': share_network.id,
    }
    security_services = cs.security_services.list(search_opts=search_opts)
    fields = ['id', 'name', 'status', 'type', ]

    if args.columns is not None:
        fields = _split_columns(columns=args.columns)

    cliutils.print_list(security_services, fields=fields)


@cliutils.arg(
    'share_network',
    metavar='<share-network>',
    nargs='+',
    help='Name or ID of share network(s) to be deleted.')
def do_share_network_delete(cs, args):
    """Delete one or more share networks."""
    failure_count = 0

    for share_network in args.share_network:
        try:
            share_ref = _find_share_network(
                cs, share_network)
            cs.share_networks.delete(share_ref)
        except Exception as e:
            failure_count += 1
            print("Delete for share network %s failed: %s" % (
                share_network, e), file=sys.stderr)

    if failure_count == len(args.share_network):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "share networks.")


@cliutils.arg(
    'type',
    metavar='<type>',
    help="Security service type: 'ldap', 'kerberos' or 'active_directory'.")
@cliutils.arg(
    '--dns-ip',
    metavar='<dns_ip>',
    default=None,
    help="DNS IP address used inside tenant's network.")
@cliutils.arg(
    '--ou',
    metavar='<ou>',
    default=None,
    help="Security service OU (Organizational Unit). Available only for "
         "microversion >= 2.44.")
@cliutils.arg(
    '--server',
    metavar='<server>',
    default=None,
    help="Security service IP address or hostname.")
@cliutils.arg(
    '--domain',
    metavar='<domain>',
    default=None,
    help="Security service domain.")
@cliutils.arg(
    '--user',
    metavar='<user>',
    default=None,
    help="Security service user or group used by tenant.")
@cliutils.arg(
    '--password',
    metavar='<password>',
    default=None,
    help="Password used by user.")
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help="Security service name.")
@cliutils.arg(
    '--description',
    metavar='<description>',
    default=None,
    help="Security service description.")
def do_security_service_create(cs, args):
    """Create security service used by tenant."""
    values = {
        'dns_ip': args.dns_ip,
        'server': args.server,
        'domain': args.domain,
        'user': args.user,
        'password': args.password,
        'name': args.name,
        'description': args.description,
    }

    if cs.api_version.matches(api_versions.APIVersion("2.44"),
                              api_versions.APIVersion()):
        values['ou'] = args.ou
    elif args.ou:
        raise exceptions.CommandError(
            "Security service Organizational Unit (ou) option "
            "is only available with manila API version >= 2.44")

    security_service = cs.security_services.create(args.type, **values)
    info = security_service._info.copy()
    cliutils.print_dict(info)


@cliutils.arg(
    'security_service',
    metavar='<security-service>',
    help='Security service name or ID to update.')
@cliutils.arg(
    '--dns-ip',
    metavar='<dns-ip>',
    default=None,
    help="DNS IP address used inside tenant's network.")
@cliutils.arg(
    '--ou',
    metavar='<ou>',
    default=None,
    help="Security service OU (Organizational Unit). Available only for "
         "microversion >= 2.44.")
@cliutils.arg(
    '--server',
    metavar='<server>',
    default=None,
    help="Security service IP address or hostname.")
@cliutils.arg(
    '--domain',
    metavar='<domain>',
    default=None,
    help="Security service domain.")
@cliutils.arg(
    '--user',
    metavar='<user>',
    default=None,
    help="Security service user or group used by tenant.")
@cliutils.arg(
    '--password',
    metavar='<password>',
    default=None,
    help="Password used by user.")
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help="Security service name.")
@cliutils.arg(
    '--description',
    metavar='<description>',
    default=None,
    help="Security service description.")
def do_security_service_update(cs, args):
    """Update security service."""
    values = {
        'dns_ip': args.dns_ip,
        'server': args.server,
        'domain': args.domain,
        'user': args.user,
        'password': args.password,
        'name': args.name,
        'description': args.description,
    }

    if cs.api_version.matches(api_versions.APIVersion("2.44"),
                              api_versions.APIVersion()):
        values['ou'] = args.ou
    elif args.ou:
        raise exceptions.CommandError(
            "Security service Organizational Unit (ou) option "
            "is only available with manila API version >= 2.44")

    security_service = _find_security_service(
        cs, args.security_service).update(**values)
    cliutils.print_dict(security_service._info)


@cliutils.arg(
    'security_service',
    metavar='<security-service>',
    help='Security service name or ID to show.')
def do_security_service_show(cs, args):
    """Show security service."""
    security_service = _find_security_service(cs, args.security_service)
    info = security_service._info.copy()
    cliutils.print_dict(info)


@cliutils.arg(
    '--all-tenants',
    dest='all_tenants',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help='Display information from all tenants (Admin only).')
@cliutils.arg(
    '--share-network',
    '--share_network',  # alias
    metavar='<share_network>',
    action='single_alias',
    default=None,
    help='Filter results by share network id or name.')
@cliutils.arg(
    '--status',
    metavar='<status>',
    default=None,
    help='Filter results by status.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help='Filter results by name.')
@cliutils.arg(
    '--type',
    metavar='<type>',
    default=None,
    help='Filter results by type.')
@cliutils.arg(
    '--user',
    metavar='<user>',
    default=None,
    help='Filter results by user or group used by tenant.')
@cliutils.arg(
    '--dns-ip',
    '--dns_ip',  # alias
    metavar='<dns_ip>',
    action='single_alias',
    default=None,
    help="Filter results by DNS IP address used inside tenant's network.")
@cliutils.arg(
    '--ou',
    metavar='<ou>',
    default=None,
    help="Filter results by security service OU (Organizational Unit)."
         " Available only for microversion >= 2.44.")
@cliutils.arg(
    '--server',
    metavar='<server>',
    default=None,
    help="Filter results by security service IP address or hostname.")
@cliutils.arg(
    '--domain',
    metavar='<domain>',
    default=None,
    help="Filter results by domain.")
@cliutils.arg(
    '--detailed',
    dest='detailed',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help="Show detailed information about filtered security services.")
@cliutils.arg(
    '--offset',
    metavar="<offset>",
    default=None,
    help='Start position of security services listing.')
@cliutils.arg(
    '--limit',
    metavar="<limit>",
    default=None,
    help='Number of security services to return per request.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "name,type".')
def do_security_service_list(cs, args):
    """Get a list of security services."""
    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'status': args.status,
        'name': args.name,
        'type': args.type,
        'user': args.user,
        'dns_ip': args.dns_ip,
        'server': args.server,
        'domain': args.domain,
        'offset': args.offset,
        'limit': args.limit,
    }

    if cs.api_version.matches(api_versions.APIVersion("2.44"),
                              api_versions.APIVersion()):
        search_opts['ou'] = args.ou
    elif args.ou:
        raise exceptions.CommandError(
            "Security service Organizational Unit (ou) option "
            "is only available with manila API version >= 2.44")

    if args.share_network:
        search_opts['share_network_id'] = _find_share_network(
            cs, args.share_network).id
    security_services = cs.security_services.list(search_opts=search_opts,
                                                  detailed=args.detailed)
    fields = ['id', 'name', 'status', 'type', ]
    if args.columns is not None:
        fields = _split_columns(columns=args.columns)

    if args.detailed:
        fields.append('share_networks')
    cliutils.print_list(security_services, fields=fields)


@cliutils.arg(
    'security_service',
    metavar='<security-service>',
    nargs='+',
    help='Name or ID of the security service(s) to delete.')
def do_security_service_delete(cs, args):
    """Delete one or more security services."""
    failure_count = 0

    for security_service in args.security_service:
        try:
            security_ref = _find_security_service(
                cs, security_service)
            cs.security_services.delete(security_ref)
        except Exception as e:
            failure_count += 1
            print("Delete for security service %s failed: %s" % (
                security_service, e), file=sys.stderr)

    if failure_count == len(args.security_service):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "security services.")


@cliutils.arg(
    '--host',
    metavar='<hostname>',
    default=None,
    help='Filter results by name of host.')
@cliutils.arg(
    '--status',
    metavar='<status>',
    default=None,
    help='Filter results by status.')
@cliutils.arg(
    '--share-network',
    metavar='<share_network>',
    default=None,
    help='Filter results by share network.')
@cliutils.arg(
    '--project-id',
    metavar='<project_id>',
    default=None,
    help='Filter results by project ID.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,host,status".')
def do_share_server_list(cs, args):
    """List all share servers (Admin only)."""
    search_opts = {
        "host": args.host,
        "share_network": args.share_network,
        "status": args.status,
        "project_id": args.project_id,
    }
    fields = [
        "Id",
        "Host",
        "Status",
        "Share Network",
        "Project Id",
        "Updated_at",
    ]

    if args.columns is not None:
        fields = _split_columns(columns=args.columns)

    share_servers = cs.share_servers.list(search_opts=search_opts)
    cliutils.print_list(share_servers, fields=fields)


@cliutils.arg(
    'id',
    metavar='<id>',
    type=str,
    help='ID of share server.')
def do_share_server_show(cs, args):
    """Show share server info (Admin only)."""
    share_server = cs.share_servers.get(args.id)
    # All 'backend_details' data already present as separated strings,
    # so remove big dict from view.
    if "backend_details" in share_server._info:
        del share_server._info["backend_details"]
    cliutils.print_dict(share_server._info)


@cliutils.arg(
    'id',
    metavar='<id>',
    type=str,
    help='ID of share server.')
def do_share_server_details(cs, args):
    """Show share server details (Admin only)."""
    details = cs.share_servers.details(args.id)
    cliutils.print_dict(details._info)


@cliutils.arg(
    'id',
    metavar='<id>',
    nargs='+',
    type=str,
    help='ID of the share server(s) to delete.')
def do_share_server_delete(cs, args):
    """Delete one or more share servers (Admin only)."""

    failure_count = 0

    for server_id in args.id:
        try:
            id_ref = _find_share_server(cs, server_id)
            cs.share_servers.delete(id_ref)
        except Exception as e:
            failure_count += 1
            print("Delete for share server %s failed: %s" % (
                server_id, e), file=sys.stderr)

    if failure_count == len(args.id):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "share servers.")


@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
def do_availability_zone_list(cs, args):
    """List all availability zones."""

    if args.columns is not None:
        fields = _split_columns(columns=args.columns)
    else:
        fields = ("Id", "Name", "Created_At", "Updated_At")

    availability_zones = cs.availability_zones.list()
    cliutils.print_list(availability_zones, fields=fields)


@cliutils.arg(
    '--host',
    metavar='<hostname>',
    default=None,
    help='Name of host.')
@cliutils.arg(
    '--binary',
    metavar='<binary>',
    default=None,
    help='Service binary.')
@cliutils.arg(
    '--status',
    metavar='<status>',
    default=None,
    help='Filter results by status.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default=None,
    help='Filter results by state.')
@cliutils.arg(
    '--zone',
    metavar='<zone>',
    default=None,
    help='Availability zone.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,host".')
def do_service_list(cs, args):
    """List all services (Admin only)."""
    search_opts = {
        'status': args.status,
        'host': args.host,
        'binary': args.binary,
        'zone': args.zone,
        'state': args.state,
    }
    fields = ["Id", "Binary", "Host", "Zone", "Status", "State", "Updated_at"]

    if args.columns is not None:
        fields = _split_columns(columns=args.columns)

    services = cs.services.list(search_opts=search_opts)
    cliutils.print_list(services, fields=fields)


@cliutils.arg(
    'host',
    metavar='<hostname>',
    help="Host name as 'example_host@example_backend'.")
@cliutils.arg(
    'binary',
    metavar='<binary>',
    help="Service binary, could be 'manila-share' or 'manila-scheduler'.")
def do_service_enable(cs, args):
    """Enables 'manila-share' or 'manila-scheduler' services (Admin only)."""
    columns = ("Host", "Binary", "Enabled")
    result = cs.services.enable(args.host, args.binary)
    result.enabled = not result.disabled
    cliutils.print_list([result], columns)


@cliutils.arg(
    'host',
    metavar='<hostname>',
    help="Host name as 'example_host@example_backend'.")
@cliutils.arg(
    'binary',
    metavar='<binary>',
    help="Service binary, could be 'manila-share' or 'manila-scheduler'.")
def do_service_disable(cs, args):
    """Disables 'manila-share' or 'manila-scheduler' services (Admin only)."""
    columns = ("Host", "Binary", "Enabled")
    result = cs.services.disable(args.host, args.binary)
    result.enabled = not result.disabled
    cliutils.print_list([result], columns)


def _print_dict(data_dict):
    formatted_data = []

    for date in data_dict:
        formatted_data.append("%s : %s" % (date, data_dict[date]))

    return "\n".join(formatted_data)


@cliutils.arg(
    '--host',
    metavar='<host>',
    type=str,
    default='.*',
    help='Filter results by host name.  Regular expressions are supported.')
@cliutils.arg(
    '--backend',
    metavar='<backend>',
    type=str,
    default='.*',
    help='Filter results by backend name.  Regular expressions are supported.')
@cliutils.arg(
    '--pool',
    metavar='<pool>',
    type=str,
    default='.*',
    help='Filter results by pool name.  Regular expressions are supported.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "name,host".')
@cliutils.arg(
    '--detail', '--detailed',
    action='store_true',
    help='Show detailed information about pools. If this parameter is set '
         'to True, --columns parameter will be ignored if present. '
         '(Default=False)')
@cliutils.arg(
    '--share-type', '--share_type',
    '--share-type-id', '--share_type_id',
    metavar='<share_type>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by share type name or ID. (Default=None)'
         'Available only for microversion >= 2.23.')
def do_pool_list(cs, args):
    """List all backend storage pools known to the scheduler (Admin only)."""

    search_opts = {
        'host': args.host,
        'backend': args.backend,
        'pool': args.pool,
        'share_type': args.share_type,
    }

    if args.detail:
        fields = ["Name", "Host", "Backend", "Pool", "Capabilities"]
    else:
        fields = ["Name", "Host", "Backend", "Pool"]

    pools = cs.pools.list(detailed=args.detail, search_opts=search_opts)
    if args.columns is not None:
        fields = _split_columns(columns=args.columns)
        pools = cs.pools.list(detailed=True, search_opts=search_opts)

    if args.detail:
        for info in pools:
            backend = dict()
            backend['name'] = info.name
            backend.update(info.capabilities)
            cliutils.print_dict(backend)
    else:
        cliutils.print_list(pools, fields=fields)


@cliutils.arg('share', metavar='<share>',
              help='Name or ID of share to extend.')
@cliutils.arg('new_size',
              metavar='<new_size>',
              type=int,
              help='New size of share, in GiBs.')
def do_extend(cs, args):
    """Increases the size of an existing share."""
    share = _find_share(cs, args.share)
    cs.shares.extend(share, args.new_size)


@cliutils.arg('share', metavar='<share>',
              help='Name or ID of share to shrink.')
@cliutils.arg('new_size',
              metavar='<new_size>',
              type=int,
              help='New size of share, in GiBs.')
def do_shrink(cs, args):
    """Decreases the size of an existing share."""
    share = _find_share(cs, args.share)
    cs.shares.shrink(share, args.new_size)


##############################################################################
#
# Share types
#
##############################################################################


def _print_type_extra_specs(share_type):
    """Prints share type extra specs or share group type specs."""
    try:
        return _print_dict(share_type.get_keys())
    except exceptions.NotFound:
        return None


def _print_type_required_extra_specs(share_type):
    try:
        return _print_dict(share_type.get_required_keys())
    except exceptions.NotFound:
        return "N/A"


def _print_type_optional_extra_specs(share_type):
    try:
        return _print_dict(share_type.get_optional_keys())
    except exceptions.NotFound:
        return "N/A"


def _is_share_type_public(share_type):
    return 'public' if share_type.is_public else 'private'


def _print_share_type_list(stypes, default_share_type=None, columns=None,
                           description=False):

    def _is_default(share_type):
        if hasattr(share_type, 'is_default'):
            return 'YES' if share_type.is_default else '-'
        elif default_share_type:
            default = default_share_type.id
            return 'YES' if share_type.id == default else '-'
        else:
            return '-'

    formatters = {
        'visibility': _is_share_type_public,
        'is_default': _is_default,
        'required_extra_specs': _print_type_required_extra_specs,
        'optional_extra_specs': _print_type_optional_extra_specs,
    }

    for stype in stypes:
        stype = stype.to_dict()
        stype['visibility'] = stype.pop('is_public', 'unknown')

    fields = [
        'ID',
        'Name',
        'visibility',
        'is_default',
        'required_extra_specs',
        'optional_extra_specs',
    ]
    if description:
        fields.append('Description')
    if columns is not None:
        fields = _split_columns(columns=columns, title=False)

    cliutils.print_list(stypes, fields, formatters)


def _print_share_type(stype, default_share_type=None, show_des=False):

    def _is_default(share_type):
        if hasattr(share_type, 'is_default'):
            return 'YES' if share_type.is_default else '-'
        return '-'

    stype_dict = {
        'ID': stype.id,
        'Name': stype.name,
        'Visibility': _is_share_type_public(stype),
        'is_default': _is_default(stype),
        'required_extra_specs': _print_type_required_extra_specs(stype),
        'optional_extra_specs': _print_type_optional_extra_specs(stype),
    }
    if show_des:
        stype_dict['Description'] = stype.description
    cliutils.print_dict(stype_dict)


def _print_type_and_extra_specs_list(stypes, columns=None):
    """Prints extra specs for a list of share types or share group types."""
    formatters = {
        'all_extra_specs': _print_type_extra_specs,
    }
    fields = ['ID', 'Name', 'all_extra_specs']

    if columns is not None:
        fields = _split_columns(columns=columns, title=False)

    cliutils.print_list(stypes, fields, formatters)


def _find_share_type(cs, stype):
    """Get a share type by name or ID."""
    return apiclient_utils.find_resource(cs.share_types, stype)


@cliutils.arg(
    '--all',
    dest='all',
    action='store_true',
    default=False,
    help='Display all share types whatever public or private '
         'OPTIONAL: Default=False. (Admin only).')
@cliutils.arg(
    '--extra-specs',
    '--extra_specs',
    type=str,
    nargs='*',
    metavar='<key=value>',
    action='single_alias',
    default=None,
    help='Filters results by a extra specs key and value of share type that '
         'was used for share creation. Available only for microversion >= '
         '2.43. OPTIONAL: Default=None.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
def do_type_list(cs, args):
    """Print a list of available 'share types'."""
    search_opts = None
    show_all = args.all
    extra_specs = _extract_extra_specs(args)
    if extra_specs:
        if cs.api_version < api_versions.APIVersion("2.43"):
            raise exceptions.CommandError(
                "Filter by 'extra_specs' is available only starting with "
                "'2.43' API microversion.")
        search_opts = {
            'extra_specs': extra_specs
        }

    share_types = cs.share_types.list(show_all=show_all,
                                      search_opts=search_opts)
    default = None
    if share_types and not hasattr(share_types[0], 'is_default'):
        if ((args.columns and 'is_default' in args.columns) or
                args.columns is None):
            default = cs.share_types.get()

    show_des = cs.api_version.matches(
        api_versions.APIVersion("2.41"), api_versions.APIVersion())
    _print_share_type_list(share_types, default_share_type=default,
                           columns=args.columns, description=show_des)


@cliutils.arg(
    'share_type',
    metavar='<share_type>',
    help='Name or ID of the share type.')
def do_type_show(cs, args):
    """Show share type details."""
    share_type = _find_share_type(cs, args.share_type)
    default = None
    if (share_type and not hasattr(share_type, 'is_default')):
        default = cs.share_types.get()
    _print_type_show(share_type, default_share_type=default)


@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
def do_extra_specs_list(cs, args):
    """Print a list of current 'share types and extra specs' (Admin Only)."""
    stypes = cs.share_types.list()
    _print_type_and_extra_specs_list(stypes, columns=args.columns)


@cliutils.arg(
    'name',
    metavar='<name>',
    help="Name of the new share type.")
@cliutils.arg(
    'spec_driver_handles_share_servers',
    metavar='<spec_driver_handles_share_servers>',
    type=str,
    help="Required extra specification. "
         "Valid values are 'true'/'1' and 'false'/'0'.")
@cliutils.arg(
    '--description',
    metavar='<description>',
    type=str,
    default=None,
    help='Filter results by description. '
         'Available only for microversion >= 2.41.')
@cliutils.arg(
    '--snapshot_support',
    '--snapshot-support',
    metavar='<snapshot_support>',
    action='single_alias',
    help="Boolean extra spec used for filtering of back ends by their "
         "capability to create share snapshots.")
@cliutils.arg(
    '--create_share_from_snapshot_support',
    '--create-share-from-snapshot-support',
    metavar='<create_share_from_snapshot_support>',
    action='single_alias',
    help="Boolean extra spec used for filtering of back ends by their "
         "capability to create shares from snapshots.")
@cliutils.arg(
    '--revert_to_snapshot_support',
    '--revert-to-snapshot-support',
    metavar='<revert_to_snapshot_support>',
    action='single_alias',
    help="Boolean extra spec used for filtering of back ends by their "
         "capability to revert shares to snapshots. (Default is False).")
@cliutils.arg(
    '--mount_snapshot_support',
    '--mount-snapshot-support',
    metavar='<mount_snapshot_support>',
    action='single_alias',
    help="Boolean extra spec used for filtering of back ends by their "
         "capability to mount share snapshots. (Default is False).")
@cliutils.arg(
    '--extra-specs',
    '--extra_specs',  # alias
    type=str,
    nargs='*',
    metavar='<key=value>',
    action='single_alias',
    help="Extra specs key and value of share type that will be"
         " used for share type creation. OPTIONAL: Default=None."
         " example --extra-specs  thin_provisioning='<is> True', "
         "replication_type=readable.",
    default=None)
@cliutils.arg(
    '--is_public',
    '--is-public',
    metavar='<is_public>',
    action='single_alias',
    help="Make type accessible to the public (default true).")
def do_type_create(cs, args):
    """Create a new share type (Admin only)."""
    kwargs = {
        "name": args.name,
        "is_public": strutils.bool_from_string(args.is_public, default=True),
    }
    try:
        kwargs['spec_driver_handles_share_servers'] = (
            strutils.bool_from_string(
                args.spec_driver_handles_share_servers, strict=True))
    except ValueError as e:
        msg = ("Argument spec_driver_handles_share_servers "
               "argument is not valid: %s" % six.text_type(e))
        raise exceptions.CommandError(msg)

    kwargs['extra_specs'] = _extract_extra_specs(args)

    if 'driver_handles_share_servers' in kwargs['extra_specs']:
        msg = ("Argument 'driver_handles_share_servers' is already "
               "set via positional argument.")
        raise exceptions.CommandError(msg)

    show_des = False
    if cs.api_version.matches(api_versions.APIVersion("2.41"),
                              api_versions.APIVersion()):
        show_des = True
        kwargs['description'] = getattr(args, 'description')
    elif getattr(args, 'description'):
        raise exceptions.CommandError(
            "Pattern based option (description)"
            " is only available with manila API version >= 2.41")

    boolean_keys = (
        'snapshot_support',
        'create_share_from_snapshot_support',
        'revert_to_snapshot_support',
        'mount_snapshot_support'
    )
    for key in boolean_keys:
        value = getattr(args, key)

        if value is not None and key in kwargs['extra_specs']:
            msg = ("Argument '%s' value specified twice." % key)
            raise exceptions.CommandError(msg)

        try:
            if value:
                kwargs['extra_specs'][key] = (
                    strutils.bool_from_string(value, strict=True))
            elif key in kwargs['extra_specs']:
                kwargs['extra_specs'][key] = (
                    strutils.bool_from_string(
                        kwargs['extra_specs'][key], strict=True))
        except ValueError as e:
            msg = ("Argument '%s' is of boolean "
                   "type and has invalid value: %s" % (key, six.text_type(e)))
            raise exceptions.CommandError(msg)

    stype = cs.share_types.create(**kwargs)
    _print_share_type(stype, show_des=show_des)


@cliutils.arg(
    'id',
    metavar='<id>',
    nargs='+',
    help="Name or ID of the share type(s) to delete.")
def do_type_delete(cs, args):
    """Delete one or more specific share types (Admin only)."""

    failure_count = 0

    for name_or_id in args.id:
        try:
            id_ref = _find_share_type(cs, name_or_id)
            cs.share_types.delete(id_ref)
        except Exception as e:
            failure_count += 1
            print("Delete for share type %s failed: %s" % (
                name_or_id, e), file=sys.stderr)

    if failure_count == len(args.id):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "share types.")


@cliutils.arg(
    'stype',
    metavar='<stype>',
    help="Name or ID of the share type.")
@cliutils.arg(
    'action',
    metavar='<action>',
    choices=['set', 'unset'],
    help="Actions: 'set' or 'unset'.")
@cliutils.arg(
    'metadata',
    metavar='<key=value>',
    nargs='*',
    default=None,
    help='Extra_specs to set or unset (key is only necessary on unset).')
def do_type_key(cs, args):
    """Set or unset extra_spec for a share type (Admin only)."""
    stype = _find_share_type(cs, args.stype)

    if args.metadata is not None:
        keypair = _extract_metadata(args)

        if args.action == 'set':
            stype.set_keys(keypair)
        elif args.action == 'unset':
            stype.unset_keys(list(keypair))


@cliutils.arg(
    'share_type',
    metavar='<share_type>',
    help="Filter results by share type name or ID.")
def do_type_access_list(cs, args):
    """Print access information about the given share type (Admin only)."""
    share_type = _find_share_type(cs, args.share_type)
    if share_type.is_public:
        raise exceptions.CommandError("Forbidden to get access list "
                                      "for public share type.")
    access_list = cs.share_type_access.list(share_type)

    columns = ['Project_ID']
    cliutils.print_list(access_list, columns)


@cliutils.arg(
    'share_type',
    metavar='<share_type>',
    help="Share type name or ID to add access"
         " for the given project.")
@cliutils.arg(
    'project_id',
    metavar='<project_id>',
    help='Project ID to add share type access for.')
def do_type_access_add(cs, args):
    """Adds share type access for the given project (Admin only)."""
    vtype = _find_share_type(cs, args.share_type)
    cs.share_type_access.add_project_access(vtype, args.project_id)


@cliutils.arg(
    'share_type',
    metavar='<share_type>',
    help=('Share type name or ID to remove access '
          'for the given project.'))
@cliutils.arg(
    'project_id',
    metavar='<project_id>',
    help='Project ID to remove share type access for.')
def do_type_access_remove(cs, args):
    """Removes share type access for the given project (Admin only)."""
    vtype = _find_share_type(cs, args.share_type)
    cs.share_type_access.remove_project_access(
        vtype, args.project_id)


##############################################################################
#
# Share group types
#
##############################################################################


def _print_share_group_type_list(share_group_types,
                                 default_share_group_type=None, columns=None):

    def _is_default(share_group_type):
        if hasattr(share_group_type, 'is_default'):
            return 'YES' if share_group_type.is_default else '-'
        elif default_share_group_type:
            default = default_share_group_type.id
            return 'YES' if share_group_type.id == default else '-'
        else:
            return '-'

    formatters = {
        'visibility': _is_share_type_public,
        'is_default': _is_default,
    }

    for sg_type in share_group_types:
        sg_type = sg_type.to_dict()
        sg_type['visibility'] = sg_type.pop('is_public', 'unknown')

    fields = [
        'ID',
        'Name',
        'visibility',
        'is_default',
    ]
    if columns is not None:
        fields = _split_columns(columns=columns, title=False)

    cliutils.print_list(share_group_types, fields, formatters,
                        sortby_index=None)


def _print_share_group_type(share_group_type, default_share_type=None):

    def _is_default(share_group_type):
        if hasattr(share_group_type, 'is_default'):
            return 'YES' if share_group_type.is_default else '-'
        return '-'

    share_group_type_dict = {
        'ID': share_group_type.id,
        'Name': share_group_type.name,
        'Visibility': _is_share_type_public(share_group_type),
        'is_default': _is_default(share_group_type)
    }
    cliutils.print_dict(share_group_type_dict)


def _find_share_group_type(cs, sg_type):
    """Get a share group type by name or ID."""
    return apiclient_utils.find_resource(cs.share_group_types, sg_type)


@cliutils.arg(
    '--all',
    dest='all',
    action='store_true',
    default=False,
    help='Display all share group types (Admin only).')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_type_list(cs, args):
    """Print a list of available 'share group types'."""

    sg_types = cs.share_group_types.list(show_all=args.all)

    default = None
    if sg_types and not hasattr(sg_types[0], 'is_default'):
        if ((args.columns and 'is_default' in args.columns) or
                args.columns is None):
            default = cs.share_group_types.get()

    _print_share_group_type_list(
        sg_types, default_share_group_type=default, columns=args.columns)


@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_type_specs_list(cs, args):
    """Print a list of 'share group types specs' (Admin Only)."""

    sg_types = cs.share_group_types.list()
    _print_type_and_extra_specs_list(sg_types, columns=args.columns)


@cliutils.arg(
    'name',
    metavar='<name>',
    help='Name of the new share group type.')
@cliutils.arg(
    'share_types',
    metavar='<share_types>',
    type=str,
    help='Comma-separated list of share type names or IDs.')
@cliutils.arg(
    '--is_public',
    '--is-public',
    metavar='<is_public>',
    action='single_alias',
    help='Make type accessible to the public (default true).')
@cliutils.arg(
    '--group-specs',
    '--group_specs',
    metavar='<key=value>',
    type=str,
    nargs='*',
    action='single_alias',
    default=None,
    help='Share Group type extra specs by key and value. '
         'OPTIONAL: Default=None. '
         'Example: "--group-specs consistent_snapshot_support=host".',)
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_type_create(cs, args):
    """Create a new share group type (Admin only)."""

    share_types = [_find_share_type(cs, share_type)
                   for share_type in args.share_types.split(',')]

    kwargs = {
        'share_types': share_types,
        'name': args.name,
        'is_public': strutils.bool_from_string(args.is_public, default=True),
    }
    if args.group_specs is not None:
        kwargs['group_specs'] = _extract_group_specs(args)

    sg_type = cs.share_group_types.create(**kwargs)
    _print_share_group_type(sg_type)


@cliutils.arg(
    'id',
    metavar='<id>',
    help="Name or ID of the share group type to delete.")
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_type_delete(cs, args):
    """Delete a specific share group type (Admin only)."""
    share_group_type = _find_share_group_type(cs, args.id)
    cs.share_group_types.delete(share_group_type)


@cliutils.arg(
    'share_group_type',
    metavar='<share_group_type>',
    help="Name or ID of the share group type.")
@cliutils.arg(
    'action',
    metavar='<action>',
    choices=['set', 'unset'],
    help="Actions: 'set' or 'unset'.")
@cliutils.arg(
    'group_specs',
    metavar='<key=value>',
    nargs='*',
    default=None,
    help='Group specs to set or unset (key is only necessary on unset).')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_type_key(cs, args):
    """Set or unset group_spec for a share group type (Admin only)."""
    sg_type = _find_share_group_type(cs, args.share_group_type)
    if args.group_specs is not None:
        keypair = _extract_group_specs(args)
        if args.action == 'set':
            sg_type.set_keys(keypair)
        elif args.action == 'unset':
            sg_type.unset_keys(list(keypair))


@cliutils.arg(
    'share_group_type',
    metavar='<share_group_type>',
    help="Filter results by share group type name or ID.")
def do_share_group_type_access_list(cs, args):
    """Print access information about a share group type (Admin only)."""
    share_group_type = _find_share_group_type(cs, args.share_group_type)
    if share_group_type.is_public:
        raise exceptions.CommandError(
            "Forbidden to get access list for public share group type.")
    access_list = cs.share_group_type_access.list(share_group_type)
    columns = ['Project_ID']
    cliutils.print_list(access_list, columns)


@cliutils.arg(
    'share_group_type',
    metavar='<share_group_type>',
    help='Share group type name or ID to add access for the given project.')
@cliutils.arg(
    'project_id',
    metavar='<project_id>',
    help='Project ID to add share group type access for.')
def do_share_group_type_access_add(cs, args):
    """Adds share group type access for the given project (Admin only)."""
    share_group_type = _find_share_group_type(cs, args.share_group_type)
    cs.share_group_type_access.add_project_access(
        share_group_type, args.project_id)


@cliutils.arg(
    'share_group_type',
    metavar='<share_group_type>',
    help='Share group type name or ID to remove access for the given project.')
@cliutils.arg(
    'project_id',
    metavar='<project_id>',
    help='Project ID to remove share group type access for.')
def do_share_group_type_access_remove(cs, args):
    """Removes share group type access for the given project (Admin only)."""
    share_group_type = _find_share_group_type(cs, args.share_group_type)
    cs.share_group_type_access.remove_project_access(
        share_group_type, args.project_id)


##############################################################################
#
# Share groups
#
##############################################################################


@cliutils.arg(
    '--name',
    metavar='<name>',
    help='Optional share group name. (Default=None)',
    default=None)
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional share group description. (Default=None)',
    default=None)
@cliutils.arg(
    '--share-types', '--share_types',
    metavar='<share_types>',
    type=str,
    default=None,
    action='single_alias',
    help='Comma-separated list of share types. (Default=None)')
@cliutils.arg(
    '--share-group-type', '--share_group_type', '--type',
    metavar='<share_group_type>',
    type=str,
    default=None,
    action='single_alias',
    help="Share group type name or ID of the share group to be created. "
         "(Default=None)")
@cliutils.arg(
    '--share-network',
    '--share_network',
    metavar='<share_network>',
    type=str,
    default=None,
    action='single_alias',
    help='Specify share network name or id.')
@cliutils.arg(
    '--source-share-group-snapshot',
    '--source_share_group_snapshot',
    metavar='<source_share_group_snapshot>',
    type=str,
    action='single_alias',
    help='Optional share group snapshot name or ID to create the share group '
         'from. (Default=None)',
    default=None)
@cliutils.arg(
    '--availability-zone',
    '--availability_zone',
    '--az',
    default=None,
    action='single_alias',
    metavar='<availability-zone>',
    help='Optional availability zone in which group should be created. '
         '(Default=None)')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_create(cs, args):
    """Creates a new share group (Experimental)."""

    share_types = []
    if args.share_types:
        s_types = args.share_types.split(',')
        for s_type in s_types:
            share_type = _find_share_type(cs, s_type)
            share_types.append(share_type)

    share_group_type = None
    if args.share_group_type:
        share_group_type = _find_share_group_type(cs, args.share_group_type)

    share_network = None
    if args.share_network:
        share_network = _find_share_network(cs, args.share_network)

    share_group_snapshot = None
    if args.source_share_group_snapshot:
        share_group_snapshot = _find_share_group_snapshot(
            cs, args.source_share_group_snapshot)

    kwargs = {
        'share_group_type': share_group_type,
        'share_types': share_types or None,
        'name': args.name,
        'description': args.description,
        'availability_zone': args.availability_zone,
        'source_share_group_snapshot': share_group_snapshot,
        'share_network': share_network,
    }

    share_group = cs.share_groups.create(**kwargs)
    _print_share_group(cs, share_group)


@cliutils.arg(
    '--all-tenants',
    dest='all_tenants',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help='Display information from all tenants (Admin only).')
@cliutils.arg(
    '--name',
    metavar='<name>',
    type=six.text_type,
    default=None,
    help='Filter results by name.')
@cliutils.arg(
    '--description',
    metavar='<description>',
    type=six.text_type,
    default=None,
    help='Filter results by description. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--status',
    metavar='<status>',
    type=str,
    default=None,
    help='Filter results by status.')
@cliutils.arg(
    '--share-server-id', '--share-server_id',
    '--share_server-id', '--share_server_id',
    metavar='<share_server_id>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by share server ID (Admin only).')
@cliutils.arg(
    '--share-group-type', '--share-group-type-id',
    '--share_group_type', '--share_group_type_id',
    metavar='<share_group_type>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by a share group type ID or name that was used for '
         'share group creation.')
@cliutils.arg(
    '--snapshot',
    metavar='<snapshot>',
    type=str,
    default=None,
    help='Filter results by share group snapshot name or ID that was used to '
         'create the share group.')
@cliutils.arg(
    '--host',
    metavar='<host>',
    default=None,
    help='Filter results by host.')
@cliutils.arg(
    '--share-network', '--share_network',
    metavar='<share_network>',
    type=str,
    default=None,
    action='single_alias',
    help='Filter results by share-network name or ID.')
@cliutils.arg(
    '--project-id', '--project_id',
    metavar='<project_id>',
    type=str,
    default=None,
    action='single_alias',
    help="Filter results by project ID. Useful with set key '--all-tenants'.")
@cliutils.arg(
    '--limit',
    metavar='<limit>',
    type=int,
    default=None,
    help='Maximum number of share groups to return. (Default=None)')
@cliutils.arg(
    '--offset',
    metavar="<offset>",
    default=None,
    help='Start position of share group listing.')
@cliutils.arg(
    '--sort-key', '--sort_key',
    metavar='<sort_key>',
    type=str,
    default=None,
    action='single_alias',
    help='Key to be sorted, available keys are %(keys)s. Default=None.' % {
        'keys': constants.SHARE_GROUP_SORT_KEY_VALUES})
@cliutils.arg(
    '--sort-dir', '--sort_dir',
    metavar='<sort_dir>',
    type=str,
    default=None,
    action='single_alias',
    help='Sort direction, available values are %(values)s. '
         'OPTIONAL: Default=None.' % {'values': constants.SORT_DIR_VALUES})
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
@cliutils.arg(
    '--name~',
    metavar='<name~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share group name pattern. '
         'Available only for microversion >= 2.36.')
@cliutils.arg(
    '--description~',
    metavar='<description~>',
    type=six.text_type,
    default=None,
    help='Filter results matching a share group description pattern. '
         'Available only for microversion >= 2.36.')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_list(cs, args):
    """List share groups with filters (Experimental)."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = ('ID', 'Name', 'Status', 'Description')

    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))
    empty_obj = type('Empty', (object,), {'id': None})
    sg_type = (_find_share_group_type(cs, args.share_group_type)
               if args.share_group_type else empty_obj)
    snapshot = (_find_share_snapshot(cs, args.snapshot)
                if args.snapshot else empty_obj)
    share_network = (_find_share_network(cs, args.share_network)
                     if args.share_network else empty_obj)

    search_opts = {
        'offset': args.offset,
        'limit': args.limit,
        'all_tenants': all_tenants,
        'name': args.name,
        'status': args.status,
        'share_server_id': args.share_server_id,
        'share_group_type_id': sg_type.id,
        'source_share_group_snapshot_id': snapshot.id,
        'host': args.host,
        'share_network_id': share_network.id,
        'project_id': args.project_id,
    }
    if cs.api_version.matches(api_versions.APIVersion("2.36"),
                              api_versions.APIVersion()):
        search_opts['name~'] = getattr(args, 'name~')
        search_opts['description~'] = getattr(args, 'description~')
        search_opts['description'] = getattr(args, 'description')
    elif (getattr(args, 'name~') or getattr(args, 'description~') or
          getattr(args, 'description')):
        raise exceptions.CommandError(
            "Pattern based filtering (name~, description~ and description)"
            " is only available with manila API version >= 2.36")

    share_groups = cs.share_groups.list(
        search_opts=search_opts, sort_key=args.sort_key,
        sort_dir=args.sort_dir)
    cliutils.print_list(share_groups, fields=list_of_keys,
                        sortby_index=None)


@cliutils.arg(
    'share_group',
    metavar='<share_group>',
    help='Name or ID of the share group.')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_show(cs, args):
    """Show details about a share group (Experimental)."""
    share_group = _find_share_group(cs, args.share_group)
    _print_share_group(cs, share_group)


@cliutils.arg(
    'share_group',
    metavar='<share_group>',
    help='Name or ID of the share group to update.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help='Optional new name for the share group. (Default=None)')
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional share group description. (Default=None)',
    default=None)
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_update(cs, args):
    """Update a share group (Experimental)."""
    kwargs = {}

    if args.name is not None:
        kwargs['name'] = args.name
    if args.description is not None:
        kwargs['description'] = args.description

    if not kwargs:
        msg = "Must supply name and/or description"
        raise exceptions.CommandError(msg)
    share_group = _find_share_group(cs, args.share_group)
    share_group = cs.share_groups.update(share_group, **kwargs)
    _print_share_group(cs, share_group)


@cliutils.arg(
    'share_group',
    metavar='<share_group>',
    nargs='+',
    help='Name or ID of the share_group(s).')
@cliutils.arg(
    '--force',
    action='store_true',
    default=False,
    help='Attempt to force delete the share group (Default=False)'
         ' (Admin only).')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_delete(cs, args):
    """Remove one or more share groups (Experimental)."""
    failure_count = 0
    kwargs = {}

    if args.force is not None:
        kwargs['force'] = args.force

    for share_group in args.share_group:
        try:
            share_group_ref = _find_share_group(cs, share_group)
            cs.share_groups.delete(share_group_ref, **kwargs)
        except Exception as e:
            failure_count += 1
            print("Delete for share group %s failed: %s" % (share_group, e),
                  file=sys.stderr)

    if failure_count == len(args.share_group):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "share groups.")


@cliutils.arg(
    'share_group',
    metavar='<share_group>',
    help='Name or ID of the share group to modify.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default='available',
    help=('Indicate which state to assign the share group. '
          'Options include available, error, creating, deleting, '
          'error_deleting. If no state is provided, '
          'available will be used.'))
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_reset_state(cs, args):
    """Explicitly update the state of a share group

    (Admin only, Experimental).
    """
    share_group = _find_share_group(cs, args.share_group)
    cs.share_groups.reset_state(share_group, args.state)


##############################################################################
#
# Share group snapshots
#
##############################################################################


@cliutils.arg(
    'share_group',
    metavar='<share_group>',
    help='Name or ID of the share group.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    help='Optional share group snapshot name. (Default=None)',
    default=None)
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional share group snapshot description. (Default=None)',
    default=None)
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_snapshot_create(cs, args):
    """Creates a new share group snapshot (Experimental)."""
    kwargs = {'name': args.name, 'description': args.description}
    share_group = _find_share_group(cs, args.share_group)
    sg_snapshot = cs.share_group_snapshots.create(share_group.id, **kwargs)
    _print_share_group_snapshot(cs, sg_snapshot)


@cliutils.arg(
    '--all-tenants',
    dest='all_tenants',
    metavar='<0|1>',
    nargs='?',
    type=int,
    const=1,
    default=0,
    help='Display information from all tenants (Admin only).')
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help='Filter results by name.')
@cliutils.arg(
    '--status',
    metavar='<status>',
    default=None,
    help='Filter results by status.')
@cliutils.arg(
    '--share-group-id', '--share_group_id',
    metavar='<share_group_id>',
    default=None,
    action='single_alias',
    help='Filter results by share group ID.')
@cliutils.arg(
    '--limit',
    metavar='<limit>',
    type=int,
    default=None,
    help='Maximum number of share group snapshots to return. '
         '(Default=None)')
@cliutils.arg(
    '--offset',
    metavar="<offset>",
    default=None,
    help='Start position of share group snapshot listing.')
@cliutils.arg(
    '--sort-key', '--sort_key',
    metavar='<sort_key>',
    type=str,
    default=None,
    action='single_alias',
    help='Key to be sorted, available keys are %(keys)s. Default=None.' % {
        'keys': constants.SHARE_GROUP_SNAPSHOT_SORT_KEY_VALUES})
@cliutils.arg(
    '--sort-dir', '--sort_dir',
    metavar='<sort_dir>',
    type=str,
    default=None,
    action='single_alias',
    help='Sort direction, available values are %(values)s. '
         'OPTIONAL: Default=None.' % {'values': constants.SORT_DIR_VALUES})
@cliutils.arg(
    '--detailed',
    dest='detailed',
    default=True,
    help='Show detailed information about share group snapshots.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_snapshot_list(cs, args):
    """List share group snapshots with filters (Experimental)."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = ('id', 'name', 'status', 'description')

    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))

    search_opts = {
        'offset': args.offset,
        'limit': args.limit,
        'all_tenants': all_tenants,
        'name': args.name,
        'status': args.status,
        'share_group_id': args.share_group_id,
    }
    share_group_snapshots = cs.share_group_snapshots.list(
        detailed=args.detailed, search_opts=search_opts,
        sort_key=args.sort_key, sort_dir=args.sort_dir)
    cliutils.print_list(share_group_snapshots, fields=list_of_keys,
                        sortby_index=None)


@cliutils.arg(
    'share_group_snapshot',
    metavar='<share_group_snapshot>',
    help='Name or ID of the share group snapshot.')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_snapshot_show(cs, args):
    """Show details about a share group snapshot (Experimental)."""
    sg_snapshot = _find_share_group_snapshot(cs, args.share_group_snapshot)
    _print_share_group_snapshot(cs, sg_snapshot)


@cliutils.arg(
    'share_group_snapshot',
    metavar='<share_group_snapshot>',
    help='Name or ID of the share group snapshot.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,name".')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_snapshot_list_members(cs, args):
    """List members of a share group snapshot (Experimental)."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = ('Share ID', 'Size')

    sg_snapshot = _find_share_group_snapshot(cs, args.share_group_snapshot)
    members = [type('ShareGroupSnapshotMember', (object,), member)
               for member in sg_snapshot._info.get('members', [])]
    cliutils.print_list(members, fields=list_of_keys)


@cliutils.arg(
    '--state',
    metavar='<state>',
    default='available',
    help=('Indicate which state to assign the share group snapshot. '
          'Options include available, error, creating, deleting, '
          'error_deleting. If no state is provided, '
          'available will be used.'))
@cliutils.arg(
    'share_group_snapshot',
    metavar='<share_group_snapshot>',
    help='Name or ID of the share group snapshot.')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_snapshot_reset_state(cs, args):
    """Explicitly update the state of a share group snapshot

    (Admin only, Experimental).
    """
    sg_snapshot = _find_share_group_snapshot(cs, args.share_group_snapshot)
    cs.share_group_snapshots.reset_state(sg_snapshot, args.state)


@cliutils.arg(
    'share_group_snapshot',
    metavar='<share_group_snapshot>',
    help='Name or ID of the share group snapshot to update.')
@cliutils.arg(
    '--name',
    metavar='<name>',
    default=None,
    help='Optional new name for the share group snapshot. (Default=None)')
@cliutils.arg(
    '--description',
    metavar='<description>',
    help='Optional share group snapshot description. (Default=None)',
    default=None)
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_snapshot_update(cs, args):
    """Update a share group snapshot (Experimental)."""
    kwargs = {}

    if args.name is not None:
        kwargs['name'] = args.name
    if args.description is not None:
        kwargs['description'] = args.description

    if not kwargs:
        msg = "Must supply name and/or description"
        raise exceptions.CommandError(msg)

    sg_snapshot = _find_share_group_snapshot(cs, args.share_group_snapshot)
    cs.share_group_snapshots.update(sg_snapshot, **kwargs)


@cliutils.arg(
    'share_group_snapshot',
    metavar='<share_group_snapshot>',
    nargs='+',
    help='Name or ID of the share group snapshot(s) to delete.')
@cliutils.arg(
    '--force',
    action='store_true',
    default=False,
    help='Attempt to force delete the share group snapshot(s) (Default=False)'
         ' (Admin only).')
@cliutils.service_type('sharev2')
@api_versions.experimental_api
def do_share_group_snapshot_delete(cs, args):
    """Remove one or more share group snapshots (Experimental)."""
    failure_count = 0
    kwargs = {}

    if args.force is not None:
        kwargs['force'] = args.force

    for sg_snapshot in args.share_group_snapshot:
        try:
            sg_snapshot_ref = _find_share_group_snapshot(cs, sg_snapshot)
            cs.share_group_snapshots.delete(sg_snapshot_ref, **kwargs)
        except Exception as e:
            failure_count += 1
            print("Delete for share group snapshot %s failed: %s" % (
                sg_snapshot, e), file=sys.stderr)

    if failure_count == len(args.share_group_snapshot):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "share group snapshots.")


##############################################################################
#
# Share replicas
#
##############################################################################


@cliutils.arg(
    '--share-id',
    '--share_id',
    '--si',  # alias
    metavar='<share_id>',
    default=None,
    action='single_alias',
    help='List replicas belonging to share.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "replica_state,id".')
@api_versions.wraps("2.11")
def do_share_replica_list(cs, args):
    """List share replicas (Experimental)."""
    share = _find_share(cs, args.share_id) if args.share_id else None

    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = [
            'ID',
            'Status',
            'Replica State',
            'Share ID',
            'Host',
            'Availability Zone',
            'Updated At',
        ]

    if share:
        replicas = cs.share_replicas.list(share)
    else:
        replicas = cs.share_replicas.list()

    cliutils.print_list(replicas, list_of_keys)


@cliutils.arg(
    'share',
    metavar='<share>',
    help='Name or ID of the share to replicate.')
@cliutils.arg(
    '--availability-zone',
    '--availability_zone',
    '--az',
    default=None,
    action='single_alias',
    metavar='<availability-zone>',
    help='Optional Availability zone in which replica should be created.')
@cliutils.arg(
    '--share-network',
    '--share_network',
    metavar='<network-info>',
    default=None,
    action='single_alias',
    help='Optional network info ID or name.')
@api_versions.wraps("2.11")
def do_share_replica_create(cs, args):
    """Create a share replica (Experimental)."""
    share = _find_share(cs, args.share)

    share_network = None
    if args.share_network:
        share_network = _find_share_network(cs, args.share_network)

    replica = cs.share_replicas.create(share,
                                       args.availability_zone,
                                       share_network)
    _print_share_replica(cs, replica)


@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='ID of the share replica.')
@api_versions.wraps("2.11", "2.46")
def do_share_replica_show(cs, args):
    """Show details about a replica (Experimental)."""

    replica = cs.share_replicas.get(args.replica)
    _print_share_replica(cs, replica)


@api_versions.wraps("2.47")  # noqa
@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='ID of the share replica.')
def do_share_replica_show(cs, args):
    """Show details about a replica (Experimental)."""

    replica = cs.share_replicas.get(args.replica)
    export_locations = cs.share_replica_export_locations.list(replica)
    replica._info['export_locations'] = export_locations
    _print_share_replica(cs, replica)


@cliutils.arg(
    'replica',
    metavar='<replica>',
    nargs='+',
    help='ID of the share replica.')
@cliutils.arg(
    '--force',
    action='store_true',
    default=False,
    help='Attempt to force deletion of a replica on its backend. Using '
         'this option will purge the replica from Manila even if it '
         'is not cleaned up on the backend. Defaults to False.')
@api_versions.wraps("2.11")
def do_share_replica_delete(cs, args):
    """Remove one or more share replicas (Experimental)."""
    failure_count = 0
    kwargs = {
        "force": args.force
    }

    for replica in args.replica:
        try:
            replica_ref = _find_share_replica(cs, replica)
            cs.share_replicas.delete(replica_ref, **kwargs)
        except Exception as e:
            failure_count += 1
            print("Delete for share replica %s failed: %s" % (replica, e),
                  file=sys.stderr)

    if failure_count == len(args.replica):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "replicas.")


@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='ID of the share replica.')
@api_versions.wraps("2.11")
def do_share_replica_promote(cs, args):
    """Promote specified replica to 'active' replica_state (Experimental)."""
    replica = _find_share_replica(cs, args.replica)
    cs.share_replicas.promote(replica)


@api_versions.wraps("2.47")
@api_versions.experimental_api
@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='ID of the share replica.')
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "id,path,replica_state".')
def do_share_replica_export_location_list(cs, args):
    """List export locations of a share replica (Experimental)."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = [
            'ID',
            'Availability Zone',
            'Replica State',
            'Preferred',
            'Path',
        ]
    replica = _find_share_replica(cs, args.replica)
    export_locations = cs.share_replica_export_locations.list(replica)
    cliutils.print_list(export_locations, list_of_keys)


@api_versions.wraps("2.47")
@api_versions.experimental_api
@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='Name or ID of the share instance.')
@cliutils.arg(
    'export_location',
    metavar='<export_location>',
    help='ID of the share instance export location.')
def do_share_replica_export_location_show(cs, args):
    """Show details of a share replica's export location (Experimental)."""
    replica = _find_share_replica(cs, args.replica)
    export_location = cs.share_replica_export_locations.get(
        replica, args.export_location)
    view_data = export_location._info.copy()
    cliutils.print_dict(view_data)


@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='ID of the share replica to modify.')
@cliutils.arg(
    '--state',
    metavar='<state>',
    default='available',
    help=('Indicate which state to assign the replica. Options include '
          'available, error, creating, deleting, error_deleting. If no '
          'state is provided, available will be used.'))
@api_versions.wraps("2.11")
def do_share_replica_reset_state(cs, args):
    """Explicitly update the 'status' of a share replica (Experimental)."""
    replica = _find_share_replica(cs, args.replica)
    cs.share_replicas.reset_state(replica, args.state)


@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='ID of the share replica to modify.')
@cliutils.arg(
    '--replica-state',
    '--replica_state',
    '--state',  # alias for user sanity
    metavar='<replica_state>',
    default='out_of_sync',
    action='single_alias',
    help=('Indicate which replica_state to assign the replica. Options '
          'include in_sync, out_of_sync, active, error. If no '
          'state is provided, out_of_sync will be used.'))
@api_versions.wraps("2.11")
def do_share_replica_reset_replica_state(cs, args):
    """Explicitly update the 'replica_state' of a share replica

    (Experimental).
    """
    replica = _find_share_replica(cs, args.replica)
    cs.share_replicas.reset_replica_state(replica, args.replica_state)


@cliutils.arg(
    'replica',
    metavar='<replica>',
    help='ID of the share replica to resync.')
@api_versions.wraps("2.11")
def do_share_replica_resync(cs, args):
    """Attempt to update the share replica with its 'active' mirror

     (Experimental).
     """
    replica = _find_share_replica(cs, args.replica)
    cs.share_replicas.resync(replica)


##############################################################################
#
# User Messages
#
##############################################################################


@api_versions.wraps("2.37")
@cliutils.arg(
    '--resource_id',
    '--resource-id',
    '--resource',
    metavar='<resource_id>',
    default=None,
    action='single_alias',
    help='Filters results by a resource uuid. Default=None.')
@cliutils.arg(
    '--resource_type',
    '--resource-type',
    metavar='<type>',
    default=None,
    action='single_alias',
    help='Filters results by a resource type. Default=None. '
         'Example: "manila message-list --resource_type share"')
@cliutils.arg(
    '--action_id',
    '--action-id',
    '--action',
    metavar='<id>',
    default=None,
    action='single_alias',
    help='Filters results by action id. Default=None.')
@cliutils.arg(
    '--detail_id',
    '--detail-id',
    '--detail',
    metavar='<id>',
    default=None,
    action='single_alias',
    help='Filters results by detail id. Default=None.')
@cliutils.arg(
    '--request_id',
    '--request-id',
    '--request',
    metavar='<request_id>',
    default=None,
    action='single_alias',
    help='Filters results by request id. Default=None.')
@cliutils.arg(
    '--level',
    '--message_level',
    '--message-level',
    metavar='<level>',
    default=None,
    action='single_alias',
    help='Filters results by the message level. Default=None. '
         'Example: "manila message-list --level ERROR".')
@cliutils.arg(
    '--limit',
    metavar='<limit>',
    type=int,
    default=None,
    help='Maximum number of messages to return. (Default=None)')
@cliutils.arg(
    '--offset',
    metavar="<offset>",
    default=None,
    help='Start position of message listing.')
@cliutils.arg(
    '--sort-key', '--sort_key',
    metavar='<sort_key>',
    type=str,
    default=None,
    action='single_alias',
    help='Key to be sorted, available keys are %(keys)s. Default=desc.' % {
        'keys': constants.MESSAGE_SORT_KEY_VALUES})
@cliutils.arg(
    '--sort-dir', '--sort_dir',
    metavar='<sort_dir>',
    type=str,
    default=None,
    action='single_alias',
    help='Sort direction, available values are %(values)s. '
         'OPTIONAL: Default=None.' % {'values': constants.SORT_DIR_VALUES})
@cliutils.arg(
    '--columns',
    metavar='<columns>',
    type=str,
    default=None,
    help='Comma separated list of columns to be displayed '
         'example --columns "resource_id,user_message".')
def do_message_list(cs, args):
    """Lists all messages."""
    if args.columns is not None:
        list_of_keys = _split_columns(columns=args.columns)
    else:
        list_of_keys = ['ID', 'Resource Type', 'Resource ID', 'Action ID',
                        'User Message', 'Detail ID', 'Created At']

    search_opts = {
        'offset': args.offset,
        'limit': args.limit,
        'request_id': args.request_id,
        'resource_type': args.resource_type,
        'resource_id': args.resource_id,
        'action_id': args.action_id,
        'detail_id': args.detail_id,
        'message_level': args.level
    }
    messages = cs.messages.list(
        search_opts=search_opts, sort_key=args.sort_key,
        sort_dir=args.sort_dir)
    cliutils.print_list(messages, fields=list_of_keys, sortby_index=None)


@cliutils.arg(
    'message',
    metavar='<message>',
    help='ID of the message.')
@api_versions.wraps("2.37")
def do_message_show(cs, args):
    """Show details about a message."""

    message = cs.messages.get(args.message)
    _print_message(message)


@api_versions.wraps("2.37")
@cliutils.arg(
    'message',
    metavar='<message>',
    nargs='+',
    help='ID of the message(s).')
def do_message_delete(cs, args):
    """Remove one or more messages."""
    failure_count = 0

    for message in args.message:
        try:
            message_ref = _find_message(cs, message)
            cs.messages.delete(message_ref)
        except Exception as e:
            failure_count += 1
            print("Delete for message %s failed: %s" % (message, e),
                  file=sys.stderr)

    if failure_count == len(args.message):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "messages.")


def _print_message(message):
    message_dict = {
        'id': message.id,
        'resource_type': message.resource_type,
        'resource_id': message.resource_id,
        'action_id': message.action_id,
        'user_message': message.user_message,
        'message_level': message.message_level,
        'detail_id': message.detail_id,
        'created_at': message.created_at,
        'expires_at': message.expires_at,
        'request_id': message.request_id,
    }
    cliutils.print_dict(message_dict)
