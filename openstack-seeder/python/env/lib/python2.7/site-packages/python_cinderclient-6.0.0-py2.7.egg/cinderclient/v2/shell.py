# Copyright (c) 2013-2014 OpenStack Foundation
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import argparse
import collections
import copy
import os

from oslo_utils import strutils
import six

from cinderclient import base
from cinderclient import exceptions
from cinderclient import shell_utils
from cinderclient import utils
from cinderclient.v2 import availability_zones


def _translate_attachments(info):
    attachments = []
    attached_servers = []
    for attachment in info['attachments']:
        attachments.append(attachment['attachment_id'])
        attached_servers.append(attachment['server_id'])
    info.pop('attachments', None)
    info['attachment_ids'] = attachments
    info['attached_servers'] = attached_servers
    return info


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Filters results by a name. Default=None.')
@utils.arg('--display-name',
           help=argparse.SUPPRESS)
@utils.arg('--status',
           metavar='<status>',
           default=None,
           help='Filters results by a status. Default=None.')
@utils.arg('--bootable',
           metavar='<True|true|False|false>',
           const=True,
           nargs='?',
           choices=['True', 'true', 'False', 'false'],
           help='Filters results by bootable status. Default=None.')
@utils.arg('--migration_status',
           metavar='<migration_status>',
           default=None,
           help='Filters results by a migration status. Default=None. '
                'Admin only.')
@utils.arg('--metadata',
           nargs='*',
           metavar='<key=value>',
           default=None,
           help='Filters results by a image metadata key and value pair. '
                'Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning volumes that appear later in the volume '
                'list than that represented by this volume id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of volumes to return. Default=None.')
@utils.arg('--fields',
           default=None,
           metavar='<fields>',
           help='Comma-separated list of fields to display. '
                'Use the show command to see which fields are available. '
                'Unavailable/non-existent fields will be ignored. '
                'Default=None.')
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
@utils.arg('--tenant',
           type=str,
           dest='tenant',
           nargs='?',
           metavar='<tenant>',
           help='Display information from single tenant (Admin only).')
def do_list(cs, args):
    """Lists all volumes."""
    # NOTE(thingee): Backwards-compatibility with v1 args
    if args.display_name is not None:
        args.name = args.display_name

    all_tenants = 1 if args.tenant else \
        int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'project_id': args.tenant,
        'name': args.name,
        'status': args.status,
        'bootable': args.bootable,
        'migration_status': args.migration_status,
        'metadata': (shell_utils.extract_metadata(args) if args.metadata
                     else None),
    }

    # If unavailable/non-existent fields are specified, these fields will
    # be removed from key_list at the print_list() during key validation.
    field_titles = []
    if args.fields:
        for field_title in args.fields.split(','):
            field_titles.append(field_title)

    volumes = cs.volumes.list(search_opts=search_opts, marker=args.marker,
                              limit=args.limit, sort=args.sort)
    shell_utils.translate_volume_keys(volumes)

    # Create a list of servers to which the volume is attached
    for vol in volumes:
        servers = [s.get('server_id') for s in vol.attachments]
        setattr(vol, 'attached_to', ','.join(map(str, servers)))

    if field_titles:
        # Remove duplicate fields
        key_list = ['ID']
        unique_titles = [k for k in collections.OrderedDict.fromkeys(
            [x.title().strip() for x in field_titles]) if k != 'Id']
        key_list.extend(unique_titles)
    else:
        key_list = ['ID', 'Status', 'Name', 'Size', 'Volume Type',
                    'Bootable', 'Attached to']
        # If all_tenants is specified, print
        # Tenant ID as well.
        if search_opts['all_tenants']:
            key_list.insert(1, 'Tenant ID')

    if args.sort:
        sortby_index = None
    else:
        sortby_index = 0
    utils.print_list(volumes, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index)


@utils.arg('volume',
           metavar='<volume>',
           help='Name or ID of volume.')
def do_show(cs, args):
    """Shows volume details."""
    info = dict()
    volume = utils.find_volume(cs, args.volume)
    info.update(volume._info)

    if 'readonly' in info['metadata']:
        info['readonly'] = info['metadata']['readonly']

    info.pop('links', None)
    info = _translate_attachments(info)
    utils.print_dict(info,
                     formatters=['metadata', 'volume_image_metadata',
                                 'attachment_ids', 'attached_servers'])


class CheckSizeArgForCreate(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        if ((args.snapshot_id or args.source_volid)
                is None and values is None):
            if not hasattr(args, 'backup_id') or args.backup_id is None:
                parser.error('Size is a required parameter if snapshot '
                             'or source volume or backup is not specified.')
        setattr(args, self.dest, values)


@utils.arg('size',
           metavar='<size>',
           nargs='?',
           type=int,
           action=CheckSizeArgForCreate,
           help='Size of volume, in GiBs. (Required unless '
                'snapshot-id/source-volid is specified).')
@utils.arg('--consisgroup-id',
           metavar='<consistencygroup-id>',
           default=None,
           help='ID of a consistency group where the new volume belongs to. '
                'Default=None.')
@utils.arg('--snapshot-id',
           metavar='<snapshot-id>',
           default=None,
           help='Creates volume from snapshot ID. Default=None.')
@utils.arg('--snapshot_id',
           help=argparse.SUPPRESS)
@utils.arg('--source-volid',
           metavar='<source-volid>',
           default=None,
           help='Creates volume from volume ID. Default=None.')
@utils.arg('--source_volid',
           help=argparse.SUPPRESS)
@utils.arg('--image-id',
           metavar='<image-id>',
           default=None,
           help='Creates volume from image ID. Default=None.')
@utils.arg('--image_id',
           help=argparse.SUPPRESS)
@utils.arg('--image',
           metavar='<image>',
           default=None,
           help='Creates a volume from image (ID or name). Default=None.')
@utils.arg('--image_ref',
           help=argparse.SUPPRESS)
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Volume name. Default=None.')
@utils.arg('--display-name',
           help=argparse.SUPPRESS)
@utils.arg('--display_name',
           help=argparse.SUPPRESS)
@utils.arg('--description',
           metavar='<description>',
           default=None,
           help='Volume description. Default=None.')
@utils.arg('--display-description',
           help=argparse.SUPPRESS)
@utils.arg('--display_description',
           help=argparse.SUPPRESS)
@utils.arg('--volume-type',
           metavar='<volume-type>',
           default=None,
           help='Volume type. Default=None.')
@utils.arg('--volume_type',
           help=argparse.SUPPRESS)
@utils.arg('--availability-zone',
           metavar='<availability-zone>',
           default=None,
           help='Availability zone for volume. Default=None.')
@utils.arg('--availability_zone',
           help=argparse.SUPPRESS)
@utils.arg('--metadata',
           nargs='*',
           metavar='<key=value>',
           default=None,
           help='Metadata key and value pairs. Default=None.')
@utils.arg('--hint',
           metavar='<key=value>',
           dest='scheduler_hints',
           action='append',
           default=[],
           help='Scheduler hint, similar to nova. Repeat option to set '
                'multiple hints. Values with the same key will be stored '
                'as a list.')
def do_create(cs, args):
    """Creates a volume."""
    # NOTE(thingee): Backwards-compatibility with v1 args
    if args.display_name is not None:
        args.name = args.display_name

    if args.display_description is not None:
        args.description = args.display_description

    volume_metadata = None
    if args.metadata is not None:
        volume_metadata = shell_utils.extract_metadata(args)

    # NOTE(N.S.): take this piece from novaclient
    hints = {}
    if args.scheduler_hints:
        for hint in args.scheduler_hints:
            key, _sep, value = hint.partition('=')
            # NOTE(vish): multiple copies of same hint will
            #             result in a list of values
            if key in hints:
                if isinstance(hints[key], six.string_types):
                    hints[key] = [hints[key]]
                hints[key] += [value]
            else:
                hints[key] = value
    # NOTE(N.S.): end of taken piece

    # Keep backward compatibility with image_id, favoring explicit ID
    image_ref = args.image_id or args.image or args.image_ref

    volume = cs.volumes.create(args.size,
                               args.consisgroup_id,
                               args.snapshot_id,
                               args.source_volid,
                               args.name,
                               args.description,
                               args.volume_type,
                               availability_zone=args.availability_zone,
                               imageRef=image_ref,
                               metadata=volume_metadata,
                               scheduler_hints=hints)

    info = dict()
    volume = cs.volumes.get(volume.id)
    info.update(volume._info)

    if 'readonly' in info['metadata']:
        info['readonly'] = info['metadata']['readonly']

    info.pop('links', None)
    info = _translate_attachments(info)
    utils.print_dict(info)


@utils.arg('--cascade',
           action='store_true',
           default=False,
           help='Remove any snapshots along with volume. Default=False.')
@utils.arg('volume',
           metavar='<volume>', nargs='+',
           help='Name or ID of volume or volumes to delete.')
def do_delete(cs, args):
    """Removes one or more volumes."""
    failure_count = 0
    for volume in args.volume:
        try:
            utils.find_volume(cs, volume).delete(cascade=args.cascade)
            print("Request to delete volume %s has been accepted." % (volume))
        except Exception as e:
            failure_count += 1
            print("Delete for volume %s failed: %s" % (volume, e))
    if failure_count == len(args.volume):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "volumes.")


