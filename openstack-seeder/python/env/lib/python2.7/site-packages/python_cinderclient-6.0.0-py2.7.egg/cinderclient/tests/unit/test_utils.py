# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import ddt
import sys

import mock
import six
from six import moves

from cinderclient import api_versions
from cinderclient.apiclient import base as common_base
from cinderclient import base
from cinderclient import exceptions
from cinderclient import shell_utils
from cinderclient import utils

from cinderclient.tests.unit import utils as test_utils
from cinderclient.tests.unit.v2 import fakes

UUID = '8e8ec658-c7b0-4243-bdf8-6f7f2952c0d0'


class FakeResource(object):
    NAME_ATTR = 'name'

    def __init__(self, _id, properties, **kwargs):
        self.id = _id
        try:
            self.name = properties['name']
        except KeyError:
            pass

    def append_request_ids(self, resp):
        pass


class FakeManager(base.ManagerWithFind):

    resource_class = FakeResource

    resources = [
        FakeResource('1234', {'name': 'entity_one'}),
        FakeResource(UUID, {'name': 'entity_two'}),
        FakeResource('5678', {'name': '9876'})
    ]

    def get(self, resource_id, **kwargs):
        for resource in self.resources:
            if resource.id == str(resource_id):
                return resource
        raise exceptions.NotFound(resource_id)

    def list(self, search_opts, **kwargs):
        return common_base.ListWithMeta(self.resources, fakes.REQUEST_ID)


class FakeManagerWithApi(base.Manager):

    @api_versions.wraps('3.1')
    def return_api_version(self):
        return '3.1'

    @api_versions.wraps('3.2')  # noqa: F811
    def return_api_version(self):
        return '3.2'


class FakeDisplayResource(object):
    NAME_ATTR = 'display_name'

    def __init__(self, _id, properties):
        self.id = _id
        try:
            self.display_name = properties['display_name']
        except KeyError:
            pass

    def append_request_ids(self, resp):
        pass


class FakeDisplayManager(FakeManager):

    resource_class = FakeDisplayResource

    resources = [
        FakeDisplayResource('4242', {'display_name': 'entity_three'}),
    ]


class FindResourceTestCase(test_utils.TestCase):

    def setUp(self):
        super(FindResourceTestCase, self).setUp()
        self.manager = FakeManager(None)

    def test_find_none(self):
        self.manager.find = mock.Mock(side_effect=self.manager.find)
        self.assertRaises(exceptions.CommandError,
                          utils.find_resource,
                          self.manager,
                          'asdf')
        self.assertEqual(2, self.manager.find.call_count)

    def test_find_by_integer_id(self):
        output = utils.find_resource(self.manager, 1234)
        self.assertEqual(self.manager.get('1234'), output)

    def test_find_by_str_id(self):
        output = utils.find_resource(self.manager, '1234')
        self.assertEqual(self.manager.get('1234'), output)

    def test_find_by_uuid(self):
        output = utils.find_resource(self.manager, UUID)
        self.assertEqual(self.manager.get(UUID), output)

    def test_find_by_str_name(self):
        output = utils.find_resource(self.manager, 'entity_one')
        self.assertEqual(self.manager.get('1234'), output)

    def test_find_by_str_displayname(self):
        display_manager = FakeDisplayManager(None)
        output = utils.find_resource(display_manager, 'entity_three')
        self.assertEqual(display_manager.get('4242'), output)

    def test_find_by_group_id(self):
        output = utils.find_resource(self.manager, 1234, is_group=True,
                                     list_volume=True)
        self.assertEqual(self.manager.get('1234', list_volume=True), output)

    def test_find_by_group_name(self):
        display_manager = FakeDisplayManager(None)
        output = utils.find_resource(display_manager, 'entity_three',
                                     is_group=True, list_volume=True)
        self.assertEqual(display_manager.get('4242', list_volume=True),
                         output)


class CaptureStdout(object):
    """Context manager for capturing stdout from statements in its block."""
    def __enter__(self):
        self.real_stdout = sys.stdout
        self.stringio = moves.StringIO()
        sys.stdout = self.stringio
        return self

    def __exit__(self, *args):
        sys.stdout = self.real_stdout
        self.stringio.seek(0)
        self.read = self.stringio.read


@ddt.ddt
class BuildQueryParamTestCase(test_utils.TestCase):

    def test_build_param_without_sort_switch(self):
        dict_param = {
            'key1': 'val1',
            'key2': 'val2',
            'key3': 'val3',
        }
        result = utils.build_query_param(dict_param, True)

        self.assertIn('key1=val1', result)
        self.assertIn('key2=val2', result)
        self.assertIn('key3=val3', result)

    def test_build_param_with_sort_switch(self):
        dict_param = {
            'key1': 'val1',
            'key2': 'val2',
            'key3': 'val3',
        }
        result = utils.build_query_param(dict_param, True)

        expected = "?key1=val1&key2=val2&key3=val3"
        self.assertEqual(expected, result)

    @ddt.data({},
              None,
              {'key1': 'val1', 'key2': None, 'key3': False, 'key4': ''})
    def test_build_param_with_nones(self, dict_param):
        result = utils.build_query_param(dict_param)

        expected = ("key1=val1", "key3=False") if dict_param else ()
        for exp in expected:
            self.assertIn(exp, result)
        if not expected:
            self.assertEqual("", result)


