# Copyright 2010 Jacob Kaplan-Moss
# Copyright 2011 OpenStack Foundation
# Copyright 2011 Piston Cloud Computing, Inc.

# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
OpenStack Client interface. Handles the REST calls and responses.
"""

from oslo_utils import importutils

from manilaclient import api_versions
from manilaclient import exceptions


def get_client_class(version):
    version_map = {
        '1': 'manilaclient.v1.client.Client',
        '2': 'manilaclient.v2.client.Client',
    }
    try:
        client_path = version_map[str(version)]
    except (KeyError, ValueError):
        msg = "Invalid client version '%s'. must be one of: %s" % (
            (version, ', '.join(version_map)))
        raise exceptions.UnsupportedVersion(msg)

    return importutils.import_class(client_path)


def Client(client_version, *args, **kwargs):

    def _convert_to_api_version(version):
        """Convert version to an APIVersion object unless it already is one."""

        if hasattr(version, 'get_major_version'):
            api_version = version
        else:
            if version in ('1', '1.0'):
                api_version = api_versions.APIVersion(
                    api_versions.DEPRECATED_VERSION)
            elif version == '2':
                api_version = api_versions.APIVersion(api_versions.MIN_VERSION)
            else:
                api_version = api_versions.APIVersion(version)
        return api_version

    api_version = _convert_to_api_version(client_version)
    client_class = get_client_class(api_version.get_major_version())

    # Make sure the kwarg api_version is set with an APIVersion object.
    # 1st choice is to use the incoming kwarg. 2nd choice is the positional.
    kwargs['api_version'] = _convert_to_api_version(
        kwargs.get('api_version', api_version))

    return client_class(*args, **kwargs)
