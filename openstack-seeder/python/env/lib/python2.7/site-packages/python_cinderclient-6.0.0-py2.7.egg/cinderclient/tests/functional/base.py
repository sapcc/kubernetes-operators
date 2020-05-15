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

import os
import time

import six
from tempest.lib.cli import base
from tempest.lib.cli import output_parser
from tempest.lib import exceptions

_CREDS_FILE = 'functional_creds.conf'


def credentials():
    """Retrieves credentials to run functional tests

    Credentials are either read from the environment or from a config file
    ('functional_creds.conf'). Environment variables override those from the
    config file.

    The 'functional_creds.conf' file is the clean and new way to use (by
    default tox 2.0 does not pass environment variables).
    """

    username = os.environ.get('OS_USERNAME')
    password = os.environ.get('OS_PASSWORD')
    tenant_name = (os.environ.get('OS_TENANT_NAME') or
                   os.environ.get('OS_PROJECT_NAME'))
    auth_url = os.environ.get('OS_AUTH_URL')

    config = six.moves.configparser.RawConfigParser()
    if config.read(_CREDS_FILE):
        username = username or config.get('admin', 'user')
        password = password or config.get('admin', 'pass')
        tenant_name = tenant_name or config.get('admin', 'tenant')
        auth_url = auth_url or config.get('auth', 'uri')

    return {
        'username': username,
        'password': password,
        'tenant_name': tenant_name,
        'uri': auth_url
    }


class ClientTestBase(base.ClientTestBase):
    """Cinder base class, issues calls to cinderclient.

    """
    def setUp(self):
        super(ClientTestBase, self).setUp()
        self.clients = self._get_clients()
        self.parser = output_parser

    def _get_clients(self):
        cli_dir = os.environ.get(
            'OS_CINDERCLIENT_EXEC_DIR',
            os.path.join(os.path.abspath('.'), '.tox/functional/bin'))

        return base.CLIClient(cli_dir=cli_dir, **credentials())

    def cinder(self, *args, **kwargs):
        return self.clients.cinder(*args,
                                   **kwargs)

    def assertTableHeaders(self, output_lines, field_names):
        """Verify that output table has headers item listed in field_names.

        :param output_lines: output table from cmd
        :param field_names: field names from the output table of the cmd
        """
        table = self.parser.table(output_lines)
        headers = table['headers']
        for field in field_names:
            self.assertIn(field, headers)

    def assert_object_details(self, expected, items):
        """Check presence of common object properties.

        :param expected: expected object properties
        :param items: object properties
        """
        for value in expected:
            self.assertIn(value, items)

    def _get_property_from_output(self, output):
        """Create a dictionary from an output

        :param output: the output of the cmd
        """
        obj = {}
        items = self.parser.listing(output)
        for item in items:
            obj[item['Property']] = six.text_type(item['Value'])
        return obj

    def object_cmd(self, object_name, cmd):
        return (object_name + '-' + cmd if object_name != 'volume' else cmd)

    def wait_for_object_status(self, object_name, object_id, status,
                               timeout=120, interval=3):
        """Wait until object reaches given status.

        :param object_name: object name
        :param object_id: uuid4 id of an object
        :param status: expected status of an object
        :param timeout: timeout in seconds
        """
        cmd = self.object_cmd(object_name, 'show')
        start_time = time.time()
        while time.time() - start_time < timeout:
            if status in self.cinder(cmd, params=object_id):
                break
            time.sleep(interval)
        else:
            self.fail("%s %s did not reach status %s after %d seconds."
                      % (object_name, object_id, status, timeout))

    def check_object_deleted(self, object_name, object_id, timeout=60):
        """Check that object deleted successfully.

        :param object_name: object name
        :param object_id: uuid4 id of an object
        :param timeout: timeout in seconds
        """
        cmd = self.object_cmd(object_name, 'show')
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if object_id not in self.cinder(cmd, params=object_id):
                    break
        except exceptions.CommandFailed:
            pass
        else:
            self.fail("%s %s not deleted after %d seconds."
                      % (object_name, object_id, timeout))

    def object_create(self, object_name, params):
        """Create an object.

        :param object_name: object name
        :param params: parameters to cinder command
        :return: object dictionary
        """
        cmd = self.object_cmd(object_name, 'create')
        output = self.cinder(cmd, params=params)
        object = self._get_property_from_output(output)
        self.addCleanup(self.object_delete, object_name, object['id'])
        self.wait_for_object_status(object_name, object['id'], 'available')
        return object

    def object_delete(self, object_name, object_id):
        """Delete specified object by ID.

        :param object_name: object name
        :param object_id: uuid4 id of an object
        """
        cmd = self.object_cmd(object_name, 'list')
        cmd_delete = self.object_cmd(object_name, 'delete')
        if object_id in self.cinder(cmd):
            self.cinder(cmd_delete, params=object_id)
