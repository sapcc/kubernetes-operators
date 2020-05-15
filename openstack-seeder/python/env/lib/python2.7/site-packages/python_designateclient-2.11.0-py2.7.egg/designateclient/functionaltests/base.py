"""
Copyright 2015 Rackspace

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from tempest.lib.cli import base
from tempest.lib.exceptions import CommandFailed

from designateclient.functionaltests import client
from designateclient.functionaltests import config


class BaseDesignateTest(base.ClientTestBase):

    def _get_clients(self):
        config.read_config()
        return client.DesignateCLI.as_user('default')

    def ensure_tld_exists(self, tld):
        try:
            self.clients.as_user('admin').tld_create(tld)
        except CommandFailed:
            pass

    def _is_entity_in_list(self, entity, entity_list):
        """Determines if the given entity exists in the given list.

        Uses the id for comparison.

        Certain entities (e.g. zone import, export) cannot be made
        comparable in a list of CLI output results, because the fields
        in a list command can be different from those in a show command.

        """
        return any([entity_record.id == entity.id
                    for entity_record in entity_list])
