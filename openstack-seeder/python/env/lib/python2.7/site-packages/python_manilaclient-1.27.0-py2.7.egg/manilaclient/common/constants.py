# Copyright 2014 Mirantis, Inc.
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

"""Common constants that can be used all over the manilaclient."""

# These are used for providing desired sorting params with list requests
SORT_DIR_VALUES = ('asc', 'desc')

SHARE_SORT_KEY_VALUES = (
    'id', 'status', 'size', 'host', 'share_proto',
    'availability_zone',
    'user_id', 'project_id',
    'created_at', 'updated_at',
    'display_name', 'name',
    'share_type_id', 'share_type',
    'share_network_id', 'share_network',
    'snapshot_id', 'snapshot',
)

SNAPSHOT_SORT_KEY_VALUES = (
    'id',
    'status',
    'size',
    'share_id',
    'user_id',
    'project_id',
    'progress',
    'name',
    'display_name',
)

SHARE_GROUP_SORT_KEY_VALUES = (
    'id',
    'name',
    'status',
    'host',
    'user_id',
    'project_id',
    'created_at',
    'availability_zone',
    'share_network',
    'share_network_id',
    'share_group_type',
    'share_group_type_id',
    'source_share_group_snapshot_id',
)

SHARE_GROUP_SNAPSHOT_SORT_KEY_VALUES = (
    'id',
    'name',
    'status',
    'host',
    'user_id',
    'project_id',
    'created_at',
    'share_group_id',
)

TASK_STATE_MIGRATION_SUCCESS = 'migration_success'
TASK_STATE_MIGRATION_ERROR = 'migration_error'
TASK_STATE_MIGRATION_CANCELLED = 'migration_cancelled'
TASK_STATE_MIGRATION_DRIVER_PHASE1_DONE = 'migration_driver_phase1_done'
TASK_STATE_DATA_COPYING_COMPLETED = 'data_copying_completed'

EXPERIMENTAL_HTTP_HEADER = 'X-OpenStack-Manila-API-Experimental'
V1_SERVICE_TYPE = 'share'
V2_SERVICE_TYPE = 'sharev2'

SERVICE_TYPES = {'1': V1_SERVICE_TYPE, '2': V2_SERVICE_TYPE}

EXTENSION_PLUGIN_NAMESPACE = 'manilaclient.common.apiclient.auth'
MESSAGE_SORT_KEY_VALUES = (
    'id', 'project_id', 'request_id', 'resource_type', 'action_id',
    'detail_id', 'resource_id', 'message_level', 'expires_at',
    'request_id', 'created_at'
)

STATUS_AVAILABLE = 'available'
STATUS_ERROR = 'error'
STATUS_ACTIVE = 'active'
STATUS_MANAGE_ERROR = 'manage_error'
STATUS_UNMANAGE_ERROR = 'unmanage_error'
STATUS_DELETING = 'deleting'
STATUS_CREATING = 'creating'
