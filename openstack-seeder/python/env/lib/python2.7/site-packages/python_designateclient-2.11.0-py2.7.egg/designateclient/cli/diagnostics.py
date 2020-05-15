# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
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


class PingCommand(base.GetCommand):
    """Ping a service on a given host"""

    def get_parser(self, prog_name):
        parser = super(PingCommand, self).get_parser(prog_name)

        parser.add_argument('--service', help="Service name (e.g. central)",
                            required=True)
        parser.add_argument('--host', help="Hostname", required=True)

        return parser

    def execute(self, parsed_args):
        return self.client.diagnostics.ping(parsed_args.service,
                                            parsed_args.host)
