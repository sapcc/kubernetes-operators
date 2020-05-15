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

import ddt

from manilaclient.tests.functional import utils as func_utils
from manilaclient.tests.unit import utils


@ddt.ddt
class ShellTest(utils.TestCase):

    OUTPUT_LINES_SIMPLE = """
+----+------+---------+
| ID | Name | Status  |
+----+------+---------+
| 11 | foo  | BUILD   |
| 21 | bar  | ERROR   |
+----+------+---------+
"""
    OUTPUT_LINES_ONE_MULTI_ROW = """
+----+------+---------+
| ID | Name | Status  |
+----+------+---------+
| 11 | foo  | BUILD   |
| 21 | bar  | ERROR   |
|    |      | ERROR2  |
| 31 | bee  | None    |
+----+------+---------+
"""

    OUTPUT_LINES_COMPLICATED_MULTI_ROW = """
+----+------+---------+
| ID | Name | Status  |
+----+------+---------+
| 11 | foo  | BUILD   |
| 21 | bar  | ERROR   |
|    |      | ERROR2  |
|    |      | ERROR3  |
| 31 | bee  | None    |
|    | bee2 |         |
|    | bee3 |         |
| 41 | rand | None    |
|    | rend | None2   |
|    |      |         |
+----+------+---------+
"""

    OUTPUT_LINES_COMPLICATED_MULTI_ROW_WITH_SHIFTED_ID = """
+----+----+------+---------+
| ** | ID | Name | Status  |
+----+----+------+---------+
| ** | 11 | foo  | BUILD   |
|    | 21 | bar  | ERROR   |
|    |    |      | ERROR2  |
|    |    |      | ERROR3  |
|    |    |      |         |
| ** | 31 | bee  | None    |
|    |    | bee2 |         |
|    |    |      |         |
+----+----+------+---------+
"""

    OUTPUT_LINES_NESTED_TABLE = """
+----+----+------+--------------+
| ** | ID | Name | Status       |
+----+----+------+--------------+
| ** | 11 | foo  | +----+----+  |
|    |    |      | | aa | bb |  |
|    |    |      | +----+----+  |
|    |    |      | +----+----+  |
|    | 21 | bar  | ERROR        |
|    |    |      | ERROR2       |
|    |    |      | ERROR3       |
+----+----+------+--------------+
"""
    OUTPUT_LINES_NESTED_TABLE_MULTI_LINE = """
+----+----+------+--------------+
| ** | ID | Name | Status       |
+----+----+------+--------------+
| ** | 11 | foo  | +----+----+  |
|    |    |      | | id | bb |  |
|    |    |      | +----+----+  |
|    |    |      | | 01 | a1 |  |
|    |    |      | |    | a2 |  |
|    |    |      | +----+----+  |
|    | 21 | bar  | ERROR        |
|    |    |      | ERROR2       |
|    |    |      | ERROR3       |
+----+----+------+--------------+
"""
    OUTPUT_LINES_DETAILS = """
+----------+--------+
| Property | Value  |
+----------+--------+
| foo      | BUILD  |
| bar      | ERROR  |
|          | ERROR2 |
|          | ERROR3 |
| bee      | None   |
+----------+--------+
"""

    @ddt.data({'input': OUTPUT_LINES_SIMPLE,
               'valid_values': [
                   ['11', 'foo', 'BUILD'],
                   ['21', 'bar', 'ERROR']
               ]},
              {'input': OUTPUT_LINES_ONE_MULTI_ROW,
               'valid_values': [
                   ['11', 'foo', 'BUILD'],
                   ['21', 'bar', ['ERROR', 'ERROR2']],
                   ['31', 'bee', 'None'],
               ]},
              {'input': OUTPUT_LINES_COMPLICATED_MULTI_ROW,
               'valid_values': [
                   ['11', 'foo', 'BUILD'],
                   ['21', 'bar', ['ERROR', 'ERROR2', 'ERROR3']],
                   ['31', ['bee', 'bee2', 'bee3'], 'None'],
                   ['41', ['rand', 'rend'], ['None', 'None2']],
                   ['', '', '']
               ]})
    @ddt.unpack
    def test_multi_line_row_table(self, input, valid_values):

        actual_result = func_utils.multi_line_row_table(input)

        self.assertEqual(['ID', 'Name', 'Status'], actual_result['headers'])
        self.assertEqual(valid_values, actual_result['values'])

    def test_multi_line_row_table_shifted_id_column(self):
        input = self.OUTPUT_LINES_COMPLICATED_MULTI_ROW_WITH_SHIFTED_ID
        valid_values = [
            ['**', '11', 'foo', 'BUILD'],
            ['', '21', 'bar', ['ERROR', 'ERROR2', 'ERROR3']],
            ['', '', '', ''],
            ['**', '31', ['bee', 'bee2'], 'None'],
            ['', '', '', '']
        ]

        actual_result = func_utils.multi_line_row_table(
            input, group_by_column_index=1)

        self.assertEqual(['**', 'ID', 'Name', 'Status'],
                         actual_result['headers'])
        self.assertEqual(valid_values, actual_result['values'])

    @ddt.data({'input': OUTPUT_LINES_NESTED_TABLE,
               'valid_nested': {
                   'headers': ['aa', 'bb'],
                   'values': []
               }},
              {'input': OUTPUT_LINES_NESTED_TABLE_MULTI_LINE,
               'valid_nested': {
                   'headers': ['id', 'bb'],
                   'values': [['01', ['a1', 'a2']]]
               }},)
    @ddt.unpack
    def test_nested_tables(self, input, valid_nested):

        actual_result = func_utils.multi_line_row_table(
            input, group_by_column_index=1)

        self.assertEqual(['**', 'ID', 'Name', 'Status'],
                         actual_result['headers'])

        self.assertEqual(2, len(actual_result['values']))
        self.assertEqual(valid_nested, actual_result['values'][0][3])

    @ddt.data({'input': OUTPUT_LINES_DETAILS,
               'valid_values': [
                   ['foo', 'BUILD'],
                   ['bar', ['ERROR', 'ERROR2', 'ERROR3']],
                   ['bee', 'None'],
               ]})
    @ddt.unpack
    def test_details(self, input, valid_values):
        actual_result = func_utils.multi_line_row_table(input)

        self.assertEqual(['Property', 'Value'], actual_result['headers'])
        self.assertEqual(valid_values, actual_result['values'])

    @ddt.data({'input_data': OUTPUT_LINES_DETAILS,
               'output_data': [
                   {'Property': 'foo', 'Value': 'BUILD'},
                   {'Property': 'bar', 'Value': ['ERROR', 'ERROR2', 'ERROR3']},
                   {'Property': 'bee', 'Value': 'None'}]},
              {'input_data': OUTPUT_LINES_SIMPLE,
               'output_data': [
                   {'ID': '11', 'Name': 'foo', 'Status': 'BUILD'},
                   {'ID': '21', 'Name': 'bar', 'Status': 'ERROR'},
               ]},
              {'input_data': OUTPUT_LINES_ONE_MULTI_ROW,
               'output_data': [
                   {'ID': '11', 'Name': 'foo', 'Status': 'BUILD'},
                   {'ID': '21', 'Name': 'bar', 'Status': ['ERROR', 'ERROR2']},
                   {'ID': '31', 'Name': 'bee', 'Status': 'None'},
               ]},
              {'input_data': OUTPUT_LINES_COMPLICATED_MULTI_ROW,
               'output_data': [
                   {'ID': '11', 'Name': 'foo', 'Status': 'BUILD'},
                   {'ID': '21', 'Name': 'bar',
                    'Status': ['ERROR', 'ERROR2', 'ERROR3']},
                   {'ID': '31', 'Name': ['bee', 'bee2', 'bee3'],
                    'Status': 'None'},
                   {'ID': '41', 'Name': ['rand', 'rend'],
                    'Status': ['None', 'None2']},
                   {'ID': '', 'Name': '', 'Status': ''},
               ]})
    @ddt.unpack
    def test_listing(self, input_data, output_data):
        actual_result = func_utils.listing(input_data)
        self.assertEqual(output_data, actual_result)