@utils.arg('volume',
           metavar='<volume>', nargs='+',
           help='Name or ID of volume or volumes to delete.')
def do_force_delete(cs, args):
    """Attempts force-delete of volume, regardless of state."""
    failure_count = 0
    for volume in args.volume:
        try:
            utils.find_volume(cs, volume).force_delete()
        except Exception as e:
            failure_count += 1
            print("Delete for volume %s failed: %s" % (volume, e))
    if failure_count == len(args.volume):
        raise exceptions.CommandError("Unable to force delete any of the "
                                      "specified volumes.")


@utils.arg('volume', metavar='<volume>', nargs='+',
           help='Name or ID of volume to modify.')
@utils.arg('--state', metavar='<state>', default=None,
           help=('The state to assign to the volume. Valid values are '
                 '"available", "error", "creating", "deleting", "in-use", '
                 '"attaching", "detaching", "error_deleting" and '
                 '"maintenance". '
                 'NOTE: This command simply changes the state of the '
                 'Volume in the DataBase with no regard to actual status, '
                 'exercise caution when using. Default=None, that means the '
                 'state is unchanged.'))
@utils.arg('--attach-status', metavar='<attach-status>', default=None,
           help=('The attach status to assign to the volume in the DataBase, '
                 'with no regard to the actual status. Valid values are '
                 '"attached" and "detached". Default=None, that means the '
                 'status is unchanged.'))
@utils.arg('--reset-migration-status',
           action='store_true',
           help=('Clears the migration status of the volume in the DataBase '
                 'that indicates the volume is source or destination of '
                 'volume migration, with no regard to the actual status.'))
def do_reset_state(cs, args):
    """Explicitly updates the volume state in the Cinder database.

    Note that this does not affect whether the volume is actually attached to
    the Nova compute host or instance and can result in an unusable volume.
    Being a database change only, this has no impact on the true state of the
    volume and may not match the actual state. This can render a volume
    unusable in the case of change to the 'available' state.
    """
    failure_flag = False
    migration_status = 'none' if args.reset_migration_status else None
    if not (args.state or args.attach_status or migration_status):
        # Nothing specified, default to resetting state
        args.state = 'available'

    for volume in args.volume:
        try:
            utils.find_volume(cs, volume).reset_state(args.state,
                                                      args.attach_status,
                                                      migration_status)
        except Exception as e:
            failure_flag = True
            msg = "Reset state for volume %s failed: %s" % (volume, e)
            print(msg)

    if failure_flag:
        msg = "Unable to reset the state for the specified volume(s)."
        raise exceptions.CommandError(msg)


@utils.arg('volume',
           metavar='<volume>',
           help='Name or ID of volume to rename.')
@utils.arg('name',
           nargs='?',
           metavar='<name>',
           help='New name for volume.')
@utils.arg('--description', metavar='<description>',
           help='Volume description. Default=None.',
           default=None)
@utils.arg('--display-description',
           help=argparse.SUPPRESS)
@utils.arg('--display_description',
           help=argparse.SUPPRESS)
def do_rename(cs, args):
    """Renames a volume."""
    kwargs = {}

    if args.name is not None:
        kwargs['name'] = args.name
    if args.display_description is not None:
        kwargs['description'] = args.display_description
    elif args.description is not None:
        kwargs['description'] = args.description

    if not any(kwargs):
        msg = 'Must supply either name or description.'
        raise exceptions.ClientException(code=1, message=msg)

    utils.find_volume(cs, args.volume).update(**kwargs)


@utils.arg('volume',
           metavar='<volume>',
           help='Name or ID of volume for which to update metadata.')
@utils.arg('action',
           metavar='<action>',
           choices=['set', 'unset'],
           help='The action. Valid values are "set" or "unset."')
@utils.arg('metadata',
           metavar='<key=value>',
           nargs='+',
           default=[],
           help='Metadata key and value pair to set or unset. '
                'For unset, specify only the key.')
def do_metadata(cs, args):
    """Sets or deletes volume metadata."""
    volume = utils.find_volume(cs, args.volume)
    metadata = shell_utils.extract_metadata(args)

    if args.action == 'set':
        cs.volumes.set_metadata(volume, metadata)
    elif args.action == 'unset':
        # NOTE(zul): Make sure py2/py3 sorting is the same
        cs.volumes.delete_metadata(volume, sorted(metadata.keys(),
                                   reverse=True))


@utils.arg('volume',
           metavar='<volume>',
           help='Name or ID of volume for which to update metadata.')
@utils.arg('action',
           metavar='<action>',
           choices=['set', 'unset'],
           help="The action. Valid values are 'set' or 'unset.'")
@utils.arg('metadata',
           metavar='<key=value>',
           nargs='+',
           default=[],
           help='Metadata key and value pair to set or unset. '
           'For unset, specify only the key.')
def do_image_metadata(cs, args):
    """Sets or deletes volume image metadata."""
    volume = utils.find_volume(cs, args.volume)
    metadata = shell_utils.extract_metadata(args)

    if args.action == 'set':
        cs.volumes.set_image_metadata(volume, metadata)
    elif args.action == 'unset':
        cs.volumes.delete_image_metadata(volume, sorted(metadata.keys(),
                                         reverse=True))


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Filters results by a name. Default=None.')
@utils.arg('--display-name',
           help=argparse.SUPPRESS)
@utils.arg('--display_name',
           help=argparse.SUPPRESS)
@utils.arg('--status',
           metavar='<status>',
           default=None,
           help='Filters results by a status. Default=None.')
@utils.arg('--volume-id',
           metavar='<volume-id>',
           default=None,
           help='Filters results by a volume ID. Default=None.')
@utils.arg('--volume_id',
           help=argparse.SUPPRESS)
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning snapshots that appear later in the snapshot '
                'list than that represented by this id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of snapshots to return. Default=None.')
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
@utils.arg('--tenant',
           type=str,
           dest='tenant',
           nargs='?',
           metavar='<tenant>',
           help='Display information from single tenant (Admin only).')
def do_snapshot_list(cs, args):
    """Lists all snapshots."""
    all_tenants = (1 if args.tenant else
                   int(os.environ.get("ALL_TENANTS", args.all_tenants)))

    if args.display_name is not None:
        args.name = args.display_name

    search_opts = {
        'all_tenants': all_tenants,
        'name': args.name,
        'status': args.status,
        'volume_id': args.volume_id,
        'project_id': args.tenant,
    }

    snapshots = cs.volume_snapshots.list(search_opts=search_opts,
                                         marker=args.marker,
                                         limit=args.limit,
                                         sort=args.sort)
    shell_utils.translate_volume_snapshot_keys(snapshots)
    if args.sort:
        sortby_index = None
    else:
        sortby_index = 0

    utils.print_list(snapshots,
                     ['ID', 'Volume ID', 'Status', 'Name', 'Size'],
                     sortby_index=sortby_index)


@utils.arg('snapshot',
           metavar='<snapshot>',
           help='Name or ID of snapshot.')
def do_snapshot_show(cs, args):
    """Shows snapshot details."""
    snapshot = shell_utils.find_volume_snapshot(cs, args.snapshot)
    shell_utils.print_volume_snapshot(snapshot)


@utils.arg('volume',
           metavar='<volume>',
           help='Name or ID of volume to snapshot.')
@utils.arg('--force',
           metavar='<True|False>',
           const=True,
           nargs='?',
           default=False,
           help='Allows or disallows snapshot of '
           'a volume when the volume is attached to an instance. '
           'If set to True, ignores the current status of the '
           'volume when attempting to snapshot it rather '
           'than forcing it to be available. '
           'Default=False.')
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Snapshot name. Default=None.')
@utils.arg('--display-name',
           help=argparse.SUPPRESS)
@utils.arg('--display_name',
           help=argparse.SUPPRESS)
@utils.arg('--description',
           metavar='<description>',
           default=None,
           help='Snapshot description. Default=None.')
@utils.arg('--display-description',
           help=argparse.SUPPRESS)
@utils.arg('--display_description',
           help=argparse.SUPPRESS)
@utils.arg('--metadata',
           nargs='*',
           metavar='<key=value>',
           default=None,
           help='Snapshot metadata key and value pairs. Default=None.')
def do_snapshot_create(cs, args):
    """Creates a snapshot."""
    if args.display_name is not None:
        args.name = args.display_name

    if args.display_description is not None:
        args.description = args.display_description

    snapshot_metadata = None
    if args.metadata is not None:
        snapshot_metadata = shell_utils.extract_metadata(args)

    volume = utils.find_volume(cs, args.volume)
    snapshot = cs.volume_snapshots.create(volume.id,
                                          args.force,
                                          args.name,
                                          args.description,
                                          metadata=snapshot_metadata)
    shell_utils.print_volume_snapshot(snapshot)


@utils.arg('snapshot',
           metavar='<snapshot>', nargs='+',
           help='Name or ID of the snapshot(s) to delete.')
@utils.arg('--force',
           action="store_true",
           help='Allows deleting snapshot of a volume '
           'when its status is other than "available" or "error". '
           'Default=False.')
def do_snapshot_delete(cs, args):
    """Removes one or more snapshots."""
    failure_count = 0

    for snapshot in args.snapshot:
        try:
            shell_utils.find_volume_snapshot(cs, snapshot).delete(args.force)
        except Exception as e:
            failure_count += 1
            print("Delete for snapshot %s failed: %s" % (snapshot, e))
    if failure_count == len(args.snapshot):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "snapshots.")


