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

import sys
import time

from cinderclient import exceptions
from cinderclient import utils

_quota_resources = ['volumes', 'snapshots', 'gigabytes',
                    'backups', 'backup_gigabytes',
                    'per_volume_gigabytes', 'groups', ]
_quota_infos = ['Type', 'In_use', 'Reserved', 'Limit', 'Allocated']


def print_volume_image(image_resp_tuple):
    # image_resp_tuple = tuple (response, body)
    image = image_resp_tuple[1]
    vt = image['os-volume_upload_image'].get('volume_type')
    if vt is not None:
        image['os-volume_upload_image']['volume_type'] = vt.get('name')
    utils.print_dict(image['os-volume_upload_image'])


def poll_for_status(poll_fn, obj_id, action, final_ok_states,
                    poll_period=5, show_progress=True):
    """Blocks while an action occurs. Periodically shows progress."""
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


def find_volume_snapshot(cs, snapshot):
    """Gets a volume snapshot by name or ID."""
    return utils.find_resource(cs.volume_snapshots, snapshot)


def find_vtype(cs, vtype):
    """Gets a volume type by name or ID."""
    return utils.find_resource(cs.volume_types, vtype)


def find_gtype(cs, gtype):
    """Gets a group type by name or ID."""
    return utils.find_resource(cs.group_types, gtype)


def find_backup(cs, backup):
    """Gets a backup by name or ID."""
    return utils.find_resource(cs.backups, backup)


def find_consistencygroup(cs, consistencygroup):
    """Gets a consistency group by name or ID."""
    return utils.find_resource(cs.consistencygroups, consistencygroup)


def find_group(cs, group, **kwargs):
    """Gets a group by name or ID."""
    kwargs['is_group'] = True
    return utils.find_resource(cs.groups, group, **kwargs)


def find_cgsnapshot(cs, cgsnapshot):
    """Gets a cgsnapshot by name or ID."""
    return utils.find_resource(cs.cgsnapshots, cgsnapshot)


def find_group_snapshot(cs, group_snapshot):
    """Gets a group_snapshot by name or ID."""
    return utils.find_resource(cs.group_snapshots, group_snapshot)


def find_transfer(cs, transfer):
    """Gets a transfer by name or ID."""
    return utils.find_resource(cs.transfers, transfer)


def find_qos_specs(cs, qos_specs):
    """Gets a qos specs by ID."""
    return utils.find_resource(cs.qos_specs, qos_specs)


def find_message(cs, message):
    """Gets a message by ID."""
    return utils.find_resource(cs.messages, message)


def print_volume_snapshot(snapshot):
    utils.print_dict(snapshot._info)


def translate_keys(collection, convert):
    for item in collection:
        keys = item.__dict__
        for from_key, to_key in convert:
            if from_key in keys and to_key not in keys:
                setattr(item, to_key, item._info[from_key])


def translate_volume_keys(collection):
    convert = [('volumeType', 'volume_type'),
               ('os-vol-tenant-attr:tenant_id', 'tenant_id')]
    translate_keys(collection, convert)


def translate_volume_snapshot_keys(collection):
    convert = [('volumeId', 'volume_id')]
    translate_keys(collection, convert)


def translate_availability_zone_keys(collection):
    convert = [('zoneName', 'name'), ('zoneState', 'status')]
    translate_keys(collection, convert)


def extract_filters(args):
    filters = {}
    for f in args:
        if '=' in f:
            (key, value) = f.split('=', 1)
            if value.startswith('{') and value.endswith('}'):
                value = _build_internal_dict(value[1:-1])
            filters[key] = value
        else:
            print("WARNING: Ignoring the filter %s while showing result." % f)

    return filters


def _build_internal_dict(content):
    result = {}
    for pair in content.split(','):
        k, v = pair.split(':', 1)
        result.update({k.strip(): v.strip()})
    return result


def extract_metadata(args, type='user_metadata'):
    metadata = {}
    if type == 'image_metadata':
        args_metadata = args.image_metadata
    else:
        args_metadata = args.metadata
    for metadatum in args_metadata:
        # unset doesn't require a val, so we have the if/else
        if '=' in metadatum:
            (key, value) = metadatum.split('=', 1)
        else:
            key = metadatum
            value = None

        metadata[key] = value
    return metadata


