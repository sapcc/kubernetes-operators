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

"""Volume interface (v2 extension)."""

from cinderclient.apiclient import base as common_base
from cinderclient import base


class Volume(base.Resource):
    """A volume is an extra block level storage to the OpenStack instances."""
    def __repr__(self):
        return "<Volume: %s>" % self.id

    def delete(self, cascade=False):
        """Delete this volume."""
        return self.manager.delete(self, cascade=cascade)

    def update(self, **kwargs):
        """Update the name or description for this volume."""
        return self.manager.update(self, **kwargs)

    def attach(self, instance_uuid, mountpoint, mode='rw', host_name=None):
        """Inform Cinder that the given volume is attached to the given instance.

        Calling this method will not actually ask Cinder to attach
        a volume, but to mark it on the DB as attached. If the volume
        is not actually attached to the given instance, inconsistent
        data will result.

        The right flow of calls is :
        1- call reserve
        2- call initialize_connection
        3- call attach

        :param instance_uuid: uuid of the attaching instance.
        :param mountpoint: mountpoint on the attaching instance or host.
        :param mode: the access mode.
        :param host_name: name of the attaching host.
        """
        return self.manager.attach(self, instance_uuid, mountpoint, mode,
                                   host_name)

    def detach(self):
        """Inform Cinder that the given volume is detached from the given instance.

        Calling this method will not actually ask Cinder to detach
        a volume, but to mark it on the DB as detached. If the volume
        is not actually detached from the given instance, inconsistent
        data will result.

        The right flow of calls is :
        1- call reserve
        2- call initialize_connection
        3- call detach
        """
        return self.manager.detach(self)

    def reserve(self, volume):
        """Reserve this volume."""
        return self.manager.reserve(self)

    def unreserve(self, volume):
        """Unreserve this volume."""
        return self.manager.unreserve(self)

    def begin_detaching(self, volume):
        """Begin detaching volume."""
        return self.manager.begin_detaching(self)

    def roll_detaching(self, volume):
        """Roll detaching volume."""
        return self.manager.roll_detaching(self)

    def initialize_connection(self, volume, connector):
        """Initialize a volume connection.

        :param connector: connector dict from nova.
        """
        return self.manager.initialize_connection(self, connector)

    def terminate_connection(self, volume, connector):
        """Terminate a volume connection.

        :param connector: connector dict from nova.
        """
        return self.manager.terminate_connection(self, connector)

    def set_metadata(self, volume, metadata):
        """Set or Append metadata to a volume.

        :param volume : The :class: `Volume` to set metadata on
        :param metadata: A dict of key/value pairs to set
        """
        return self.manager.set_metadata(self, metadata)

    def set_image_metadata(self, volume, metadata):
        """Set a volume's image metadata.

        :param volume : The :class: `Volume` to set metadata on
        :param metadata: A dict of key/value pairs to set
        """
        return self.manager.set_image_metadata(self, volume, metadata)

    def delete_image_metadata(self, volume, keys):
        """Delete specified keys from volume's image metadata.

        :param volume: The :class:`Volume`.
        :param keys: A list of keys to be removed.
        """
        return self.manager.delete_image_metadata(self, volume, keys)

    def show_image_metadata(self, volume):
        """Show a volume's image metadata.

        :param volume : The :class: `Volume` where the image metadata
            associated.
        """
        return self.manager.show_image_metadata(self)

    def upload_to_image(self, force, image_name, container_format,
                        disk_format, visibility=None,
                        protected=None):
        """Upload a volume to image service as an image.

        :param force: Boolean to enables or disables upload of a volume that
                      is attached to an instance.
        :param image_name: The new image name.
        :param container_format: Container format type.
        :param disk_format: Disk format type.
        :param visibility: The accessibility of image (allowed for
                           3.1-latest).
        :param protected: Boolean to decide whether prevents image from being
                          deleted (allowed for 3.1-latest).
        """
        return self.manager.upload_to_image(self, force, image_name,
                                            container_format, disk_format)

    def force_delete(self):
        """Delete the specified volume ignoring its current state.

        :param volume: The UUID of the volume to force-delete.
        """
        return self.manager.force_delete(self)

    def reset_state(self, state, attach_status=None, migration_status=None):
        """Update the volume with the provided state.

        :param state: The state of the volume to set.
        :param attach_status: The attach_status of the volume to be set,
                              or None to keep the current status.
        :param migration_status: The migration_status of the volume to be set,
                                 or None to keep the current status.
        """
        return self.manager.reset_state(self, state, attach_status,
                                        migration_status)

    def extend(self, volume, new_size):
        """Extend the size of the specified volume.

        :param volume: The UUID of the volume to extend
        :param new_size: The desired size to extend volume to.
        """
        return self.manager.extend(self, new_size)

    def migrate_volume(self, host, force_host_copy, lock_volume):
        """Migrate the volume to a new host."""
        return self.manager.migrate_volume(self, host, force_host_copy,
                                           lock_volume)

    def retype(self, volume_type, policy):
        """Change a volume's type."""
        return self.manager.retype(self, volume_type, policy)

    def update_all_metadata(self, metadata):
        """Update all metadata of this volume."""
        return self.manager.update_all_metadata(self, metadata)

    def update_readonly_flag(self, volume, read_only):
        """Update the read-only access mode flag of the specified volume.

        :param volume: The UUID of the volume to update.
        :param read_only: The value to indicate whether to update volume to
            read-only access mode.
        """
        return self.manager.update_readonly_flag(self, read_only)

    def manage(self, host, ref, name=None, description=None,
               volume_type=None, availability_zone=None, metadata=None,
               bootable=False):
        """Manage an existing volume."""
        return self.manager.manage(host=host, ref=ref, name=name,
                                   description=description,
                                   volume_type=volume_type,
                                   availability_zone=availability_zone,
                                   metadata=metadata, bootable=bootable)

    def list_manageable(self, host, detailed=True, marker=None, limit=None,
                        offset=None, sort=None):
        return self.manager.list_manageable(host, detailed=detailed,
                                            marker=marker, limit=limit,
                                            offset=offset, sort=sort)

    def unmanage(self, volume):
        """Unmanage a volume."""
        return self.manager.unmanage(volume)

    def get_pools(self, detail):
        """Show pool information for backends."""
        return self.manager.get_pools(detail)


