# Copyright 2015 Mirantis inc.
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

from oslo_utils import uuidutils

from manilaclient import api_versions
from manilaclient import base
from manilaclient.common.apiclient import base as common_base


class ShareInstance(common_base.Resource):
    """A share is an extra block level storage to the OpenStack instances."""
    def __repr__(self):
        return "<Share: %s>" % self.id

    def force_delete(self):
        """Delete the specified share ignoring its current state."""
        self.manager.force_delete(self)

    def reset_state(self, state):
        """Update the share with the provided state."""
        self.manager.reset_state(self, state)


class ShareInstanceManager(base.ManagerWithFind):
    """Manage :class:`ShareInstances` resources."""
    resource_class = ShareInstance

    @api_versions.wraps("2.3")
    def get(self, instance):
        """Get a share instance.

        :param instance: either share object or text with its ID.
        :rtype: :class:`ShareInstance`
        """
        share_id = common_base.getid(instance)
        return self._get("/share_instances/%s" % share_id, "share_instance")

    @api_versions.wraps("2.3", "2.34")
    def list(self, search_opts=None):
        """List all share instances."""
        return self.do_list()

    @api_versions.wraps("2.35")   # noqa
    def list(self, export_location=None, search_opts=None):
        """List all share instances."""
        return self.do_list(export_location)

    def do_list(self, export_location=None):
        """List all share instances."""
        path = '/share_instances'
        if export_location:
            if uuidutils.is_uuid_like(export_location):
                path += '?export_location_id=' + export_location
            else:
                path += '?export_location_path=' + export_location

        return self._list(path, 'share_instances')

    def _action(self, action, instance, info=None, **kwargs):
        """Perform a share instance 'action'.

        :param action: text with action name.
        :param instance: either share object or text with its ID.
        :param info: dict with data for specified 'action'.
        :param kwargs: dict with data to be provided for action hooks.
        """
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = '/share_instances/%s/action' % common_base.getid(instance)
        return self.api.client.post(url, body=body)

    def _do_force_delete(self, instance, action_name="force_delete"):
        """Delete a share instance forcibly - share status will be avoided.

        :param instance: either share instance object or text with its ID.
        """
        return self._action(action_name, common_base.getid(instance))

    @api_versions.wraps("2.3", "2.6")
    def force_delete(self, instance):
        return self._do_force_delete(instance, "os-force_delete")

    @api_versions.wraps("2.7")  # noqa
    def force_delete(self, instance):
        return self._do_force_delete(instance, "force_delete")

    def _do_reset_state(self, instance, state, action_name):
        """Update the provided share instance with the provided state.

        :param instance: either share object or text with its ID.
        :param state: text with new state to set for share.
        """
        return self._action(action_name, instance, {"status": state})

    @api_versions.wraps("2.3", "2.6")
    def reset_state(self, instance, state):
        return self._do_reset_state(instance, state, "os-reset_status")

    @api_versions.wraps("2.7")  # noqa
    def reset_state(self, instance, state):
        return self._do_reset_state(instance, state, "reset_status")
