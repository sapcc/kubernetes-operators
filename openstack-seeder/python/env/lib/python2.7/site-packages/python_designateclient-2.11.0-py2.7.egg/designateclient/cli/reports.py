# Copyright 2013 Hewlett-Packard Development Company, L.P. All Rights Reserved.
#
# Author: Patrick Galbraith <patg@patg.net>
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
from designateclient.cli import base


class DomainCountCommand(base.GetCommand):
    """Get counts for total domains"""

    def execute(self, parsed_args):
        return self.client.reports.count_domains()


class RecordCountCommand(base.GetCommand):
    """Get counts for total records"""

    def execute(self, parsed_args):
        return self.client.reports.count_records()


class TenantCountCommand(base.GetCommand):
    """Get counts for total tenants"""

    def execute(self, parsed_args):
        return self.client.reports.count_tenants()


class CountsCommand(base.GetCommand):
    """Get count totals for all tenants, domains and records"""

    def execute(self, parsed_args):
        return self.client.reports.count_all()


class TenantsCommand(base.ListCommand):
    """Get list of tenants and domain count for each"""

    columns = ['domain_count', 'id']

    def execute(self, parsed_args):
        return self.client.reports.tenants_all()


class TenantCommand(base.ListCommand):
    """Get a list of domains for given tenant"""

    columns = ['domain']

    def get_parser(self, prog_name):
        parser = super(TenantCommand, self).get_parser(prog_name)

        parser.add_argument('--report-tenant-id',
                            help="The tenant_id being reported on.",
                            required=True)

        return parser

    def execute(self, parsed_args):
        return self.client.reports.tenant_domains(parsed_args.report_tenant_id)