def print_volume_type_list(vtypes):
    utils.print_list(vtypes, ['ID', 'Name', 'Description', 'Is_Public'])


def print_group_type_list(gtypes):
    utils.print_list(gtypes, ['ID', 'Name', 'Description'])


def print_resource_filter_list(filters):
    formatter = {'Filters': lambda resource: ', '.join(resource.filters)}
    utils.print_list(filters, ['Resource', 'Filters'], formatters=formatter)


def quota_show(quotas):
    quotas_info_dict = utils.unicode_key_value_to_string(quotas._info)
    quota_dict = {}
    for resource in quotas_info_dict.keys():
        good_name = False
        for name in _quota_resources:
            if resource.startswith(name):
                good_name = True
        if not good_name:
            continue
        quota_dict[resource] = getattr(quotas, resource, None)
    utils.print_dict(quota_dict)


def quota_usage_show(quotas):
    quota_list = []
    quotas_info_dict = utils.unicode_key_value_to_string(quotas._info)
    for resource in quotas_info_dict.keys():
        good_name = False
        for name in _quota_resources:
            if resource.startswith(name):
                good_name = True
        if not good_name:
            continue
        quota_info = getattr(quotas, resource, None)
        quota_info['Type'] = resource
        quota_info = dict((k.capitalize(), v) for k, v in quota_info.items())
        quota_list.append(quota_info)
    utils.print_list(quota_list, _quota_infos)


def quota_update(manager, identifier, args):
    updates = {}
    for resource in _quota_resources:
        val = getattr(args, resource, None)
        if val is not None:
            if args.volume_type:
                resource = resource + '_%s' % args.volume_type
            updates[resource] = val

    if updates:
        skip_validation = getattr(args, 'skip_validation', True)
        if not skip_validation:
            updates['skip_validation'] = skip_validation
        quota_show(manager.update(identifier, **updates))
    else:
        msg = 'Must supply at least one quota field to update.'
        raise exceptions.ClientException(code=1, message=msg)


def find_volume_type(cs, vtype):
    """Gets a volume type by name or ID."""
    return utils.find_resource(cs.volume_types, vtype)


def find_group_type(cs, gtype):
    """Gets a group type by name or ID."""
    return utils.find_resource(cs.group_types, gtype)


def print_volume_encryption_type_list(encryption_types):
    """
    Lists volume encryption types.

    :param encryption_types: a list of :class: VolumeEncryptionType instances
    """
    utils.print_list(encryption_types, ['Volume Type ID', 'Provider',
                                        'Cipher', 'Key Size',
                                        'Control Location'])


def print_qos_specs(qos_specs):
    # formatters defines field to be converted from unicode to string
    utils.print_dict(qos_specs._info, formatters=['specs'])


def print_qos_specs_list(q_specs):
    utils.print_list(q_specs, ['ID', 'Name', 'Consumer', 'specs'])


def print_qos_specs_and_associations_list(q_specs):
    utils.print_list(q_specs, ['ID', 'Name', 'Consumer', 'specs'])


def print_associations_list(associations):
    utils.print_list(associations, ['Association_Type', 'Name', 'ID'])


def _poll_for_status(poll_fn, obj_id, info, action, final_ok_states,
                     timeout_period, global_request_id=None, messages=None,
                     poll_period=2, status_field="status"):
    """Block while an action is being performed."""
    time_elapsed = 0
    while True:
        time.sleep(poll_period)
        time_elapsed += poll_period
        obj = poll_fn(obj_id)
        status = getattr(obj, status_field)
        info[status_field] = status
        if status:
            status = status.lower()

        if status in final_ok_states:
            break
        elif status == "error":
            utils.print_dict(info)
            if global_request_id:
                search_opts = {
                    'request_id': global_request_id
                    }
                message_list = messages.list(search_opts=search_opts)
                try:
                    fault_msg = message_list[0].user_message
                except IndexError:
                    fault_msg = "Unknown error. Operation failed."
                raise exceptions.ResourceInErrorState(obj, fault_msg)
        elif time_elapsed == timeout_period:
            utils.print_dict(info)
            raise exceptions.TimeoutException(obj, action)
