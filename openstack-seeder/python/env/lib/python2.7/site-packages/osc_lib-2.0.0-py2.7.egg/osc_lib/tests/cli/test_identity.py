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

import argparse

import mock
from openstack import exceptions
from openstack.identity.v3 import project
import testtools

from osc_lib.cli import identity as cli_identity
from osc_lib.tests import utils as test_utils


class IdentityUtilsTestCase(test_utils.TestCase):

    def test_add_project_owner_option_to_parser(self):
        parser = argparse.ArgumentParser()
        cli_identity.add_project_owner_option_to_parser(parser)
        parsed_args = parser.parse_args(['--project', 'project1',
                                         '--project-domain', 'domain1'])
        self.assertEqual('project1', parsed_args.project)
        self.assertEqual('domain1', parsed_args.project_domain)

    def test_find_project(self):
        sdk_connection = mock.Mock()
        sdk_find_project = sdk_connection.identity.find_project
        sdk_find_project.return_value = mock.sentinel.project1

        ret = cli_identity.find_project(sdk_connection, 'project1')
        self.assertEqual(mock.sentinel.project1, ret)
        sdk_find_project.assert_called_once_with(
            'project1', ignore_missing=False, domain_id=None)

    def test_find_project_with_domain(self):
        domain1 = mock.Mock()
        domain1.id = 'id-domain1'

        sdk_connection = mock.Mock()
        sdk_find_domain = sdk_connection.identity.find_domain
        sdk_find_domain.return_value = domain1
        sdk_find_project = sdk_connection.identity.find_project
        sdk_find_project.return_value = mock.sentinel.project1

        ret = cli_identity.find_project(sdk_connection, 'project1', 'domain1')
        self.assertEqual(mock.sentinel.project1, ret)
        sdk_find_domain.assert_called_once_with(
            'domain1', ignore_missing=False)
        sdk_find_project.assert_called_once_with(
            'project1', ignore_missing=False, domain_id='id-domain1')

    def test_find_project_with_forbidden_exception(self):
        sdk_connection = mock.Mock()
        sdk_find_project = sdk_connection.identity.find_project
        exc = exceptions.HttpException()
        exc.status_code = 403
        sdk_find_project.side_effect = exc

        ret = cli_identity.find_project(sdk_connection, 'project1')

        self.assertIsInstance(ret, project.Project)
        self.assertEqual('project1', ret.id)
        self.assertEqual('project1', ret.name)

    def test_find_project_with_generic_exception(self):
        sdk_connection = mock.Mock()
        sdk_find_project = sdk_connection.identity.find_project
        exc = exceptions.HttpException()
        # Some value other than 403.
        exc.status_code = 499
        sdk_find_project.side_effect = exc

        with testtools.ExpectedException(exceptions.HttpException):
            cli_identity.find_project(sdk_connection, 'project1')