@utils.arg('snapshot', metavar='<snapshot>',
           help='Name or ID of snapshot.')
@utils.arg('name', nargs='?', metavar='<name>',
           help='New name for snapshot.')
@utils.arg('--description', metavar='<description>',
           default=None,
           help='Snapshot description. Default=None.')
@utils.arg('--display-description',
           help=argparse.SUPPRESS)
@utils.arg('--display_description',
           help=argparse.SUPPRESS)
def do_snapshot_rename(cs, args):
    """Renames a snapshot."""
    kwargs = {}

    if args.name is not None:
        kwargs['name'] = args.name

    if args.description is not None:
        kwargs['description'] = args.description
    elif args.display_description is not None:
        kwargs['description'] = args.display_description

    if not any(kwargs):
        msg = 'Must supply either name or description.'
        raise exceptions.ClientException(code=1, message=msg)

    shell_utils.find_volume_snapshot(cs, args.snapshot).update(**kwargs)
    print("Request to rename snapshot '%s' has been accepted." % (
        args.snapshot))


@utils.arg('snapshot', metavar='<snapshot>', nargs='+',
           help='Name or ID of snapshot to modify.')
@utils.arg('--state', metavar='<state>',
           default='available',
           help=('The state to assign to the snapshot. Valid values are '
                 '"available", "error", "creating", "deleting", and '
                 '"error_deleting". NOTE: This command simply changes '
                 'the state of the Snapshot in the DataBase with no regard '
                 'to actual status, exercise caution when using. '
                 'Default=available.'))
def do_snapshot_reset_state(cs, args):
    """Explicitly updates the snapshot state."""
    failure_count = 0

    single = (len(args.snapshot) == 1)

    for snapshot in args.snapshot:
        try:
            shell_utils.find_volume_snapshot(
                cs, snapshot).reset_state(args.state)
        except Exception as e:
            failure_count += 1
            msg = "Reset state for snapshot %s failed: %s" % (snapshot, e)
            if not single:
                print(msg)

    if failure_count == len(args.snapshot):
        if not single:
            msg = ("Unable to reset the state for any of the specified "
                   "snapshots.")
        raise exceptions.CommandError(msg)


def do_type_list(cs, args):
    """Lists available 'volume types'.

    (Only admin and tenant users will see private types)
    """
    vtypes = cs.volume_types.list()
    shell_utils.print_volume_type_list(vtypes)


def do_type_default(cs, args):
    """List the default volume type."""
    vtype = cs.volume_types.default()
    shell_utils.print_volume_type_list([vtype])


@utils.arg('volume_type',
           metavar='<volume_type>',
           help='Name or ID of the volume type.')
def do_type_show(cs, args):
    """Show volume type details."""
    vtype = shell_utils.find_vtype(cs, args.volume_type)
    info = dict()
    info.update(vtype._info)

    info.pop('links', None)
    utils.print_dict(info, formatters=['extra_specs'])


@utils.arg('id',
           metavar='<id>',
           help='ID of the volume type.')
@utils.arg('--name',
           metavar='<name>',
           help='Name of the volume type.')
@utils.arg('--description',
           metavar='<description>',
           help='Description of the volume type.')
@utils.arg('--is-public',
           metavar='<is-public>',
           help='Make type accessible to the public or not.')
def do_type_update(cs, args):
    """Updates volume type name, description, and/or is_public."""
    is_public = args.is_public
    if args.name is None and args.description is None and is_public is None:
        raise exceptions.CommandError('Specify a new type name, description, '
                                      'is_public or a combination thereof.')

    if is_public is not None:
        is_public = strutils.bool_from_string(args.is_public, strict=True)
    vtype = cs.volume_types.update(args.id, args.name, args.description,
                                   is_public)
    shell_utils.print_volume_type_list([vtype])


def do_extra_specs_list(cs, args):
    """Lists current volume types and extra specs."""
    vtypes = cs.volume_types.list()
    utils.print_list(vtypes, ['ID', 'Name', 'extra_specs'])


@utils.arg('name',
           metavar='<name>',
           help='Name of new volume type.')
@utils.arg('--description',
           metavar='<description>',
           help='Description of new volume type.')
@utils.arg('--is-public',
           metavar='<is-public>',
           default=True,
           help='Make type accessible to the public (default true).')
def do_type_create(cs, args):
    """Creates a volume type."""
    is_public = strutils.bool_from_string(args.is_public, strict=True)
    vtype = cs.volume_types.create(args.name, args.description, is_public)
    shell_utils.print_volume_type_list([vtype])


@utils.arg('vol_type',
           metavar='<vol_type>', nargs='+',
           help='Name or ID of volume type or types to delete.')
def do_type_delete(cs, args):
    """Deletes volume type or types."""
    failure_count = 0
    for vol_type in args.vol_type:
        try:
            vtype = shell_utils.find_volume_type(cs, vol_type)
            cs.volume_types.delete(vtype)
            print("Request to delete volume type %s has been accepted."
                  % (vol_type))
        except Exception as e:
            failure_count += 1
            print("Delete for volume type %s failed: %s" % (vol_type, e))
    if failure_count == len(args.vol_type):
        raise exceptions.CommandError("Unable to delete any of the "
                                      "specified types.")


@utils.arg('vtype',
           metavar='<vtype>',
           help='Name or ID of volume type.')
@utils.arg('action',
           metavar='<action>',
           choices=['set', 'unset'],
           help='The action. Valid values are "set" or "unset."')
@utils.arg('metadata',
           metavar='<key=value>',
           nargs='+',
           default=[],
           help='The extra specs key and value pair to set or unset. '
                'For unset, specify only the key.')
def do_type_key(cs, args):
    """Sets or unsets extra_spec for a volume type."""
    vtype = shell_utils.find_volume_type(cs, args.vtype)
    keypair = shell_utils.extract_metadata(args)

    if args.action == 'set':
        vtype.set_keys(keypair)
    elif args.action == 'unset':
        vtype.unset_keys(list(keypair))


@utils.arg('--volume-type', metavar='<volume_type>', required=True,
           help='Filter results by volume type name or ID.')
def do_type_access_list(cs, args):
    """Print access information about the given volume type."""
    volume_type = shell_utils.find_volume_type(cs, args.volume_type)
    if volume_type.is_public:
        raise exceptions.CommandError("Failed to get access list "
                                      "for public volume type.")
    access_list = cs.volume_type_access.list(volume_type)

    columns = ['Volume_type_ID', 'Project_ID']
    utils.print_list(access_list, columns)


@utils.arg('--volume-type', metavar='<volume_type>', required=True,
           help='Volume type name or ID to add access for the given project.')
@utils.arg('--project-id', metavar='<project_id>', required=True,
           help='Project ID to add volume type access for.')
def do_type_access_add(cs, args):
    """Adds volume type access for the given project."""
    vtype = shell_utils.find_volume_type(cs, args.volume_type)
    cs.volume_type_access.add_project_access(vtype, args.project_id)


@utils.arg('--volume-type', metavar='<volume_type>', required=True,
           help=('Volume type name or ID to remove access '
                 'for the given project.'))
@utils.arg('--project-id', metavar='<project_id>', required=True,
           help='Project ID to remove volume type access for.')
def do_type_access_remove(cs, args):
    """Removes volume type access for the given project."""
    vtype = shell_utils.find_volume_type(cs, args.volume_type)
    cs.volume_type_access.remove_project_access(
        vtype, args.project_id)


@utils.arg('tenant',
           metavar='<tenant_id>',
           help='ID of tenant for which to list quotas.')
def do_quota_show(cs, args):
    """Lists quotas for a tenant."""

    shell_utils.quota_show(cs.quotas.get(args.tenant))


@utils.arg('tenant', metavar='<tenant_id>',
           help='ID of tenant for which to list quota usage.')
def do_quota_usage(cs, args):
    """Lists quota usage for a tenant."""

    shell_utils.quota_usage_show(cs.quotas.get(args.tenant, usage=True))


@utils.arg('tenant',
           metavar='<tenant_id>',
           help='ID of tenant for which to list quota defaults.')
def do_quota_defaults(cs, args):
    """Lists default quotas for a tenant."""

    shell_utils.quota_show(cs.quotas.defaults(args.tenant))


@utils.arg('tenant',
           metavar='<tenant_id>',
           help='ID of tenant for which to set quotas.')
@utils.arg('--volumes',
           metavar='<volumes>',
           type=int, default=None,
           help='The new "volumes" quota value. Default=None.')
@utils.arg('--snapshots',
           metavar='<snapshots>',
           type=int, default=None,
           help='The new "snapshots" quota value. Default=None.')
@utils.arg('--gigabytes',
           metavar='<gigabytes>',
           type=int, default=None,
           help='The new "gigabytes" quota value. Default=None.')
@utils.arg('--backups',
           metavar='<backups>',
           type=int, default=None,
           help='The new "backups" quota value. Default=None.')
@utils.arg('--backup-gigabytes',
           metavar='<backup_gigabytes>',
           type=int, default=None,
           help='The new "backup_gigabytes" quota value. Default=None.')
@utils.arg('--volume-type',
           metavar='<volume_type_name>',
           default=None,
           help='Volume type. Default=None.')