class VolumeManager(base.ManagerWithFind):
    """Manage :class:`Volume` resources."""
    resource_class = Volume

    def create(self, size, consistencygroup_id=None,
               snapshot_id=None,
               source_volid=None, name=None, description=None,
               volume_type=None, user_id=None,
               project_id=None, availability_zone=None,
               metadata=None, imageRef=None, scheduler_hints=None):
        """Create a volume.

        :param size: Size of volume in GB
        :param consistencygroup_id: ID of the consistencygroup
        :param snapshot_id: ID of the snapshot
        :param name: Name of the volume
        :param description: Description of the volume
        :param volume_type: Type of volume
        :param user_id: User id derived from context (IGNORED)
        :param project_id: Project id derived from context (IGNORED)
        :param availability_zone: Availability Zone to use
        :param metadata: Optional metadata to set on volume creation
        :param imageRef: reference to an image stored in glance
        :param source_volid: ID of source volume to clone from
        :param scheduler_hints: (optional extension) arbitrary key-value pairs
                            specified by the client to help boot an instance
        :rtype: :class:`Volume`
        """
        if metadata is None:
            volume_metadata = {}
        else:
            volume_metadata = metadata

        body = {'volume': {'size': size,
                           'consistencygroup_id': consistencygroup_id,
                           'snapshot_id': snapshot_id,
                           'name': name,
                           'description': description,
                           'volume_type': volume_type,
                           'availability_zone': availability_zone,
                           'metadata': volume_metadata,
                           'imageRef': imageRef,
                           'source_volid': source_volid,
                           }}

        if scheduler_hints:
            body['OS-SCH-HNT:scheduler_hints'] = scheduler_hints

        return self._create('/volumes', body, 'volume')

    def get(self, volume_id):
        """Get a volume.

        :param volume_id: The ID of the volume to get.
        :rtype: :class:`Volume`
        """
        return self._get("/volumes/%s" % volume_id, "volume")

    def list(self, detailed=True, search_opts=None, marker=None, limit=None,
             sort=None):
        """Lists all volumes.

        :param detailed: Whether to return detailed volume info.
        :param search_opts: Search options to filter out volumes.
        :param marker: Begin returning volumes that appear later in the volume
                       list than that represented by this volume id.
        :param limit: Maximum number of volumes to return.
        :param sort: Sort information
        :rtype: list of :class:`Volume`
        """

        resource_type = "volumes"
        url = self._build_list_url(resource_type, detailed=detailed,
                                   search_opts=search_opts, marker=marker,
                                   limit=limit, sort=sort)
        return self._list(url, resource_type, limit=limit)

    def delete(self, volume, cascade=False):
        """Delete a volume.

        :param volume: The :class:`Volume` to delete.
        :param cascade: Also delete dependent snapshots.
        """

        loc = "/volumes/%s" % base.getid(volume)

        if cascade:
            loc += '?cascade=True'

        return self._delete(loc)

    def update(self, volume, **kwargs):
        """Update the name or description for a volume.

        :param volume: The :class:`Volume` to update.
        """
        if not kwargs:
            return

        body = {"volume": kwargs}

        return self._update("/volumes/%s" % base.getid(volume), body)

    def _action(self, action, volume, info=None, **kwargs):
        """Perform a volume "action."

        :returns: tuple (response, body)
        """
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/volumes/%s/action' % base.getid(volume)
        resp, body = self.api.client.post(url, body=body)
        return common_base.TupleWithMeta((resp, body), resp)

    def attach(self, volume, instance_uuid, mountpoint, mode='rw',
               host_name=None):
        """Set attachment metadata.

        :param volume: The :class:`Volume` (or its ID)
                       you would like to attach.
        :param instance_uuid: uuid of the attaching instance.
        :param mountpoint: mountpoint on the attaching instance or host.
        :param mode: the access mode.
        :param host_name: name of the attaching host.
        """
        body = {'mountpoint': mountpoint, 'mode': mode}
        if instance_uuid is not None:
            body.update({'instance_uuid': instance_uuid})
        if host_name is not None:
            body.update({'host_name': host_name})
        return self._action('os-attach', volume, body)

    def detach(self, volume, attachment_uuid=None):
        """Clear attachment metadata.

        :param volume: The :class:`Volume` (or its ID)
                       you would like to detach.
        :param attachment_uuid: The uuid of the volume attachment.
        """
        return self._action('os-detach', volume,
                            {'attachment_id': attachment_uuid})

    def reserve(self, volume):
        """Reserve this volume.

        :param volume: The :class:`Volume` (or its ID)
                       you would like to reserve.
        """
        return self._action('os-reserve', volume)

    def unreserve(self, volume):
        """Unreserve this volume.

        :param volume: The :class:`Volume` (or its ID)
                       you would like to unreserve.
        """
        return self._action('os-unreserve', volume)

    def begin_detaching(self, volume):
        """Begin detaching this volume.

        :param volume: The :class:`Volume` (or its ID)
                       you would like to detach.
        """
        return self._action('os-begin_detaching', volume)

    def roll_detaching(self, volume):
        """Roll detaching this volume.

        :param volume: The :class:`Volume` (or its ID)
                       you would like to roll detaching.
        """
        return self._action('os-roll_detaching', volume)

    def initialize_connection(self, volume, connector):
        """Initialize a volume connection.

        :param volume: The :class:`Volume` (or its ID).
        :param connector: connector dict from nova.
        """
        resp, body = self._action('os-initialize_connection', volume,
                                  {'connector': connector})
        return common_base.DictWithMeta(body['connection_info'], resp)

    def terminate_connection(self, volume, connector):
        """Terminate a volume connection.

        :param volume: The :class:`Volume` (or its ID).
        :param connector: connector dict from nova.
        """
        return self._action('os-terminate_connection', volume,
                            {'connector': connector})

    def set_metadata(self, volume, metadata):
        """Update/Set a volumes metadata.

        :param volume: The :class:`Volume`.
        :param metadata: A list of keys to be set.
        """
        body = {'metadata': metadata}
        return self._create("/volumes/%s/metadata" % base.getid(volume),
                            body, "metadata")

    def delete_metadata(self, volume, keys):
        """Delete specified keys from volumes metadata.

        :param volume: The :class:`Volume`.
        :param keys: A list of keys to be removed.
        """
        response_list = []
        for k in keys:
            resp, body = self._delete("/volumes/%s/metadata/%s" %
                                     (base.getid(volume), k))
            response_list.append(resp)

        return common_base.ListWithMeta([], response_list)

    def set_image_metadata(self, volume, metadata):
        """Set a volume's image metadata.

        :param volume: The :class:`Volume`.
        :param metadata: keys and the values to be set with.
        :type metadata: dict
        """
        return self._action("os-set_image_metadata", volume,
                            {'metadata': metadata})

    def delete_image_metadata(self, volume, keys):
        """Delete specified keys from volume's image metadata.

        :param volume: The :class:`Volume`.
        :param keys: A list of keys to be removed.
        """
        response_list = []
        for key in keys:
            resp, body = self._action("os-unset_image_metadata", volume,
                                      {'key': key})
            response_list.append(resp)

        return common_base.ListWithMeta([], response_list)

    def show_image_metadata(self, volume):
        """Show a volume's image metadata.

        :param volume : The :class: `Volume` where the image metadata
            associated.
        """
        return self._action("os-show_image_metadata", volume)

    def upload_to_image(self, volume, force, image_name, container_format,
                        disk_format):
        """Upload volume to image service as image.

        :param volume: The :class:`Volume` to upload.
        """
        return self._action('os-volume_upload_image',
                            volume,
                            {'force': force,
                             'image_name': image_name,
                             'container_format': container_format,
                             'disk_format': disk_format})

    def force_delete(self, volume):
        """Delete the specified volume ignoring its current state.

        :param volume: The :class:`Volume` to force-delete.
        """
        return self._action('os-force_delete', base.getid(volume))

    def reset_state(self, volume, state, attach_status=None,
                    migration_status=None):
        """Update the provided volume with the provided state.

        :param volume: The :class:`Volume` to set the state.
        :param state: The state of the volume to be set.
        :param attach_status: The attach_status of the volume to be set,
                              or None to keep the current status.
        :param migration_status: The migration_status of the volume to be set,
                                 or None to keep the current status.
        """
        body = {'status': state} if state else {}
        if attach_status:
            body.update({'attach_status': attach_status})
        if migration_status:
            body.update({'migration_status': migration_status})
        return self._action('os-reset_status', volume, body)

    def extend(self, volume, new_size):
        """Extend the size of the specified volume.

        :param volume: The UUID of the volume to extend.
        :param new_size: The requested size to extend volume to.
        """
        return self._action('os-extend',
                            base.getid(volume),
                            {'new_size': new_size})

    def get_encryption_metadata(self, volume_id):
        """
        Retrieve the encryption metadata from the desired volume.

        :param volume_id: the id of the volume to query
        :return: a dictionary of volume encryption metadata
        """
        metadata = self._get("/volumes/%s/encryption" % volume_id)
        return common_base.DictWithMeta(metadata._info, metadata.request_ids)

    def migrate_volume(self, volume, host, force_host_copy, lock_volume):
        """Migrate volume to new host.

        :param volume: The :class:`Volume` to migrate
        :param host: The destination host
        :param force_host_copy: Skip driver optimizations
        :param lock_volume: Lock the volume and guarantee the migration
                            to finish
        """
        return self._action('os-migrate_volume',
                            volume,
                            {'host': host, 'force_host_copy': force_host_copy,
                             'lock_volume': lock_volume})

    def migrate_volume_completion(self, old_volume, new_volume, error):
        """Complete the migration from the old volume to the temp new one.

        :param old_volume: The original :class:`Volume` in the migration
        :param new_volume: The new temporary :class:`Volume` in the migration
        :param error: Inform of an error to cause migration cleanup
        """
        new_volume_id = base.getid(new_volume)
        resp, body = self._action('os-migrate_volume_completion', old_volume,
                                  {'new_volume': new_volume_id,
                                   'error': error})
        return common_base.DictWithMeta(body, resp)

    def update_all_metadata(self, volume, metadata):
        """Update all metadata of a volume.

        :param volume: The :class:`Volume`.
        :param metadata: A list of keys to be updated.
        """
        body = {'metadata': metadata}
        return self._update("/volumes/%s/metadata" % base.getid(volume),
                            body)

    def update_readonly_flag(self, volume, flag):
        return self._action('os-update_readonly_flag',
                            base.getid(volume),
                            {'readonly': flag})

    def retype(self, volume, volume_type, policy):
        """Change a volume's type.

        :param volume: The :class:`Volume` to retype
        :param volume_type: New volume type
        :param policy: Policy for migration during the retype
        """
        return self._action('os-retype',
                            volume,
                            {'new_type': volume_type,
                             'migration_policy': policy})

    def set_bootable(self, volume, flag):
        return self._action('os-set_bootable',
                            base.getid(volume),
                            {'bootable': flag})

    def manage(self, host, ref, name=None, description=None,
               volume_type=None, availability_zone=None, metadata=None,
               bootable=False):
        """Manage an existing volume."""
        body = {'volume': {'host': host,
                           'ref': ref,
                           'name': name,
                           'description': description,
                           'volume_type': volume_type,
                           'availability_zone': availability_zone,
                           'metadata': metadata,
                           'bootable': bootable
                           }}
        return self._create('/os-volume-manage', body, 'volume')

    def list_manageable(self, host, detailed=True, marker=None, limit=None,
                        offset=None, sort=None):
        url = self._build_list_url("os-volume-manage", detailed=detailed,
                                   search_opts={'host': host}, marker=marker,
                                   limit=limit, offset=offset, sort=sort)
        return self._list(url, "manageable-volumes")

    def unmanage(self, volume):
        """Unmanage a volume."""
        return self._action('os-unmanage', volume, None)

    def get_pools(self, detail):
        """Show pool information for backends."""
        query_string = ""
        if detail:
            query_string = "?detail=True"

        return self._get('/scheduler-stats/get_pools%s' % query_string, None)
