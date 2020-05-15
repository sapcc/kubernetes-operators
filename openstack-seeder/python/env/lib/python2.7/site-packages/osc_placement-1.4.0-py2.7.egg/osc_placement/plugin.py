# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"OpenStackClient plugin for Placement service"

import logging

from osc_lib import utils
from osc_placement import version


LOG = logging.getLogger(__name__)

API_NAME = 'placement'
API_VERSION_OPTION = 'os_placement_api_version'
API_VERSIONS = {v: 'osc_placement.http.SessionClient'
                for v in version.SUPPORTED_VERSIONS}


def make_client(instance):
    client_class = utils.get_client_class(
        API_NAME,
        instance._api_version[API_NAME],
        API_VERSIONS
    )

    ks_filter = {'service_type': API_NAME,
                 'region_name': instance._region_name,
                 'interface': instance.interface}

    LOG.debug('Instantiating placement client: %s', client_class)
    # TODO(rpodolyaka): add version negotiation
    return client_class(session=instance.session,
                        ks_filter=ks_filter,
                        api_version=instance._api_version[API_NAME])


def build_option_parser(parser):
    default = version.SUPPORTED_VERSIONS[0]
    parser.add_argument(
        '--os-placement-api-version',
        metavar='<placement-api-version>',
        default=utils.env(
            'OS_PLACEMENT_API_VERSION',
            default=default
        ),
        help='Placement API version, default=%s' % default)

    return parser