@utils.arg('--per-volume-gigabytes',
           metavar='<per_volume_gigabytes>',
           type=int, default=None,
           help='Set max volume size limit. Default=None.')
def do_quota_update(cs, args):
    """Updates quotas for a tenant."""

    shell_utils.quota_update(cs.quotas, args.tenant, args)


@utils.arg('tenant', metavar='<tenant_id>',
           help='UUID of tenant to delete the quotas for.')
def do_quota_delete(cs, args):
    """Delete the quotas for a tenant."""

    cs.quotas.delete(args.tenant)


@utils.arg('class_name',
           metavar='<class>',
           help='Name of quota class for which to list quotas.')
def do_quota_class_show(cs, args):
    """Lists quotas for a quota class."""

    shell_utils.quota_show(cs.quota_classes.get(args.class_name))


@utils.arg('class_name',
           metavar='<class_name>',
           help='Name of quota class for which to set quotas.')
@utils.arg('--volumes',
           metavar='<volumes>',
           type=int, default=None,
           help='The new "volumes" quota value. Default=None.')
@utils.arg('--snapshots',
           metavar='<snapshots>',
           type=int, default=None,
           help='The new "snapshots" quota value. Default=None.')
@utils.arg('--gigabytes',
           metavar='<gigabytes>',
           type=int, default=None,
           help='The new "gigabytes" quota value. Default=None.')
@utils.arg('--backups',
           metavar='<backups>',
           type=int, default=None,
           help='The new "backups" quota value. Default=None.')
@utils.arg('--backup-gigabytes',
           metavar='<backup_gigabytes>',
           type=int, default=None,
           help='The new "backup_gigabytes" quota value. Default=None.')
@utils.arg('--volume-type',
           metavar='<volume_type_name>',
           default=None,
           help='Volume type. Default=None.')
@utils.arg('--per-volume-gigabytes',
           metavar='<per_volume_gigabytes>',
           type=int, default=None,
           help='Set max volume size limit. Default=None.')
def do_quota_class_update(cs, args):
    """Updates quotas for a quota class."""

    shell_utils.quota_update(cs.quota_classes, args.class_name, args)


@utils.arg('tenant',
           metavar='<tenant_id>',
           nargs='?',
           default=None,
           help='Display information for a single tenant (Admin only).')
def do_absolute_limits(cs, args):
    """Lists absolute limits for a user."""
    limits = cs.limits.get(args.tenant).absolute
    columns = ['Name', 'Value']
    utils.print_list(limits, columns)


@utils.arg('tenant',
           metavar='<tenant_id>',
           nargs='?',
           default=None,
           help='Display information for a single tenant (Admin only).')
def do_rate_limits(cs, args):
    """Lists rate limits for a user."""
    limits = cs.limits.get(args.tenant).rate
    columns = ['Verb', 'URI', 'Value', 'Remain', 'Unit', 'Next_Available']
    utils.print_list(limits, columns)


@utils.arg('volume',
           metavar='<volume>',
           help='Name or ID of volume to snapshot.')
@utils.arg('--force',
           metavar='<True|False>',
           const=True,
           nargs='?',
           default=False,
           help='Enables or disables upload of '
           'a volume that is attached to an instance. '
           'Default=False. '
           'This option may not be supported by your cloud.')
@utils.arg('--container-format',
           metavar='<container-format>',
           default='bare',
           help='Container format type. '
                'Default is bare.')
@utils.arg('--container_format',
           help=argparse.SUPPRESS)
@utils.arg('--disk-format',
           metavar='<disk-format>',
           default='raw',
           help='Disk format type. '
                'Default is raw.')
@utils.arg('--disk_format',
           help=argparse.SUPPRESS)
@utils.arg('image_name',
           metavar='<image-name>',
           help='The new image name.')
@utils.arg('--image_name',
           help=argparse.SUPPRESS)
def do_upload_to_image(cs, args):
    """Uploads volume to Image Service as an image."""
    volume = utils.find_volume(cs, args.volume)
    shell_utils.print_volume_image(
        volume.upload_to_image(args.force,
                               args.image_name,
                               args.container_format,
                               args.disk_format))


@utils.arg('volume', metavar='<volume>', help='ID of volume to migrate.')
@utils.arg('host', metavar='<host>', help='Destination host. Takes the form: '
                                          'host@backend-name#pool')
@utils.arg('--force-host-copy', metavar='<True|False>',
           choices=['True', 'False'],
           required=False,
           const=True,
           nargs='?',
           default=False,
           help='Enables or disables generic host-based '
           'force-migration, which bypasses driver '
           'optimizations. Default=False.')
@utils.arg('--lock-volume', metavar='<True|False>',
           choices=['True', 'False'],
           required=False,
           const=True,
           nargs='?',
           default=False,
           help='Enables or disables the termination of volume migration '
           'caused by other commands. This option applies to the '
           'available volume. True means it locks the volume '
           'state and does not allow the migration to be aborted. The '
           'volume status will be in maintenance during the '
           'migration. False means it allows the volume migration '
           'to be aborted. The volume status is still in the original '
           'status. Default=False.')
def do_migrate(cs, args):
    """Migrates volume to a new host."""
    volume = utils.find_volume(cs, args.volume)
    try:
        volume.migrate_volume(args.host, args.force_host_copy,
                              args.lock_volume)
        print("Request to migrate volume %s has been accepted." % (volume.id))
    except Exception as e:
        print("Migration for volume %s failed: %s." % (volume.id,
                                                       six.text_type(e)))


@utils.arg('volume', metavar='<volume>',
           help='Name or ID of volume for which to modify type.')
@utils.arg('new_type', metavar='<volume-type>', help='New volume type.')
@utils.arg('--migration-policy', metavar='<never|on-demand>', required=False,
           choices=['never', 'on-demand'], default='never',
           help='Migration policy during retype of volume.')
def do_retype(cs, args):
    """Changes the volume type for a volume."""
    volume = utils.find_volume(cs, args.volume)
    volume.retype(args.new_type, args.migration_policy)


@utils.arg('volume', metavar='<volume>',
           help='Name or ID of volume to backup.')
@utils.arg('--container', metavar='<container>',
           default=None,
           help='Backup container name. Default=None.')
@utils.arg('--display-name',
           help=argparse.SUPPRESS)
@utils.arg('--name', metavar='<name>',
           default=None,
           help='Backup name. Default=None.')
@utils.arg('--display-description',
           help=argparse.SUPPRESS)
@utils.arg('--description',
           metavar='<description>',
           default=None,
           help='Backup description. Default=None.')
@utils.arg('--incremental',
           action='store_true',
           help='Incremental backup. Default=False.',
           default=False)
@utils.arg('--force',
           action='store_true',
           help='Allows or disallows backup of a volume '
           'when the volume is attached to an instance. '
           'If set to True, backs up the volume whether '
           'its status is "available" or "in-use". The backup '
           'of an "in-use" volume means your data is crash '
           'consistent. Default=False.',
           default=False)
@utils.arg('--snapshot-id',
           metavar='<snapshot-id>',
           default=None,
           help='ID of snapshot to backup. Default=None.')
def do_backup_create(cs, args):
    """Creates a volume backup."""
    if args.display_name is not None:
        args.name = args.display_name

    if args.display_description is not None:
        args.description = args.display_description

    volume = utils.find_volume(cs, args.volume)
    backup = cs.backups.create(volume.id,
                               args.container,
                               args.name,
                               args.description,
                               args.incremental,
                               args.force,
                               args.snapshot_id)

    info = {"volume_id": volume.id}
    info.update(backup._info)

    if 'links' in info:
        info.pop('links')

    utils.print_dict(info)


@utils.arg('backup', metavar='<backup>', help='Name or ID of backup.')
def do_backup_show(cs, args):
    """Shows backup details."""
    backup = shell_utils.find_backup(cs, args.backup)
    info = dict()
    info.update(backup._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('--all-tenants',
           metavar='<all_tenants>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Filters results by a name. Default=None.')
@utils.arg('--status',
           metavar='<status>',
           default=None,
           help='Filters results by a status. Default=None.')
@utils.arg('--volume-id',
           metavar='<volume-id>',
           default=None,
           help='Filters results by a volume ID. Default=None.')
@utils.arg('--volume_id',
           help=argparse.SUPPRESS)
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning backups that appear later in the backup '
                'list than that represented by this id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of backups to return. Default=None.')
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
def do_backup_list(cs, args):
    """Lists all backups."""

    search_opts = {
        'all_tenants': args.all_tenants,
        'name': args.name,
        'status': args.status,
        'volume_id': args.volume_id,
    }

    backups = cs.backups.list(search_opts=search_opts,
                              marker=args.marker,
                              limit=args.limit,
                              sort=args.sort)
    shell_utils.translate_volume_snapshot_keys(backups)
    columns = ['ID', 'Volume ID', 'Status', 'Name', 'Size', 'Object Count',
               'Container']
    if args.sort:
        sortby_index = None
    else:
        sortby_index = 0
    utils.print_list(backups, columns, sortby_index=sortby_index)


@utils.arg('--force',
           action="store_true",
           help='Allows deleting backup of a volume '
           'when its status is other than "available" or "error". '
           'Default=False.')
@utils.arg('backup', metavar='<backup>', nargs='+',
           help='Name or ID of backup(s) to delete.')
