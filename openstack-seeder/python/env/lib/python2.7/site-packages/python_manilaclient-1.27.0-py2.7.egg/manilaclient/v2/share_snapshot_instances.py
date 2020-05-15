# Copyright 2016 Huawei inc.
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


class ShareSnapshotInstance(common_base.Resource):
    """A snapshot instance is an instance of a snapshot."""

    def __repr__(self):
        return "<SnapshotInstance: %s>" % self.id

    def reset_state(self, state):
        """Update snapshot instance's 'status' attr."""
        self.manager.reset_state(self, state)


class ShareSnapshotInstanceManager(base.ManagerWithFind):
    """Manage :class:`SnapshotInstances` resources."""
    resource_class = ShareSnapshotInstance

    @api_versions.wraps("2.19")
    def get(self, instance):
        """Get a snapshot instance.

        :param instance: either snapshot instance object or text with its ID.
        :rtype: :class:`ShareSnapshotInstance`
        """
        snapshot_instance_id = common_base.getid(instance)
        return self._get("/snapshot-instances/%s" % snapshot_instance_id,
                         "snapshot_instance")

    @api_versions.wraps("2.19")
    def list(self, detailed=False, snapshot=None, search_opts=None):
        """List all snapshot instances."""
        if detailed:
            url = '/snapshot-instances/detail'
        else:
            url = '/snapshot-instances'

        if snapshot:
            url += '?snapshot_id=%s' % common_base.getid(snapshot)
        return self._list(url, 'snapshot_instances')

    @api_versions.wraps("2.19")
    def reset_state(self, instance, state):
        """Reset the 'status' attr of the snapshot instance.

        :param instance: either snapshot instance object or its UUID.
        :param state: state to set the snapshot instance's 'status' attr to.
        """
        return self._action("reset_status", instance, {"status": state})

    def _action(self, action, instance, info=None, **kwargs):
        """Perform a snapshot instance 'action'."""
        body = {action: info}
        self.run_hooks('modify_body_for_action', body, **kwargs)
        url = ('/snapshot-instances/%s/action' %
               common_base.getid(instance))
        return self.api.client.post(url, body=body)
