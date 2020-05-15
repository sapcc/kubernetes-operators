# Copyright 2016 Hewlett Packard Enterprise Development Company LP
#
# Author: Graham Hayes <endre.karlson@hp.com>
#
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
import six


def add_all_projects_option(parser):
    parser.add_argument(
        '--all-projects',
        default=False,
        action='store_true',
        help='Show results from all projects. Default: False'
    )


def add_edit_managed_option(parser):
    parser.add_argument(
        '--edit-managed',
        default=False,
        action='store_true',
        help='Edit resources marked as managed. Default: False'
    )


def add_sudo_project_id_option(parser):
    parser.add_argument(
        '--sudo-project-id',
        default=None,
        help='Project ID to impersonate for this command. Default: None'
    )


def add_all_common_options(parser):
    add_all_projects_option(parser)
    add_edit_managed_option(parser)
    add_sudo_project_id_option(parser)


def set_all_projects(client, value):
    client.session.all_projects = value


def set_sudo_project_id(client, value):
    client.session.sudo_project_id = value


def set_edit_managed(client, value):
    client.session.edit_managed = value


def set_all_common_headers(client, parsed_args):

    if parsed_args.all_projects is not None and \
            isinstance(parsed_args.all_projects, bool):
        set_all_projects(client, parsed_args.all_projects)

    if parsed_args.edit_managed is not None and \
            isinstance(parsed_args.edit_managed, bool):
        set_edit_managed(client, parsed_args.edit_managed)

    if parsed_args.sudo_project_id is not None and \
            isinstance(parsed_args.sudo_project_id, six.string_types):
        set_sudo_project_id(client, parsed_args.sudo_project_id)
