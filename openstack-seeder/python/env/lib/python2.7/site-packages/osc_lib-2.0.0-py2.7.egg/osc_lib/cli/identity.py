#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

from openstack import exceptions
from openstack.identity.v3 import project

from osc_lib.i18n import _


def add_project_owner_option_to_parser(parser):
    """Register project and project domain options.

    :param parser: argparse.Argument parser object.
    """
    parser.add_argument(
        '--project',
        metavar='<project>',
        help=_("Owner's project (name or ID)")
    )
    parser.add_argument(
        '--project-domain',
        metavar='<project-domain>',
        help=_('Domain the project belongs to (name or ID). '
               'This can be used in case collisions between project names '
               'exist.'),
    )


def find_project(sdk_connection, name_or_id, domain_name_or_id=None):
    """Find a project by its name name or ID.

    If Forbidden to find the resource (a common case if the user does not have
    permission), then return the resource by creating a local instance of
    openstack.identity.v3.Project resource.

    :param sdk_connection: Connection object of OpenStack SDK.
    :type sdk_connection: `openstack.connection.Connection`
    :param name_or_id: Name or ID of the project
    :type name_or_id: string
    :param domain_name_or_id: Domain name or ID of the project.
        This can be used when there are multiple projects with a same name.
    :returns: the project object found
    :rtype: `openstack.identity.v3.project.Project`

    """
    try:
        if domain_name_or_id:
            domain = sdk_connection.identity.find_domain(domain_name_or_id,
                                                         ignore_missing=False)
            domain_id = domain.id
        else:
            domain_id = None
        return sdk_connection.identity.find_project(name_or_id,
                                                    ignore_missing=False,
                                                    domain_id=domain_id)
    # NOTE: OpenStack SDK raises HttpException for 403 response code.
    # There is no specific exception class at now, so we need to catch
    # HttpException and check the status code.
    except exceptions.HttpException as e:
        if e.status_code == 403:
            return project.Project(id=name_or_id, name=name_or_id)
        raise
