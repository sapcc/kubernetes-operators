# Copyright (c) 2013 OpenStack Foundation
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


"""Volume Type interface."""
from six.moves.urllib import parse

from cinderclient.apiclient import base as common_base
from cinderclient import base


class VolumeType(base.Resource):
    """A Volume Type is the type of volume to be created."""
    def __repr__(self):
        return "<VolumeType: %s>" % self.name

    @property
    def is_public(self):
        """
        Provide a user-friendly accessor to os-volume-type-access:is_public
        """
        return self._info.get("os-volume-type-access:is_public",
                              self._info.get("is_public", 'N/A'))

    def get_keys(self):
        """Get extra specs from a volume type.

        :param vol_type: The :class:`VolumeType` to get extra specs from
        """
        _resp, body = self.manager.api.client.get(
            "/types/%s/extra_specs" %
            base.getid(self))
        return body["extra_specs"]

    def set_keys(self, metadata):
        """Set extra specs on a volume type.

        :param type : The :class:`VolumeType` to set extra spec on
        :param metadata: A dict of key/value pairs to be set
        """
        body = {'extra_specs': metadata}
        return self.manager._create(
            "/types/%s/extra_specs" % base.getid(self),
            body,
            "extra_specs",
            return_raw=True)

    def unset_keys(self, keys):
        """Unset extra specs on a volue type.

        :param type_id: The :class:`VolumeType` to unset extra spec on
        :param keys: A list of keys to be unset
        """

        # NOTE(jdg): This wasn't actually doing all of the keys before
        # the return in the loop resulted in only ONE key being unset,
        # since on success the return was ListWithMeta class, we'll only
        # interrupt the loop and if an exception is raised.
        response_list = []
        for k in keys:
            resp, body = self.manager._delete(
                "/types/%s/extra_specs/%s" % (
                base.getid(self), k))
            response_list.append(resp)

        return common_base.ListWithMeta([], response_list)


class VolumeTypeManager(base.ManagerWithFind):
    """Manage :class:`VolumeType` resources."""
    resource_class = VolumeType

    def list(self, search_opts=None, is_public=None):
        """Lists all volume types.

        :param search_opts: Optional search filters.
        :param is_public: Whether to only get public types.
        :return: List of :class:`VolumeType`.
        """
        if not search_opts:
            search_opts = dict()

        # Remove 'all_tenants' option added by ManagerWithFind.findall(),
        # as it is not a valid search option for volume_types.
        search_opts.pop('all_tenants', None)

        # Need to keep backwards compatibility with is_public usage. If it
        # isn't included then cinder will assume you want is_public=True, which
        # negatively affects the results.
        if 'is_public' not in search_opts:
            search_opts['is_public'] = is_public

        query_string = "?%s" % parse.urlencode(search_opts)
        return self._list("/types%s" % query_string, "volume_types")

    def get(self, volume_type):
        """Get a specific volume type.

        :param volume_type: The ID of the :class:`VolumeType` to get.
        :rtype: :class:`VolumeType`
        """
        return self._get("/types/%s" % base.getid(volume_type), "volume_type")

    def default(self):
        """Get the default volume type.

        :rtype: :class:`VolumeType`
        """
        return self._get("/types/default", "volume_type")

    def delete(self, volume_type):
        """Deletes a specific volume_type.

        :param volume_type: The name or ID of the :class:`VolumeType` to get.
        """
        return self._delete("/types/%s" % base.getid(volume_type))

    def create(self, name, description=None, is_public=True):
        """Creates a volume type.

        :param name: Descriptive name of the volume type
        :param description: Description of the volume type
        :param is_public: Volume type visibility
        :rtype: :class:`VolumeType`
        """

        body = {
            "volume_type": {
                "name": name,
                "description": description,
                "os-volume-type-access:is_public": is_public,
            }
        }

        return self._create("/types", body, "volume_type")

    def update(self, volume_type, name=None, description=None, is_public=None):
        """Update the name and/or description for a volume type.

        :param volume_type: The ID of the :class:`VolumeType` to update.
        :param name: Descriptive name of the volume type.
        :param description: Description of the volume type.
        :rtype: :class:`VolumeType`
        """

        body = {
            "volume_type": {
                "name": name,
                "description": description
            }
        }
        if is_public is not None:
            body["volume_type"]["is_public"] = is_public

        return self._update("/types/%s" % base.getid(volume_type),
                            body, response_key="volume_type")
