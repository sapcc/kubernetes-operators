# coding: utf-8
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

import collections

import oslotest.base as base

import osc_placement.resources.common as common


class TestCommon(base.BaseTestCase):
    def test_encode(self):
        self.assertEqual(u'привет'.encode('utf-8'),
                         common.encode(u'привет'))

    def test_encode_custom_encoding(self):
        self.assertEqual(u'привет'.encode('utf-16'),
                         common.encode(u'привет', 'utf-16'))

    def test_encode_non_string(self):
        self.assertEqual(b'bytesvalue',
                         common.encode(b'bytesvalue'))

    def test_url_with_filters(self):
        base_url = '/resource_providers'
        expected = '/resource_providers?name=test&uuid=123456'

        filters = collections.OrderedDict([('name', 'test'), ('uuid', 123456)])

        actual = common.url_with_filters(base_url, filters)
        self.assertEqual(expected, actual)

    def test_url_with_filters_empty(self):
        base_url = '/resource_providers'

        self.assertEqual(base_url, common.url_with_filters(base_url))
        self.assertEqual(base_url, common.url_with_filters(base_url, {}))

    def test_url_with_filters_unicode_string(self):
        base_url = '/resource_providers'
        expected = ('/resource_providers?'
                    'name=%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82')

        actual = common.url_with_filters(base_url, {'name': u'привет'})
        self.assertEqual(expected, actual)
