# Copyright 2015 Mirantis Inc.
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

from tempest.lib import exceptions

"""
Exceptions for functional tests.
"""


class ResourceReleaseFailed(exceptions.TempestException):
    message = "Failed to release resource '%(res_type)s' with id '%(res_id)s'."


class InvalidResource(exceptions.TempestException):
    message = "Provided invalid resource: %(message)s"


class InvalidData(exceptions.TempestException):
    message = "Provided invalid data: %(message)s"


class ShareTypeNotFound(exceptions.NotFound):
    message = "Share type '%(share_type)s' was not found."


class InvalidConfiguration(exceptions.TempestException):
    message = "Invalid configuration: %(reason)s"


class ShareBuildErrorException(exceptions.TempestException):
    message = "Share %(share)s failed to build and is in ERROR status."


class ShareReplicaBuildErrorException(exceptions.TempestException):
    message = ("Share replica %(replica)s failed to build and is in ERROR "
               "status.")


class SnapshotBuildErrorException(exceptions.TempestException):
    message = "Snapshot %(snapshot)s failed to build and is in ERROR status."


class AccessRuleCreateErrorException(exceptions.TempestException):
    message = "Access rule %(access)s failed to create and is in ERROR state."


class AccessRuleDeleteErrorException(exceptions.TempestException):
    message = "Access rule %(access)s failed to delete and is in ERROR state."


class ShareMigrationException(exceptions.TempestException):
    message = ("Share %(share_id)s failed to migrate from "
               "host %(src)s to host %(dest)s.")