def do_backup_delete(cs, args):
    """Removes one or more backups."""
    failure_count = 0
    for backup in args.backup:
        try:
            shell_utils.find_backup(cs, backup).delete(args.force)
            print("Request to delete backup %s has been accepted." % (backup))
        except Exception as e:
            failure_count += 1
            print("Delete for backup %s failed: %s" % (backup, e))
    if failure_count == len(args.backup):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "backups.")


@utils.arg('backup', metavar='<backup>',
           help='Name or ID of backup to restore.')
@utils.arg('--volume-id', metavar='<volume>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--volume', metavar='<volume>',
           default=None,
           help='Name or ID of existing volume to which to restore. '
           'This is mutually exclusive with --name and takes priority. '
           'Default=None.')
@utils.arg('--name', metavar='<name>',
           default=None,
           help='Use the name for new volume creation to restore. '
           'This is mutually exclusive with --volume (or the deprecated '
           '--volume-id) and --volume (or --volume-id) takes priority. '
           'Default=None.')
def do_backup_restore(cs, args):
    """Restores a backup."""
    vol = args.volume or args.volume_id
    if vol:
        volume_id = utils.find_volume(cs, vol).id
        if args.name:
            args.name = None
            print('Mutually exclusive options are specified simultaneously: '
                  '"--volume (or the deprecated --volume-id) and --name". '
                  'The --volume (or --volume-id) option takes priority.')
    else:
        volume_id = None

    backup = shell_utils.find_backup(cs, args.backup)
    restore = cs.restores.restore(backup.id, volume_id, args.name)

    info = {"backup_id": backup.id}
    info.update(restore._info)

    info.pop('links', None)

    utils.print_dict(info)


@utils.arg('backup', metavar='<backup>',
           help='ID of the backup to export.')
def do_backup_export(cs, args):
    """Export backup metadata record."""
    info = cs.backups.export_record(args.backup)
    utils.print_dict(info)


@utils.arg('backup_service', metavar='<backup_service>',
           help='Backup service to use for importing the backup.')
@utils.arg('backup_url', metavar='<backup_url>',
           help='Backup URL for importing the backup metadata.')
def do_backup_import(cs, args):
    """Import backup metadata record."""
    info = cs.backups.import_record(args.backup_service, args.backup_url)
    info.pop('links', None)

    utils.print_dict(info)


@utils.arg('backup', metavar='<backup>', nargs='+',
           help='Name or ID of the backup to modify.')
@utils.arg('--state', metavar='<state>',
           default='available',
           help='The state to assign to the backup. Valid values are '
                '"available", "error". Default=available.')
def do_backup_reset_state(cs, args):
    """Explicitly updates the backup state."""
    failure_count = 0

    single = (len(args.backup) == 1)

    for backup in args.backup:
        try:
            shell_utils.find_backup(cs, backup).reset_state(args.state)
            print("Request to update backup '%s' has been accepted." % backup)
        except Exception as e:
            failure_count += 1
            msg = "Reset state for backup %s failed: %s" % (backup, e)
            if not single:
                print(msg)

    if failure_count == len(args.backup):
        if not single:
            msg = ("Unable to reset the state for any of the specified "
                   "backups.")
        raise exceptions.CommandError(msg)


@utils.arg('volume', metavar='<volume>',
           help='Name or ID of volume to transfer.')
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Transfer name. Default=None.')
@utils.arg('--display-name',
           help=argparse.SUPPRESS)
