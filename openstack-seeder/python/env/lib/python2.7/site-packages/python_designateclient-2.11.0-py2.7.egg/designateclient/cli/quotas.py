# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Author: Endre Karlson <endre.karlson@hp.com>
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

import logging

from designateclient.cli import base


LOG = logging.getLogger(__name__)


class GetQuotaCommand(base.GetCommand):
    """Get Quota"""

    def get_parser(self, prog_name):
        parser = super(GetQuotaCommand, self).get_parser(prog_name)

        parser.add_argument('tenant_id', help="Tenant ID")

        return parser

    def execute(self, parsed_args):
        return self.client.quotas.get(parsed_args.tenant_id)


class UpdateQuotaCommand(base.UpdateCommand):
    """Update Quota"""

    def get_parser(self, prog_name):
        parser = super(UpdateQuotaCommand, self).get_parser(prog_name)

        parser.add_argument('tenant_id', help="Tenant ID.")
        parser.add_argument('--domains', help="Allowed domains.", type=int)
        parser.add_argument('--domain-recordsets',
                            help="Allowed domain records.",
                            type=int)
        parser.add_argument('--recordset-records',
                            help="Allowed recordset records.",
                            type=int)
        parser.add_argument('--domain-records',
                            help="Allowed domain records.",
                            type=int)
        parser.add_argument('--api-export-size',
                            help="Allowed zone export recordsets.",
                            type=int)
        return parser

    def execute(self, parsed_args):
        # TODO(kiall): API needs updating.. this get is silly
        quota = self.client.quotas.get(parsed_args.tenant_id)

        for key, old in quota.items():
            new = getattr(parsed_args, key)
            if new is not None and new != old:
                quota[key] = new
        return self.client.quotas.update(parsed_args.tenant_id, quota)


class ResetQuotaCommand(base.DeleteCommand):
    """Reset Quota"""

    def get_parser(self, prog_name):
        parser = super(ResetQuotaCommand, self).get_parser(prog_name)

        parser.add_argument('tenant_id', help="Tenant ID.")

        return parser

    def execute(self, parsed_args):
        self.client.quotas.reset(parsed_args.tenant_id)