@ddt.ddt
class ExtractFilterTestCase(test_utils.TestCase):

    @ddt.data({'content': ['key1=value1'],
               'expected': {'key1': 'value1'}},
              {'content': ['key1={key2:value2}'],
               'expected': {'key1': {'key2': 'value2'}}},
              {'content': ['key1=value1', 'key2={key22:value22}'],
               'expected': {'key1': 'value1', 'key2': {'key22': 'value22'}}})
    @ddt.unpack
    def test_extract_filters(self, content, expected):
        result = shell_utils.extract_filters(content)
        self.assertEqual(expected, result)


class PrintListTestCase(test_utils.TestCase):

    def test_print_list_with_list(self):
        Row = collections.namedtuple('Row', ['a', 'b'])
        to_print = [Row(a=3, b=4), Row(a=1, b=2)]
        with CaptureStdout() as cso:
            utils.print_list(to_print, ['a', 'b'])
        # Output should be sorted by the first key (a)
        self.assertEqual("""\
+---+---+
| a | b |
+---+---+
| 1 | 2 |
| 3 | 4 |
+---+---+
""", cso.read())

    def test_print_list_with_None_data(self):
        Row = collections.namedtuple('Row', ['a', 'b'])
        to_print = [Row(a=3, b=None), Row(a=1, b=2)]
        with CaptureStdout() as cso:
            utils.print_list(to_print, ['a', 'b'])
        # Output should be sorted by the first key (a)
        self.assertEqual("""\
+---+---+
| a | b |
+---+---+
| 1 | 2 |
| 3 | - |
+---+---+
""", cso.read())

    def test_print_list_with_list_sortby(self):
        Row = collections.namedtuple('Row', ['a', 'b'])
        to_print = [Row(a=4, b=3), Row(a=2, b=1)]
        with CaptureStdout() as cso:
            utils.print_list(to_print, ['a', 'b'], sortby_index=1)
        # Output should be sorted by the second key (b)
        self.assertEqual("""\
+---+---+
| a | b |
+---+---+
| 2 | 1 |
| 4 | 3 |
+---+---+
""", cso.read())

    def test_print_list_with_list_no_sort(self):
        Row = collections.namedtuple('Row', ['a', 'b'])
        to_print = [Row(a=3, b=4), Row(a=1, b=2)]
        with CaptureStdout() as cso:
            utils.print_list(to_print, ['a', 'b'], sortby_index=None)
        # Output should be in the order given
        self.assertEqual("""\
+---+---+
| a | b |
+---+---+
| 3 | 4 |
| 1 | 2 |
+---+---+
""", cso.read())

    def test_print_list_with_generator(self):
        Row = collections.namedtuple('Row', ['a', 'b'])

        def gen_rows():
            for row in [Row(a=1, b=2), Row(a=3, b=4)]:
                yield row
        with CaptureStdout() as cso:
            utils.print_list(gen_rows(), ['a', 'b'])
        self.assertEqual("""\
+---+---+
| a | b |
+---+---+
| 1 | 2 |
| 3 | 4 |
+---+---+
""", cso.read())

    def test_print_list_with_return(self):
        Row = collections.namedtuple('Row', ['a', 'b'])
        to_print = [Row(a=3, b='a\r'), Row(a=1, b='c\rd')]
        with CaptureStdout() as cso:
            utils.print_list(to_print, ['a', 'b'])
        # Output should be sorted by the first key (a)
        self.assertEqual("""\
+---+-----+
| a | b   |
+---+-----+
| 1 | c d |
| 3 | a   |
+---+-----+
""", cso.read())

    def test_unicode_key_value_to_string(self):
        src = {u'key': u'\u70fd\u7231\u5a77'}
        expected = {'key': '\xe7\x83\xbd\xe7\x88\xb1\xe5\xa9\xb7'}
        if six.PY2:
            self.assertEqual(expected, utils.unicode_key_value_to_string(src))
        else:
            # u'xxxx' in PY3 is str, we will not get extra 'u' from cli
            # output in PY3
            self.assertEqual(src, utils.unicode_key_value_to_string(src))


class PrintDictTestCase(test_utils.TestCase):

    def test__pretty_format_dict(self):
        content = {'key1': 'value1', 'key2': 'value2'}
        expected = "key1 : value1\nkey2 : value2"
        result = utils._pretty_format_dict(content)
        self.assertEqual(expected, result)

    def test_print_dict_with_return(self):
        d = {'a': 'A', 'b': 'B', 'c': 'C', 'd': 'test\rcarriage\n\rreturn'}
        with CaptureStdout() as cso:
            utils.print_dict(d)
        self.assertEqual("""\
+----------+---------------+
| Property | Value         |
+----------+---------------+
| a        | A             |
| b        | B             |
| c        | C             |
| d        | test carriage |
|          |  return       |
+----------+---------------+
""", cso.read())

    def test_print_dict_with_dict_inside(self):
        content = {'a': 'A', 'b': 'B', 'f_key':
                   {'key1': 'value1', 'key2': 'value2'}}
        with CaptureStdout() as cso:
            utils.print_dict(content, formatters='f_key')
        self.assertEqual("""\
+----------+---------------+
| Property | Value         |
+----------+---------------+
| a        | A             |
| b        | B             |
| f_key    | key1 : value1 |
|          | key2 : value2 |
+----------+---------------+
""", cso.read())
