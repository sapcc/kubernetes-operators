# Copyright (c) 2015 Thales Services SAS
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

import uuid

import mock


from designateclient import exceptions
from designateclient.tests import base
from designateclient import utils


LIST_MOCK_RESPONSE = [
    {'id': '13579bdf-0000-0000-abcd-000000000001', 'name': 'abcd'},
    {'id': '13579bdf-0000-0000-baba-000000000001', 'name': 'baba'},
    {'id': '13579bdf-0000-0000-baba-000000000002', 'name': 'baba'},
]


class UtilsTestCase(base.TestCase):

    def _find_resourceid_by_name_or_id(self, name_or_id, by_name=False):
        resource_client = mock.Mock()
        resource_client.list.return_value = LIST_MOCK_RESPONSE
        resourceid = utils.find_resourceid_by_name_or_id(
            resource_client, name_or_id)
        self.assertEqual(by_name, resource_client.list.called)
        return resourceid

    def test_find_resourceid_with_hyphen_uuid(self):
        expected = str(uuid.uuid4())
        observed = self._find_resourceid_by_name_or_id(expected)
        self.assertEqual(expected, observed)

    def test_find_resourceid_with_nonhyphen_uuid(self):
        expected = str(uuid.uuid4())
        fakeid = expected.replace('-', '')
        observed = self._find_resourceid_by_name_or_id(fakeid)
        self.assertEqual(expected, observed)

    def test_find_resourceid_with_unique_resource(self):
        observed = self._find_resourceid_by_name_or_id('abcd', by_name=True)
        self.assertEqual('13579bdf-0000-0000-abcd-000000000001', observed)

    def test_find_resourceid_with_nonexistent_resource(self):
        self.assertRaises(exceptions.ResourceNotFound,
                          self._find_resourceid_by_name_or_id,
                          'taz', by_name=True)

    def test_find_resourceid_with_multiple_resources(self):
        self.assertRaises(exceptions.NoUniqueMatch,
                          self._find_resourceid_by_name_or_id,
                          'baba', by_name=True)

    def test_load_schema(self):
        schema = utils.load_schema('v1', 'domain')
        self.assertIsInstance(schema, dict)

    def test_load_schema_missing(self):
        self.assertRaises(exceptions.ResourceNotFound, utils.load_schema,
                          'v1', 'missing')

    def test_resource_string_empty_param(self):
        self.assertRaises(ValueError, utils.resource_string)

    def test_resource_string(self):
        name = ['schemas', 'v1', 'domain.json']
        resource_string = utils.resource_string(*name)
        self.assertIsNotNone(resource_string)

    def test_resource_string_missing(self):
        name = ['schemas', 'v1', 'missing']
        self.assertRaises(exceptions.ResourceNotFound, utils.resource_string,
                          *name)
