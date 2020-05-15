#   Copyright 2017 Huawei, Inc. All rights reserved.
#
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
#

from osc_lib.cli import format_columns
from osc_lib.tests import utils


class TestDictColumn(utils.TestCase):

    def test_dict_column(self):
        dict_content = {
            'key1': 'value1',
            'key2': 'value2',
        }
        col = format_columns.DictColumn(dict_content)
        self.assertEqual(dict_content, col.machine_readable())
        self.assertEqual("key1='value1', key2='value2'", col.human_readable())


class TestDictListColumn(utils.TestCase):

    def test_dict_list_column(self):
        dict_list_content = {'public': ['2001:db8::8', '172.24.4.6'],
                             'private': ['2000:db7::7', '192.24.4.6']}
        col = format_columns.DictListColumn(dict_list_content)
        self.assertEqual(dict_list_content, col.machine_readable())
        self.assertEqual('private=192.24.4.6, 2000:db7::7; '
                         'public=172.24.4.6, 2001:db8::8',
                         col.human_readable())


class TestListColumn(utils.TestCase):

    def test_list_column(self):
        list_content = [
            'key1',
            'key2',
        ]
        col = format_columns.ListColumn(list_content)
        self.assertEqual(list_content, col.machine_readable())
        self.assertEqual("key1, key2", col.human_readable())


class TestListDictColumn(utils.TestCase):

    def test_list_dict_column(self):
        list_dict_content = [
            {'key1': 'value1'},
            {'key2': 'value2'},
        ]
        col = format_columns.ListDictColumn(list_dict_content)
        self.assertEqual(list_dict_content, col.machine_readable())
        self.assertEqual("key1='value1'\nkey2='value2'", col.human_readable())