def do_transfer_create(cs, args):
    """Creates a volume transfer."""
    if args.display_name is not None:
        args.name = args.display_name

    volume = utils.find_volume(cs, args.volume)
    transfer = cs.transfers.create(volume.id,
                                   args.name)
    info = dict()
    info.update(transfer._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('transfer', metavar='<transfer>',
           help='Name or ID of transfer to delete.')
def do_transfer_delete(cs, args):
    """Undoes a transfer."""
    transfer = shell_utils.find_transfer(cs, args.transfer)
    transfer.delete()


@utils.arg('transfer', metavar='<transfer>',
           help='ID of transfer to accept.')
@utils.arg('auth_key', metavar='<auth_key>',
           help='Authentication key of transfer to accept.')
def do_transfer_accept(cs, args):
    """Accepts a volume transfer."""
    transfer = cs.transfers.accept(args.transfer, args.auth_key)
    info = dict()
    info.update(transfer._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
def do_transfer_list(cs, args):
    """Lists all transfers."""
    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
    }
    transfers = cs.transfers.list(search_opts=search_opts)
    columns = ['ID', 'Volume ID', 'Name']
    utils.print_list(transfers, columns)


@utils.arg('transfer', metavar='<transfer>',
           help='Name or ID of transfer to accept.')
def do_transfer_show(cs, args):
    """Shows transfer details."""
    transfer = shell_utils.find_transfer(cs, args.transfer)
    info = dict()
    info.update(transfer._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('volume', metavar='<volume>',
           help='Name or ID of volume to extend.')
@utils.arg('new_size',
           metavar='<new_size>',
           type=int,
           help='New size of volume, in GiBs.')
def do_extend(cs, args):
    """Attempts to extend size of an existing volume."""
    volume = utils.find_volume(cs, args.volume)
    cs.volumes.extend(volume, args.new_size)


@utils.arg('--host', metavar='<hostname>', default=None,
           help='Host name. Default=None.')
@utils.arg('--binary', metavar='<binary>', default=None,
           help='Service binary. Default=None.')
@utils.arg('--withreplication',
           metavar='<True|False>',
           const=True,
           nargs='?',
           default=False,
           help='Enables or disables display of '
                'Replication info for c-vol services. Default=False.')
def do_service_list(cs, args):
    """Lists all services. Filter by host and service binary."""
    replication = strutils.bool_from_string(args.withreplication,
                                            strict=True)
    result = cs.services.list(host=args.host, binary=args.binary)
    columns = ["Binary", "Host", "Zone", "Status", "State", "Updated_at"]
    if replication:
        columns.extend(["Replication Status", "Active Backend ID", "Frozen"])
    # NOTE(jay-lau-513): we check if the response has disabled_reason
    # so as not to add the column when the extended ext is not enabled.
    if result and hasattr(result[0], 'disabled_reason'):
        columns.append("Disabled Reason")
    utils.print_list(result, columns)


@utils.arg('host', metavar='<hostname>', help='Host name.')
@utils.arg('binary', metavar='<binary>', help='Service binary.')
def do_service_enable(cs, args):
    """Enables the service."""
    result = cs.services.enable(args.host, args.binary)
    columns = ["Host", "Binary", "Status"]
    utils.print_list([result], columns)


@utils.arg('host', metavar='<hostname>', help='Host name.')
@utils.arg('binary', metavar='<binary>', help='Service binary.')
@utils.arg('--reason', metavar='<reason>',
           help='Reason for disabling service.')
def do_service_disable(cs, args):
    """Disables the service."""
    columns = ["Host", "Binary", "Status"]
    if args.reason:
        columns.append('Disabled Reason')
        result = cs.services.disable_log_reason(args.host, args.binary,
                                                args.reason)
    else:
        result = cs.services.disable(args.host, args.binary)
    utils.print_list([result], columns)


def treeizeAvailabilityZone(zone):
    """Builds a tree view for availability zones."""
    AvailabilityZone = availability_zones.AvailabilityZone

    az = AvailabilityZone(zone.manager,
                          copy.deepcopy(zone._info), zone._loaded)
    result = []

    # Zone tree view item
    az.zoneName = zone.zoneName
    az.zoneState = ('available'
                    if zone.zoneState['available'] else 'not available')
    az._info['zoneName'] = az.zoneName
    az._info['zoneState'] = az.zoneState
    result.append(az)

    if getattr(zone, "hosts", None) and zone.hosts is not None:
        for (host, services) in zone.hosts.items():
            # Host tree view item
            az = AvailabilityZone(zone.manager,
                                  copy.deepcopy(zone._info), zone._loaded)
            az.zoneName = '|- %s' % host
            az.zoneState = ''
            az._info['zoneName'] = az.zoneName
            az._info['zoneState'] = az.zoneState
            result.append(az)

            for (svc, state) in services.items():
                # Service tree view item
                az = AvailabilityZone(zone.manager,
                                      copy.deepcopy(zone._info), zone._loaded)
                az.zoneName = '| |- %s' % svc
                az.zoneState = '%s %s %s' % (
                               'enabled' if state['active'] else 'disabled',
                               ':-)' if state['available'] else 'XXX',
                               state['updated_at'])
                az._info['zoneName'] = az.zoneName
                az._info['zoneState'] = az.zoneState
                result.append(az)
    return result


def do_availability_zone_list(cs, _args):
    """Lists all availability zones."""
    try:
        availability_zones = cs.availability_zones.list()
    except exceptions.Forbidden:  # policy doesn't allow probably
        try:
            availability_zones = cs.availability_zones.list(detailed=False)
        except Exception:
            raise

    result = []
    for zone in availability_zones:
        result += treeizeAvailabilityZone(zone)
    shell_utils.translate_availability_zone_keys(result)
    utils.print_list(result, ['Name', 'Status'])


def do_encryption_type_list(cs, args):
    """Shows encryption type details for volume types. Admin only."""
    result = cs.volume_encryption_types.list()
    utils.print_list(result, ['Volume Type ID', 'Provider', 'Cipher',
                              'Key Size', 'Control Location'])


@utils.arg('volume_type',
           metavar='<volume_type>',
           type=str,
           help='Name or ID of volume type.')
def do_encryption_type_show(cs, args):
    """Shows encryption type details for a volume type. Admin only."""
    volume_type = shell_utils.find_volume_type(cs, args.volume_type)

    result = cs.volume_encryption_types.get(volume_type)

    # Display result or an empty table if no result
    if hasattr(result, 'volume_type_id'):
        shell_utils.print_volume_encryption_type_list([result])
    else:
        shell_utils.print_volume_encryption_type_list([])


@utils.arg('volume_type',
           metavar='<volume_type>',
           type=str,
           help='Name or ID of volume type.')
@utils.arg('provider',
           metavar='<provider>',
           type=str,
           help='The encryption provider format. '
                'For example, "luks" or "plain".')
@utils.arg('--cipher',
           metavar='<cipher>',
           type=str,
           required=False,
           default=None,
           help='The encryption algorithm or mode. '
                'For example, aes-xts-plain64. Default=None.')
@utils.arg('--key-size',
           metavar='<key_size>',
           type=int,
           required=False,
           default=None,
           help='Size of encryption key, in bits. '
                'For example, 128 or 256. Default=None.')
@utils.arg('--key_size',
           type=int,
           required=False,
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--control-location',
           metavar='<control_location>',
           choices=['front-end', 'back-end'],
           type=str,
           required=False,
           default='front-end',
           help='Notional service where encryption is performed. '
                'Valid values are "front-end" or "back-end". '
                'For example, front-end=Nova. Default is "front-end".')
@utils.arg('--control_location',
           type=str,
           required=False,
           default='front-end',
           help=argparse.SUPPRESS)
def do_encryption_type_create(cs, args):
    """Creates encryption type for a volume type. Admin only."""
    volume_type = shell_utils.find_volume_type(cs, args.volume_type)

    body = {
        'provider': args.provider,
        'cipher': args.cipher,
        'key_size': args.key_size,
        'control_location': args.control_location
    }

    result = cs.volume_encryption_types.create(volume_type, body)
    shell_utils.print_volume_encryption_type_list([result])


@utils.arg('volume_type',
           metavar='<volume-type>',
           type=str,
           help="Name or ID of the volume type")
@utils.arg('--provider',
           metavar='<provider>',
           type=str,
           required=False,
           default=argparse.SUPPRESS,
           help="Encryption provider format (e.g. 'luks' or 'plain').")
@utils.arg('--cipher',
           metavar='<cipher>',
           type=str,
           nargs='?',
           required=False,
           default=argparse.SUPPRESS,
           const=None,
           help="Encryption algorithm/mode to use (e.g., aes-xts-plain64). "
           "Provide parameter without value to set to provider default.")
@utils.arg('--key-size',
           dest='key_size',
           metavar='<key-size>',
           type=int,
           nargs='?',
           required=False,
           default=argparse.SUPPRESS,
           const=None,
           help="Size of the encryption key, in bits (e.g., 128, 256). "
           "Provide parameter without value to set to provider default. ")
@utils.arg('--control-location',
           dest='control_location',
           metavar='<control-location>',
           choices=['front-end', 'back-end'],
           type=str,
           required=False,
           default=argparse.SUPPRESS,
           help="Notional service where encryption is performed (e.g., "
           "front-end=Nova). Values: 'front-end', 'back-end'")
def do_encryption_type_update(cs, args):
    """Update encryption type information for a volume type (Admin Only)."""
    volume_type = shell_utils.find_volume_type(cs, args.volume_type)

    # An argument should only be pulled if the user specified the parameter.
    body = {}
    for attr in ['provider', 'cipher', 'key_size', 'control_location']:
        if hasattr(args, attr):
            body[attr] = getattr(args, attr)

    cs.volume_encryption_types.update(volume_type, body)
    result = cs.volume_encryption_types.get(volume_type)
    shell_utils.print_volume_encryption_type_list([result])


@utils.arg('volume_type',
           metavar='<volume_type>',
           type=str,
           help='Name or ID of volume type.')
def do_encryption_type_delete(cs, args):
    """Deletes encryption type for a volume type. Admin only."""
    volume_type = shell_utils.find_volume_type(cs, args.volume_type)
    cs.volume_encryption_types.delete(volume_type)


@utils.arg('name',
           metavar='<name>',
           help='Name of new QoS specifications.')
@utils.arg('metadata',
           metavar='<key=value>',
           nargs='+',
           default=[],
           help='QoS specifications.')
def do_qos_create(cs, args):
    """Creates a qos specs."""
    keypair = None
    if args.metadata is not None:
        keypair = shell_utils.extract_metadata(args)
    qos_specs = cs.qos_specs.create(args.name, keypair)
    shell_utils.print_qos_specs(qos_specs)


def do_qos_list(cs, args):
    """Lists qos specs."""
    qos_specs = cs.qos_specs.list()
    shell_utils.print_qos_specs_list(qos_specs)


@utils.arg('qos_specs', metavar='<qos_specs>',
           help='ID of QoS specifications to show.')
def do_qos_show(cs, args):
    """Shows qos specs details."""
    qos_specs = shell_utils.find_qos_specs(cs, args.qos_specs)
    shell_utils.print_qos_specs(qos_specs)


@utils.arg('qos_specs', metavar='<qos_specs>',
           help='ID of QoS specifications to delete.')
@utils.arg('--force',
           metavar='<True|False>',
           const=True,
           nargs='?',
           default=False,
           help='Enables or disables deletion of in-use '
                'QoS specifications. Default=False.')
def do_qos_delete(cs, args):
    """Deletes a specified qos specs."""
    force = strutils.bool_from_string(args.force,
                                      strict=True)
    qos_specs = shell_utils.find_qos_specs(cs, args.qos_specs)
    cs.qos_specs.delete(qos_specs, force)


@utils.arg('qos_specs', metavar='<qos_specs>',
           help='ID of QoS specifications.')
@utils.arg('vol_type_id', metavar='<volume_type_id>',
           help='ID of volume type with which to associate '
                'QoS specifications.')
def do_qos_associate(cs, args):
    """Associates qos specs with specified volume type."""
    cs.qos_specs.associate(args.qos_specs, args.vol_type_id)


@utils.arg('qos_specs', metavar='<qos_specs>',
           help='ID of QoS specifications.')
@utils.arg('vol_type_id', metavar='<volume_type_id>',
           help='ID of volume type with which to associate '
                'QoS specifications.')
def do_qos_disassociate(cs, args):
    """Disassociates qos specs from specified volume type."""
    cs.qos_specs.disassociate(args.qos_specs, args.vol_type_id)


@utils.arg('qos_specs', metavar='<qos_specs>',
           help='ID of QoS specifications on which to operate.')
def do_qos_disassociate_all(cs, args):
    """Disassociates qos specs from all its associations."""
    cs.qos_specs.disassociate_all(args.qos_specs)


@utils.arg('qos_specs', metavar='<qos_specs>',
           help='ID of QoS specifications.')
@utils.arg('action',
           metavar='<action>',
           choices=['set', 'unset'],
           help='The action. Valid values are "set" or "unset."')
@utils.arg('metadata', metavar='key=value',
           nargs='+',
           default=[],
           help='Metadata key and value pair to set or unset. '
                'For unset, specify only the key.')
def do_qos_key(cs, args):
    """Sets or unsets specifications for a qos spec."""
    keypair = shell_utils.extract_metadata(args)

    if args.action == 'set':
        cs.qos_specs.set_keys(args.qos_specs, keypair)
    elif args.action == 'unset':
        cs.qos_specs.unset_keys(args.qos_specs, list(keypair))


@utils.arg('qos_specs', metavar='<qos_specs>',
           help='ID of QoS specifications.')
def do_qos_get_association(cs, args):
    """Lists all associations for specified qos specs."""
    associations = cs.qos_specs.get_associations(args.qos_specs)
    shell_utils.print_associations_list(associations)


@utils.arg('snapshot',
           metavar='<snapshot>',
           help='ID of snapshot for which to update metadata.')
@utils.arg('action',
           metavar='<action>',
           choices=['set', 'unset'],
           help='The action. Valid values are "set" or "unset."')
@utils.arg('metadata',
           metavar='<key=value>',
           nargs='+',
           default=[],
           help='Metadata key and value pair to set or unset. '
                'For unset, specify only the key.')
def do_snapshot_metadata(cs, args):
    """Sets or deletes snapshot metadata."""
    snapshot = shell_utils.find_volume_snapshot(cs, args.snapshot)
    metadata = shell_utils.extract_metadata(args)

    if args.action == 'set':
        metadata = snapshot.set_metadata(metadata)
        utils.print_dict(metadata._info)
    elif args.action == 'unset':
        snapshot.delete_metadata(list(metadata.keys()))


@utils.arg('snapshot', metavar='<snapshot>',
           help='ID of snapshot.')
def do_snapshot_metadata_show(cs, args):
    """Shows snapshot metadata."""
    snapshot = shell_utils.find_volume_snapshot(cs, args.snapshot)
    utils.print_dict(snapshot._info['metadata'], 'Metadata-property')


@utils.arg('volume', metavar='<volume>',
           help='ID of volume.')
def do_metadata_show(cs, args):
    """Shows volume metadata."""
    volume = utils.find_volume(cs, args.volume)
    utils.print_dict(volume._info['metadata'], 'Metadata-property')


@utils.arg('volume', metavar='<volume>',
           help='ID of volume.')
def do_image_metadata_show(cs, args):
    """Shows volume image metadata."""
    volume = utils.find_volume(cs, args.volume)
    resp, body = volume.show_image_metadata(volume)
    utils.print_dict(body['metadata'], 'Metadata-property')


@utils.arg('volume',
           metavar='<volume>',
           help='ID of volume for which to update metadata.')
@utils.arg('metadata',
           metavar='<key=value>',
           nargs='+',
           default=[],
           help='Metadata key and value pair or pairs to update.')
def do_metadata_update_all(cs, args):
    """Updates volume metadata."""
    volume = utils.find_volume(cs, args.volume)
    metadata = shell_utils.extract_metadata(args)
    metadata = volume.update_all_metadata(metadata)
    utils.print_dict(metadata['metadata'], 'Metadata-property')


@utils.arg('snapshot',
           metavar='<snapshot>',
           help='ID of snapshot for which to update metadata.')
@utils.arg('metadata',
           metavar='<key=value>',
           nargs='+',
           default=[],
           help='Metadata key and value pair to update.')
def do_snapshot_metadata_update_all(cs, args):
    """Updates snapshot metadata."""
    snapshot = shell_utils.find_volume_snapshot(cs, args.snapshot)
    metadata = shell_utils.extract_metadata(args)
    metadata = snapshot.update_all_metadata(metadata)
    utils.print_dict(metadata)


@utils.arg('volume', metavar='<volume>', help='ID of volume to update.')
@utils.arg('read_only',
           metavar='<True|true|False|false>',
           choices=['True', 'true', 'False', 'false'],
           help='Enables or disables update of volume to '
                'read-only access mode.')
def do_readonly_mode_update(cs, args):
    """Updates volume read-only access-mode flag."""
    volume = utils.find_volume(cs, args.volume)
    cs.volumes.update_readonly_flag(volume,
                                    strutils.bool_from_string(args.read_only,
                                                              strict=True))


@utils.arg('volume', metavar='<volume>', help='ID of the volume to update.')
@utils.arg('bootable',
           metavar='<True|true|False|false>',
           choices=['True', 'true', 'False', 'false'],
           help='Flag to indicate whether volume is bootable.')
def do_set_bootable(cs, args):
    """Update bootable status of a volume."""
    volume = utils.find_volume(cs, args.volume)
    cs.volumes.set_bootable(volume,
                            strutils.bool_from_string(args.bootable,
                                                      strict=True))


@utils.arg('host',
           metavar='<host>',
           help='Cinder host on which the existing volume resides; '
                'takes the form: host@backend-name#pool')
@utils.arg('identifier',
           metavar='<identifier>',
           help='Name or other Identifier for existing volume')
@utils.arg('--id-type',
           metavar='<id-type>',
           default='source-name',
           help='Type of backend device identifier provided, '
                'typically source-name or source-id (Default=source-name)')
@utils.arg('--name',
           metavar='<name>',
           help='Volume name (Default=None)')
@utils.arg('--description',
           metavar='<description>',
           help='Volume description (Default=None)')
@utils.arg('--volume-type',
           metavar='<volume-type>',
           help='Volume type (Default=None)')
@utils.arg('--availability-zone',
           metavar='<availability-zone>',
           help='Availability zone for volume (Default=None)')
@utils.arg('--metadata',
           nargs='*',
           metavar='<key=value>',
           help='Metadata key=value pairs (Default=None)')
@utils.arg('--bootable',
           action='store_true',
           help='Specifies that the newly created volume should be'
                ' marked as bootable')
def do_manage(cs, args):
    """Manage an existing volume."""
    volume_metadata = None
    if args.metadata is not None:
        volume_metadata = shell_utils.extract_metadata(args)

    # Build a dictionary of key/value pairs to pass to the API.
    ref_dict = {args.id_type: args.identifier}

    # The recommended way to specify an existing volume is by ID or name, and
    # have the Cinder driver look for 'source-name' or 'source-id' elements in
    # the ref structure.  To make things easier for the user, we have special
    # --source-name and --source-id CLI options that add the appropriate
    # element to the ref structure.
    #
    # Note how argparse converts hyphens to underscores.  We use hyphens in the
    # dictionary so that it is consistent with what the user specified on the
    # CLI.

    if hasattr(args, 'source_name') and args.source_name is not None:
        ref_dict['source-name'] = args.source_name
    if hasattr(args, 'source_id') and args.source_id is not None:
        ref_dict['source-id'] = args.source_id

    volume = cs.volumes.manage(host=args.host,
                               ref=ref_dict,
                               name=args.name,
                               description=args.description,
                               volume_type=args.volume_type,
                               availability_zone=args.availability_zone,
                               metadata=volume_metadata,
                               bootable=args.bootable)

    info = {}
    volume = cs.volumes.get(volume.id)
    info.update(volume._info)
    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('volume', metavar='<volume>',
           help='Name or ID of the volume to unmanage.')
def do_unmanage(cs, args):
    """Stop managing a volume."""
    volume = utils.find_volume(cs, args.volume)
    cs.volumes.unmanage(volume.id)


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
def do_consisgroup_list(cs, args):
    """Lists all consistency groups."""
    consistencygroups = cs.consistencygroups.list()

    columns = ['ID', 'Status', 'Name']
    utils.print_list(consistencygroups, columns)


@utils.arg('consistencygroup',
           metavar='<consistencygroup>',
           help='Name or ID of a consistency group.')
def do_consisgroup_show(cs, args):
    """Shows details of a consistency group."""
    info = dict()
    consistencygroup = shell_utils.find_consistencygroup(cs,
                                                         args.consistencygroup)
    info.update(consistencygroup._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('volumetypes',
           metavar='<volume-types>',
           help='Volume types.')
@utils.arg('--name',
           metavar='<name>',
           help='Name of a consistency group.')
@utils.arg('--description',
           metavar='<description>',
           default=None,
           help='Description of a consistency group. Default=None.')
@utils.arg('--availability-zone',
           metavar='<availability-zone>',
           default=None,
           help='Availability zone for volume. Default=None.')
def do_consisgroup_create(cs, args):
    """Creates a consistency group."""

    consistencygroup = cs.consistencygroups.create(
        args.volumetypes,
        args.name,
        args.description,
        availability_zone=args.availability_zone)

    info = dict()
    consistencygroup = cs.consistencygroups.get(consistencygroup.id)
    info.update(consistencygroup._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('--cgsnapshot',
           metavar='<cgsnapshot>',
           help='Name or ID of a cgsnapshot. Default=None.')
@utils.arg('--source-cg',
           metavar='<source-cg>',
           help='Name or ID of a source CG. Default=None.')
@utils.arg('--name',
           metavar='<name>',
           help='Name of a consistency group. Default=None.')
@utils.arg('--description',
           metavar='<description>',
           help='Description of a consistency group. Default=None.')
def do_consisgroup_create_from_src(cs, args):
    """Creates a consistency group from a cgsnapshot or a source CG."""
    if not args.cgsnapshot and not args.source_cg:
        msg = ('Cannot create consistency group because neither '
               'cgsnapshot nor source CG is provided.')
        raise exceptions.ClientException(code=1, message=msg)
    if args.cgsnapshot and args.source_cg:
        msg = ('Cannot create consistency group because both '
               'cgsnapshot and source CG are provided.')
        raise exceptions.ClientException(code=1, message=msg)
    cgsnapshot = None
    if args.cgsnapshot:
        cgsnapshot = shell_utils.find_cgsnapshot(cs, args.cgsnapshot)
    source_cg = None
    if args.source_cg:
        source_cg = shell_utils.find_consistencygroup(cs, args.source_cg)
    info = cs.consistencygroups.create_from_src(
        cgsnapshot.id if cgsnapshot else None,
        source_cg.id if source_cg else None,
        args.name,
        args.description)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('consistencygroup',
           metavar='<consistencygroup>', nargs='+',
           help='Name or ID of one or more consistency groups '
                'to be deleted.')
@utils.arg('--force',
           action='store_true',
           default=False,
           help='Allows or disallows consistency groups '
                'to be deleted. If the consistency group is empty, '
                'it can be deleted without the force flag. '
                'If the consistency group is not empty, the force '
                'flag is required for it to be deleted.')
def do_consisgroup_delete(cs, args):
    """Removes one or more consistency groups."""
    failure_count = 0
    for consistencygroup in args.consistencygroup:
        try:
            shell_utils.find_consistencygroup(
                cs, consistencygroup).delete(args.force)
        except Exception as e:
            failure_count += 1
            print("Delete for consistency group %s failed: %s" %
                  (consistencygroup, e))
    if failure_count == len(args.consistencygroup):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "consistency groups.")


@utils.arg('consistencygroup',
           metavar='<consistencygroup>',
           help='Name or ID of a consistency group.')
@utils.arg('--name', metavar='<name>',
           help='New name for consistency group. Default=None.')
@utils.arg('--description', metavar='<description>',
           help='New description for consistency group. Default=None.')
@utils.arg('--add-volumes',
           metavar='<uuid1,uuid2,......>',
           help='UUID of one or more volumes '
                'to be added to the consistency group, '
                'separated by commas. Default=None.')
@utils.arg('--remove-volumes',
           metavar='<uuid3,uuid4,......>',
           help='UUID of one or more volumes '
                'to be removed from the consistency group, '
                'separated by commas. Default=None.')
def do_consisgroup_update(cs, args):
    """Updates a consistency group."""
    kwargs = {}

    if args.name is not None:
        kwargs['name'] = args.name

    if args.description is not None:
        kwargs['description'] = args.description

    if args.add_volumes is not None:
        kwargs['add_volumes'] = args.add_volumes

    if args.remove_volumes is not None:
        kwargs['remove_volumes'] = args.remove_volumes

    if not kwargs:
        msg = ('At least one of the following args must be supplied: '
               'name, description, add-volumes, remove-volumes.')
        raise exceptions.ClientException(code=1, message=msg)

    shell_utils.find_consistencygroup(
        cs, args.consistencygroup).update(**kwargs)
    print("Request to update consistency group '%s' has been accepted." % (
        args.consistencygroup))


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--status',
           metavar='<status>',
           default=None,
           help='Filters results by a status. Default=None.')
@utils.arg('--consistencygroup-id',
           metavar='<consistencygroup_id>',
           default=None,
           help='Filters results by a consistency group ID. Default=None.')
def do_cgsnapshot_list(cs, args):
    """Lists all cgsnapshots."""

    all_tenants = int(os.environ.get("ALL_TENANTS", args.all_tenants))

    search_opts = {
        'all_tenants': all_tenants,
        'status': args.status,
        'consistencygroup_id': args.consistencygroup_id,
    }

    cgsnapshots = cs.cgsnapshots.list(search_opts=search_opts)

    columns = ['ID', 'Status', 'Name']
    utils.print_list(cgsnapshots, columns)


@utils.arg('cgsnapshot',
           metavar='<cgsnapshot>',
           help='Name or ID of cgsnapshot.')
def do_cgsnapshot_show(cs, args):
    """Shows cgsnapshot details."""
    info = dict()
    cgsnapshot = shell_utils.find_cgsnapshot(cs, args.cgsnapshot)
    info.update(cgsnapshot._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('consistencygroup',
           metavar='<consistencygroup>',
           help='Name or ID of a consistency group.')
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Cgsnapshot name. Default=None.')
@utils.arg('--description',
           metavar='<description>',
           default=None,
           help='Cgsnapshot description. Default=None.')
def do_cgsnapshot_create(cs, args):
    """Creates a cgsnapshot."""
    consistencygroup = shell_utils.find_consistencygroup(cs,
                                                         args.consistencygroup)
    cgsnapshot = cs.cgsnapshots.create(
        consistencygroup.id,
        args.name,
        args.description)

    info = dict()
    cgsnapshot = cs.cgsnapshots.get(cgsnapshot.id)
    info.update(cgsnapshot._info)

    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('cgsnapshot',
           metavar='<cgsnapshot>', nargs='+',
           help='Name or ID of one or more cgsnapshots to be deleted.')
def do_cgsnapshot_delete(cs, args):
    """Removes one or more cgsnapshots."""
    failure_count = 0
    for cgsnapshot in args.cgsnapshot:
        try:
            shell_utils.find_cgsnapshot(cs, cgsnapshot).delete()
        except Exception as e:
            failure_count += 1
            print("Delete for cgsnapshot %s failed: %s" % (cgsnapshot, e))
    if failure_count == len(args.cgsnapshot):
        raise exceptions.CommandError("Unable to delete any of the specified "
                                      "cgsnapshots.")


@utils.arg('--detail',
           action='store_true',
           help='Show detailed information about pools.')
def do_get_pools(cs, args):
    """Show pool information for backends. Admin only."""
    pools = cs.volumes.get_pools(args.detail)
    infos = dict()
    infos.update(pools._info)

    for info in infos['pools']:
        backend = dict()
        backend['name'] = info['name']
        if args.detail:
            backend.update(info['capabilities'])
        utils.print_dict(backend)


@utils.arg('host',
           metavar='<host>',
           help='Cinder host to show backend volume stats and properties; '
                'takes the form: host@backend-name')
def do_get_capabilities(cs, args):
    """Show backend volume stats and properties. Admin only."""

    capabilities = cs.capabilities.get(args.host)
    infos = dict()
    infos.update(capabilities._info)

    prop = infos.pop('properties', None)
    utils.print_dict(infos, "Volume stats")
    utils.print_dict(prop, "Backend properties",
                     formatters=sorted(prop.keys()))


@utils.arg('volume',
           metavar='<volume>',
           help='Cinder volume that already exists in the volume backend.')
@utils.arg('identifier',
           metavar='<identifier>',
           help='Name or other identifier for existing snapshot. This is '
                'backend specific.')
@utils.arg('--id-type',
           metavar='<id-type>',
           default='source-name',
           help='Type of backend device identifier provided, '
                'typically source-name or source-id (Default=source-name).')
@utils.arg('--name',
           metavar='<name>',
           help='Snapshot name (Default=None).')
@utils.arg('--description',
           metavar='<description>',
           help='Snapshot description (Default=None).')
@utils.arg('--metadata',
           nargs='*',
           metavar='<key=value>',
           help='Metadata key=value pairs (Default=None).')
def do_snapshot_manage(cs, args):
    """Manage an existing snapshot."""
    snapshot_metadata = None
    if args.metadata is not None:
        snapshot_metadata = shell_utils.extract_metadata(args)

    # Build a dictionary of key/value pairs to pass to the API.
    ref_dict = {args.id_type: args.identifier}

    if hasattr(args, 'source_name') and args.source_name is not None:
        ref_dict['source-name'] = args.source_name
    if hasattr(args, 'source_id') and args.source_id is not None:
        ref_dict['source-id'] = args.source_id

    volume = utils.find_volume(cs, args.volume)
    snapshot = cs.volume_snapshots.manage(volume_id=volume.id,
                                          ref=ref_dict,
                                          name=args.name,
                                          description=args.description,
                                          metadata=snapshot_metadata)

    info = {}
    snapshot = cs.volume_snapshots.get(snapshot.id)
    info.update(snapshot._info)
    info.pop('links', None)
    utils.print_dict(info)


@utils.arg('snapshot', metavar='<snapshot>',
           help='Name or ID of the snapshot to unmanage.')
def do_snapshot_unmanage(cs, args):
    """Stop managing a snapshot."""
    snapshot = shell_utils.find_volume_snapshot(cs, args.snapshot)
    cs.volume_snapshots.unmanage(snapshot.id)


@utils.arg('host', metavar='<hostname>', help='Host name.')
def do_freeze_host(cs, args):
    """Freeze and disable the specified cinder-volume host."""
    cs.services.freeze_host(args.host)


@utils.arg('host', metavar='<hostname>', help='Host name.')
def do_thaw_host(cs, args):
    """Thaw and enable the specified cinder-volume host."""
    cs.services.thaw_host(args.host)


@utils.arg('host', metavar='<hostname>', help='Host name.')
@utils.arg('--backend_id',
           metavar='<backend-id>',
           help='ID of backend to failover to (Default=None)')
def do_failover_host(cs, args):
    """Failover a replicating cinder-volume host."""
    cs.services.failover_host(args.host, args.backend_id)


@utils.arg('host',
           metavar='<host>',
           help='Cinder host on which to list manageable volumes; '
                'takes the form: host@backend-name#pool')
@utils.arg('--detailed',
           metavar='<detailed>',
           default=True,
           help='Returned detailed information (default true).')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning volumes that appear later in the volume '
                'list than that represented by this volume id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of volumes to return. Default=None.')
@utils.arg('--offset',
           metavar='<offset>',
           default=None,
           help='Number of volumes to skip after marker. Default=None.')
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
def do_manageable_list(cs, args):
    """Lists all manageable volumes."""
    detailed = strutils.bool_from_string(args.detailed)
    volumes = cs.volumes.list_manageable(host=args.host, detailed=detailed,
                                         marker=args.marker, limit=args.limit,
                                         offset=args.offset, sort=args.sort)
    columns = ['reference', 'size', 'safe_to_manage']
    if detailed:
        columns.extend(['reason_not_safe', 'cinder_id', 'extra_info'])
    utils.print_list(volumes, columns, sortby_index=None)


@utils.arg('host',
           metavar='<host>',
           help='Cinder host on which to list manageable snapshots; '
                'takes the form: host@backend-name#pool')
@utils.arg('--detailed',
           metavar='<detailed>',
           default=True,
           help='Returned detailed information (default true).')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning snapshots that appear later in the snapshot '
                'list than that represented by this snapshot id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of snapshots to return. Default=None.')
@utils.arg('--offset',
           metavar='<offset>',
           default=None,
           help='Number of snapshots to skip after marker. Default=None.')
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
def do_snapshot_manageable_list(cs, args):
    """Lists all manageable snapshots."""
    detailed = strutils.bool_from_string(args.detailed)
    snapshots = cs.volume_snapshots.list_manageable(host=args.host,
                                                    detailed=detailed,
                                                    marker=args.marker,
                                                    limit=args.limit,
                                                    offset=args.offset,
                                                    sort=args.sort)
    columns = ['reference', 'size', 'safe_to_manage', 'source_reference']
    if detailed:
        columns.extend(['reason_not_safe', 'cinder_id', 'extra_info'])
    utils.print_list(snapshots, columns, sortby_index=None)
