#   Copyright 2012-2013 OpenStack Foundation
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

import six
import time
import uuid

from cliff import columns as cliff_columns
import mock

from osc_lib.cli import format_columns
from osc_lib import exceptions
from osc_lib.tests import fakes
from osc_lib.tests import utils as test_utils
from osc_lib import utils

PASSWORD = "Pa$$w0rd"
WASSPORD = "Wa$$p0rd"
DROWSSAP = "dr0w$$aP"


class FakeOddballResource(fakes.FakeResource):

    def get(self, attr):
        """get() is needed for utils.find_resource()"""
        if attr == 'id':
            return self.id
        elif attr == 'name':
            return self.name
        else:
            return None


class TestUtils(test_utils.TestCase):

    def _get_test_items(self):
        item1 = {'a': 1, 'b': 2}
        item2 = {'a': 1, 'b': 3}
        item3 = {'a': 2, 'b': 2}
        item4 = {'a': 2, 'b': 1}
        return [item1, item2, item3, item4]

    def test_find_min_match_no_sort(self):
        items = self._get_test_items()
        sort_str = None
        flair = {}
        expect_items = items
        self.assertEqual(
            expect_items,
            list(utils.find_min_match(items, sort_str, **flair)),
        )

    def test_find_min_match_no_flair(self):
        items = self._get_test_items()
        sort_str = 'b'
        flair = {}
        expect_items = [items[3], items[0], items[2], items[1]]
        self.assertEqual(
            expect_items,
            utils.find_min_match(items, sort_str, **flair),
        )

    def test_find_min_match_a2(self):
        items = self._get_test_items()
        sort_str = 'b'
        flair = {'a': 2}
        expect_items = [items[3], items[2]]
        self.assertEqual(
            expect_items,
            utils.find_min_match(items, sort_str, **flair),
        )

    def test_find_min_match_b2(self):
        items = self._get_test_items()
        sort_str = 'b'
        flair = {'b': 2}
        expect_items = [items[0], items[2], items[1]]
        self.assertEqual(
            expect_items,
            utils.find_min_match(items, sort_str, **flair),
        )

    def test_find_min_match_b5(self):
        items = self._get_test_items()
        sort_str = 'b'
        flair = {'b': 5}
        expect_items = []
        self.assertEqual(
            expect_items,
            utils.find_min_match(items, sort_str, **flair),
        )

    def test_find_min_match_a2_b2(self):
        items = self._get_test_items()
        sort_str = 'b'
        flair = {'a': 2, 'b': 2}
        expect_items = [items[2]]
        self.assertEqual(
            expect_items,
            utils.find_min_match(items, sort_str, **flair),
        )

    def test_get_password_good(self):
        with mock.patch("getpass.getpass", return_value=PASSWORD):
            mock_stdin = mock.Mock()
            mock_stdin.isatty = mock.Mock()
            mock_stdin.isatty.return_value = True
            self.assertEqual(PASSWORD, utils.get_password(mock_stdin))

    def test_get_password_bad_once(self):
        answers = [PASSWORD, WASSPORD, DROWSSAP, DROWSSAP]
        with mock.patch("getpass.getpass", side_effect=answers):
            mock_stdin = mock.Mock()
            mock_stdin.isatty = mock.Mock()
            mock_stdin.isatty.return_value = True
            self.assertEqual(DROWSSAP, utils.get_password(mock_stdin))

    def test_get_password_no_tty(self):
        mock_stdin = mock.Mock()
        mock_stdin.isatty = mock.Mock()
        mock_stdin.isatty.return_value = False
        self.assertRaises(exceptions.CommandError,
                          utils.get_password,
                          mock_stdin)

    def test_get_password_cntrl_d(self):
        with mock.patch("getpass.getpass", side_effect=EOFError()):
            mock_stdin = mock.Mock()
            mock_stdin.isatty = mock.Mock()
            mock_stdin.isatty.return_value = True
            self.assertRaises(exceptions.CommandError,
                              utils.get_password,
                              mock_stdin)

    def test_sort_items_with_one_key(self):
        items = self._get_test_items()
        sort_str = 'b'
        expect_items = [items[3], items[0], items[2], items[1]]
        self.assertEqual(expect_items, utils.sort_items(items, sort_str))

    def test_sort_items_with_multiple_keys(self):
        items = self._get_test_items()
        sort_str = 'a,b'
        expect_items = [items[0], items[1], items[3], items[2]]
        self.assertEqual(expect_items, utils.sort_items(items, sort_str))

    def test_sort_items_all_with_direction(self):
        items = self._get_test_items()
        sort_str = 'a:desc,b:desc'
        expect_items = [items[2], items[3], items[1], items[0]]
        self.assertEqual(expect_items, utils.sort_items(items, sort_str))

    def test_sort_items_some_with_direction(self):
        items = self._get_test_items()
        sort_str = 'a,b:desc'
        expect_items = [items[1], items[0], items[2], items[3]]
        self.assertEqual(expect_items, utils.sort_items(items, sort_str))

    def test_sort_items_with_object(self):
        item1 = mock.Mock(a=1, b=2)
        item2 = mock.Mock(a=1, b=3)
        item3 = mock.Mock(a=2, b=2)
        item4 = mock.Mock(a=2, b=1)
        items = [item1, item2, item3, item4]
        sort_str = 'b,a'
        expect_items = [item4, item1, item3, item2]
        self.assertEqual(expect_items, utils.sort_items(items, sort_str))

    def test_sort_items_with_empty_key(self):
        items = self._get_test_items()
        sort_srt = ''
        self.assertEqual(items, utils.sort_items(items, sort_srt))
        sort_srt = None
        self.assertEqual(items, utils.sort_items(items, sort_srt))

    def test_sort_items_with_invalid_key(self):
        items = self._get_test_items()
        sort_str = 'c'
        self.assertRaises(exceptions.CommandError,
                          utils.sort_items,
                          items, sort_str)

    def test_sort_items_with_invalid_direction(self):
        items = self._get_test_items()
        sort_str = 'a:bad_dir'
        self.assertRaises(exceptions.CommandError,
                          utils.sort_items,
                          items, sort_str)

    def test_sort_items_with_different_type_exception(self):
        item1 = {'a': 2}
        item2 = {'a': 3}
        item3 = {'a': None}
        item4 = {'a': 1}
        items = [item1, item2, item3, item4]
        sort_str = 'a'
        expect_items = [item3, item4, item1, item2]
        if six.PY2:
            self.assertEqual(expect_items, utils.sort_items(items, sort_str))
        else:
            self.assertRaises(TypeError, utils.sort_items, items, sort_str)

    def test_sort_items_with_different_type_int(self):
        item1 = {'a': 2}
        item2 = {'a': 3}
        item3 = {'a': None}
        item4 = {'a': 1}
        items = [item1, item2, item3, item4]
        sort_str = 'a'
        sort_type = int
        expect_items = [item3, item4, item1, item2]
        self.assertEqual(expect_items, utils.sort_items(items, sort_str,
                                                        sort_type))

    def test_sort_items_with_different_type_str(self):
        item1 = {'a': 'a'}
        item2 = {'a': None}
        item3 = {'a': '2'}
        item4 = {'a': 'b'}
        items = [item1, item2, item3, item4]
        sort_str = 'a'
        sort_type = str
        expect_items = [item3, item2, item1, item4]
        self.assertEqual(expect_items, utils.sort_items(items, sort_str,
                                                        sort_type))

    @mock.patch.object(time, 'sleep')
    def test_wait_for_delete_ok(self, mock_sleep):
        # Tests the normal flow that the resource is deleted with a 404 coming
        # back on the 2nd iteration of the wait loop.
        resource = mock.MagicMock(status='ACTIVE', progress=None)
        mock_get = mock.Mock(side_effect=[resource,
                                          exceptions.NotFound(404)])
        manager = mock.MagicMock(get=mock_get)
        res_id = str(uuid.uuid4())
        callback = mock.Mock()
        self.assertTrue(utils.wait_for_delete(manager, res_id,
                                              callback=callback))
        mock_sleep.assert_called_once_with(5)
        callback.assert_called_once_with(0)

    @mock.patch.object(time, 'sleep')
    def test_wait_for_delete_timeout(self, mock_sleep):
        # Tests that we fail if the resource is not deleted before the timeout.
        resource = mock.MagicMock(status='ACTIVE')
        mock_get = mock.Mock(return_value=resource)
        manager = mock.MagicMock(get=mock_get)
        res_id = str(uuid.uuid4())
        self.assertFalse(utils.wait_for_delete(manager, res_id, sleep_time=1,
                                               timeout=1))
        mock_sleep.assert_called_once_with(1)

    @mock.patch.object(time, 'sleep')
    def test_wait_for_delete_error(self, mock_sleep):
        # Tests that we fail if the resource goes to error state while waiting.
        resource = mock.MagicMock(status='ERROR')
        mock_get = mock.Mock(return_value=resource)
        manager = mock.MagicMock(get=mock_get)
        res_id = str(uuid.uuid4())
        self.assertFalse(utils.wait_for_delete(manager, res_id))
        mock_sleep.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_wait_for_delete_error_with_overrides(self, mock_sleep):
        # Tests that we fail if the resource is my_status=failed
        resource = mock.MagicMock(my_status='FAILED')
        mock_get = mock.Mock(return_value=resource)
        manager = mock.MagicMock(get=mock_get)
        res_id = str(uuid.uuid4())
        self.assertFalse(utils.wait_for_delete(manager, res_id,
                                               status_field='my_status',
                                               error_status=['failed']))
        mock_sleep.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_wait_for_delete_error_with_overrides_exception(self, mock_sleep):
        # Tests that we succeed if the resource is specific exception
        mock_get = mock.Mock(side_effect=Exception)
        manager = mock.MagicMock(get=mock_get)
        res_id = str(uuid.uuid4())
        self.assertTrue(utils.wait_for_delete(manager, res_id,
                                              exception_name=['Exception']))
        mock_sleep.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_wait_for_status_ok(self, mock_sleep):
        # Tests the normal flow that the resource is status=active
        resource = mock.MagicMock(status='ACTIVE')
        status_f = mock.Mock(return_value=resource)
        res_id = str(uuid.uuid4())
        self.assertTrue(utils.wait_for_status(status_f, res_id,))
        mock_sleep.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_wait_for_status_ok_with_overrides(self, mock_sleep):
        # Tests the normal flow that the resource is status=complete
        resource = mock.MagicMock(my_status='COMPLETE')
        status_f = mock.Mock(return_value=resource)
        res_id = str(uuid.uuid4())
        self.assertTrue(utils.wait_for_status(status_f, res_id,
                                              status_field='my_status',
                                              success_status=['complete']))
        mock_sleep.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_wait_for_status_error(self, mock_sleep):
        # Tests that we fail if the resource is status=error
        resource = mock.MagicMock(status='ERROR')
        status_f = mock.Mock(return_value=resource)
        res_id = str(uuid.uuid4())
        self.assertFalse(utils.wait_for_status(status_f, res_id))
        mock_sleep.assert_not_called()

    @mock.patch.object(time, 'sleep')
    def test_wait_for_status_error_with_overrides(self, mock_sleep):
        # Tests that we fail if the resource is my_status=failed
        resource = mock.MagicMock(my_status='FAILED')
        status_f = mock.Mock(return_value=resource)
        res_id = str(uuid.uuid4())
        self.assertFalse(utils.wait_for_status(status_f, res_id,
                                               status_field='my_status',
                                               error_status=['failed']))
        mock_sleep.assert_not_called()

    def test_build_kwargs_dict_value_set(self):
        self.assertEqual({'arg_bla': 'bla'},
                         utils.build_kwargs_dict('arg_bla', 'bla'))

    def test_build_kwargs_dict_value_None(self):
        self.assertEqual({}, utils.build_kwargs_dict('arg_bla', None))

    def test_build_kwargs_dict_value_empty_str(self):
        self.assertEqual({}, utils.build_kwargs_dict('arg_bla', ''))

    def test_is_ascii_bytes(self):
        self.assertFalse(utils.is_ascii(b'\xe2'))

    def test_is_ascii_string(self):
        self.assertFalse(utils.is_ascii(u'\u2665'))

    def test_format_size(self):
        self.assertEqual("999", utils.format_size(999))
        self.assertEqual("100K", utils.format_size(100000))
        self.assertEqual("2M", utils.format_size(2000000))
        self.assertEqual(
            "16.4M", utils.format_size(16361280)
        )
        self.assertEqual(
            "1.6G", utils.format_size(1576395005)
        )
        self.assertEqual("0", utils.format_size(None))

    def test_backward_compat_col_lister(self):
        fake_col_headers = ['ID', 'Name', 'Size']
        columns = ['Display Name']
        column_map = {'Display Name': 'Name'}
        results = utils.backward_compat_col_lister(fake_col_headers,
                                                   columns,
                                                   column_map)
        self.assertIsInstance(results, list)
        self.assertIn('Display Name', results)
        self.assertNotIn('Name', results)
        self.assertIn('ID', results)
        self.assertIn('Size', results)

    def test_backward_compat_col_lister_no_specify_column(self):
        fake_col_headers = ['ID', 'Name', 'Size']
        columns = []
        column_map = {'Display Name': 'Name'}
        results = utils.backward_compat_col_lister(fake_col_headers,
                                                   columns,
                                                   column_map)
        self.assertIsInstance(results, list)
        self.assertNotIn('Display Name', results)
        self.assertIn('Name', results)
        self.assertIn('ID', results)
        self.assertIn('Size', results)

    def test_backward_compat_col_lister_with_tuple_headers(self):
        fake_col_headers = ('ID', 'Name', 'Size')
        columns = ['Display Name']
        column_map = {'Display Name': 'Name'}
        results = utils.backward_compat_col_lister(fake_col_headers,
                                                   columns,
                                                   column_map)
        self.assertIsInstance(results, list)
        self.assertIn('Display Name', results)
        self.assertNotIn('Name', results)
        self.assertIn('ID', results)
        self.assertIn('Size', results)

    def test_backward_compat_col_showone(self):
        fake_object = {'id': 'fake-id',
                       'name': 'fake-name',
                       'size': 'fake-size'}
        columns = ['display_name']
        column_map = {'display_name': 'name'}
        results = utils.backward_compat_col_showone(fake_object,
                                                    columns,
                                                    column_map)
        self.assertIsInstance(results, dict)
        self.assertIn('display_name', results)
        self.assertIn('id', results)
        self.assertNotIn('name', results)
        self.assertIn('size', results)

    def test_backward_compat_col_showone_no_specify_column(self):
        fake_object = {'id': 'fake-id',
                       'name': 'fake-name',
                       'size': 'fake-size'}
        columns = []
        column_map = {'display_name': 'name'}
        results = utils.backward_compat_col_showone(fake_object,
                                                    columns,
                                                    column_map)
        self.assertIsInstance(results, dict)
        self.assertNotIn('display_name', results)
        self.assertIn('id', results)
        self.assertIn('name', results)
        self.assertIn('size', results)

    def _test_get_item_properties_with_formatter(self, formatters):
        names = ('id', 'attr')
        item = fakes.FakeResource(info={'id': 'fake-id', 'attr': ['a', 'b']})
        res_id, res_attr = utils.get_item_properties(item, names,
                                                     formatters=formatters)
        self.assertEqual('fake-id', res_id)
        return res_attr

    def test_get_item_properties_with_format_func(self):
        formatters = {'attr': utils.format_list}
        res_attr = self._test_get_item_properties_with_formatter(formatters)
        self.assertEqual(utils.format_list(['a', 'b']), res_attr)

    def test_get_item_properties_with_formattable_column(self):
        formatters = {'attr': format_columns.ListColumn}
        res_attr = self._test_get_item_properties_with_formatter(formatters)
        self.assertIsInstance(res_attr, format_columns.ListColumn)

    def _test_get_dict_properties_with_formatter(self, formatters):
        names = ('id', 'attr')
        item = {'id': 'fake-id', 'attr': ['a', 'b']}
        res_id, res_attr = utils.get_dict_properties(item, names,
                                                     formatters=formatters)
        self.assertEqual('fake-id', res_id)
        return res_attr

    def test_get_dict_properties_with_format_func(self):
        formatters = {'attr': utils.format_list}
        res_attr = self._test_get_dict_properties_with_formatter(formatters)
        self.assertEqual(utils.format_list(['a', 'b']), res_attr)

    def test_get_dict_properties_with_formattable_column(self):
        formatters = {'attr': format_columns.ListColumn}
        res_attr = self._test_get_dict_properties_with_formatter(formatters)
        self.assertIsInstance(res_attr, format_columns.ListColumn)

    def _test_calculate_header_and_attrs(self, parsed_args_columns,
                                         expected_headers, expected_attrs):
        column_headers = ('ID', 'Name', 'Fixed IP Addresses')
        columns = ('id', 'name', 'fixed_ips')
        parsed_args = mock.Mock()
        parsed_args.columns = parsed_args_columns
        ret_headers, ret_attrs = utils.calculate_header_and_attrs(
            column_headers, columns, parsed_args)
        self.assertEqual(expected_headers, ret_headers)
        self.assertEqual(expected_attrs, ret_attrs)
        if parsed_args_columns:
            self.assertEqual(expected_headers, parsed_args.columns)
        else:
            self.assertFalse(parsed_args.columns)

    def test_calculate_header_and_attrs_without_column_arg(self):
        self._test_calculate_header_and_attrs(
            [],
            ('ID', 'Name', 'Fixed IP Addresses'),
            ('id', 'name', 'fixed_ips'))

    def test_calculate_header_and_attrs_with_known_columns(self):
        self._test_calculate_header_and_attrs(
            ['Name', 'ID'],
            ['Name', 'ID'],
            ['name', 'id'])

    def test_calculate_header_and_attrs_with_unknown_columns(self):
        self._test_calculate_header_and_attrs(
            ['Name', 'ID', 'device_id'],
            ['Name', 'ID', 'device_id'],
            ['name', 'id', 'device_id'])

    def test_calculate_header_and_attrs_with_attrname_columns(self):
        self._test_calculate_header_and_attrs(
            ['name', 'id', 'device_id'],
            ['Name', 'ID', 'device_id'],
            ['name', 'id', 'device_id'])

    def test_subtest(self):
        for i in range(3):
            with self.subTest(i=i):
                self.assertEqual(i, i)


class NoUniqueMatch(Exception):
    pass


class TestFindResource(test_utils.TestCase):

    def setUp(self):
        super(TestFindResource, self).setUp()
        self.name = 'legos'
        self.expected = mock.Mock()
        self.manager = mock.Mock()
        self.manager.resource_class = mock.Mock()
        self.manager.resource_class.__name__ = 'lego'

    def test_find_resource_get_int(self):
        self.manager.get = mock.Mock(return_value=self.expected)
        result = utils.find_resource(self.manager, 1)
        self.assertEqual(self.expected, result)
        self.manager.get.assert_called_with(1)

    def test_find_resource_get_int_string(self):
        self.manager.get = mock.Mock(return_value=self.expected)
        result = utils.find_resource(self.manager, "2")
        self.assertEqual(self.expected, result)
        self.manager.get.assert_called_with("2")

    def test_find_resource_get_name_and_domain(self):
        name = 'admin'
        domain_id = '30524568d64447fbb3fa8b7891c10dd6'
        # NOTE(stevemar): we need an iterable side-effect because the same
        # function (manager.get()) is used twice, the first time an exception
        # will happen, then the result will be found, but only after using
        # the domain ID as a query arg
        side_effect = [Exception('Boom!'), self.expected]
        self.manager.get = mock.Mock(side_effect=side_effect)
        result = utils.find_resource(self.manager, name, domain_id=domain_id)
        self.assertEqual(self.expected, result)
        self.manager.get.assert_called_with(name, domain_id=domain_id)

    def test_find_resource_get_uuid(self):
        uuid = '9a0dc2a0-ad0d-11e3-a5e2-0800200c9a66'
        self.manager.get = mock.Mock(return_value=self.expected)
        result = utils.find_resource(self.manager, uuid)
        self.assertEqual(self.expected, result)
        self.manager.get.assert_called_with(uuid)

    def test_find_resource_get_whatever(self):
        self.manager.get = mock.Mock(return_value=self.expected)
        result = utils.find_resource(self.manager, 'whatever')
        self.assertEqual(self.expected, result)
        self.manager.get.assert_called_with('whatever')

    def test_find_resource_find(self):
        self.manager.get = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.find = mock.Mock(return_value=self.expected)
        result = utils.find_resource(self.manager, self.name)
        self.assertEqual(self.expected, result)
        self.manager.get.assert_called_with(self.name)
        self.manager.find.assert_called_with(name=self.name)

    def test_find_resource_find_not_found(self):
        self.manager.get = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.find = mock.Mock(
            side_effect=exceptions.NotFound(404, "2")
        )
        result = self.assertRaises(exceptions.CommandError,
                                   utils.find_resource,
                                   self.manager,
                                   self.name)
        self.assertEqual("No lego with a name or ID of 'legos' exists.",
                         str(result))
        self.manager.get.assert_called_with(self.name)
        self.manager.find.assert_called_with(name=self.name)

    def test_find_resource_list_forbidden(self):
        self.manager.get = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.find = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.list = mock.Mock(
            side_effect=exceptions.Forbidden(403)
        )
        self.assertRaises(exceptions.Forbidden,
                          utils.find_resource,
                          self.manager,
                          self.name)
        self.manager.list.assert_called_with()

    def test_find_resource_find_no_unique(self):
        self.manager.get = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.find = mock.Mock(side_effect=NoUniqueMatch())
        result = self.assertRaises(exceptions.CommandError,
                                   utils.find_resource,
                                   self.manager,
                                   self.name)
        self.assertEqual("More than one lego exists with the name 'legos'.",
                         str(result))
        self.manager.get.assert_called_with(self.name)
        self.manager.find.assert_called_with(name=self.name)

    def test_find_resource_silly_resource(self):
        # We need a resource with no resource_class for this test, start fresh
        self.manager = mock.Mock()
        self.manager.get = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.find = mock.Mock(
            side_effect=AttributeError(
                "'Controller' object has no attribute 'find'",
            )
        )
        silly_resource = FakeOddballResource(
            None,
            {'id': '12345', 'name': self.name},
            loaded=True,
        )
        self.manager.list = mock.Mock(
            return_value=[silly_resource, ],
        )
        result = utils.find_resource(self.manager, self.name)
        self.assertEqual(silly_resource, result)
        self.manager.get.assert_called_with(self.name)
        self.manager.find.assert_called_with(name=self.name)

    def test_find_resource_silly_resource_not_found(self):
        # We need a resource with no resource_class for this test, start fresh
        self.manager = mock.Mock()
        self.manager.get = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.find = mock.Mock(
            side_effect=AttributeError(
                "'Controller' object has no attribute 'find'",
            )
        )
        self.manager.list = mock.Mock(return_value=[])
        result = self.assertRaises(exceptions.CommandError,
                                   utils.find_resource,
                                   self.manager,
                                   self.name)
        self.assertEqual("Could not find resource legos",
                         str(result))
        self.manager.get.assert_called_with(self.name)
        self.manager.find.assert_called_with(name=self.name)

    def test_find_resource_silly_resource_no_unique_match(self):
        # We need a resource with no resource_class for this test, start fresh
        self.manager = mock.Mock()
        self.manager.get = mock.Mock(side_effect=Exception('Boom!'))
        self.manager.find = mock.Mock(
            side_effect=AttributeError(
                "'Controller' object has no attribute 'find'",
            )
        )
        silly_resource = FakeOddballResource(
            None,
            {'id': '12345', 'name': self.name},
            loaded=True,
        )
        silly_resource_same = FakeOddballResource(
            None,
            {'id': 'abcde', 'name': self.name},
            loaded=True,
        )
        self.manager.list = mock.Mock(return_value=[silly_resource,
                                                    silly_resource_same])
        result = self.assertRaises(exceptions.CommandError,
                                   utils.find_resource,
                                   self.manager,
                                   self.name)
        self.assertEqual("More than one resource exists "
                         "with the name or ID 'legos'.", str(result))
        self.manager.get.assert_called_with(self.name)
        self.manager.find.assert_called_with(name=self.name)

    def test_format_dict(self):
        expected = "a='b', c='d', e='f'"
        self.assertEqual(expected,
                         utils.format_dict({'a': 'b', 'c': 'd', 'e': 'f'}))
        self.assertEqual(expected,
                         utils.format_dict({'e': 'f', 'c': 'd', 'a': 'b'}))
        self.assertIsNone(utils.format_dict(None))

    def test_format_dict_recursive(self):
        expected = "a='b', c.1='d', c.2=''"
        self.assertEqual(
            expected,
            utils.format_dict({'a': 'b', 'c': {'1': 'd', '2': ''}})
        )
        self.assertEqual(
            expected,
            utils.format_dict({'c': {'1': 'd', '2': ''}, 'a': 'b'})
        )
        self.assertIsNone(utils.format_dict(None))

        expected = "a1='A', a2.b1.c1='B', a2.b1.c2=, a2.b2='D'"
        self.assertEqual(
            expected,
            utils.format_dict(
                {
                    'a1': 'A',
                    'a2': {
                        'b1': {
                            'c1': 'B',
                            'c2': None,
                        },
                        'b2': 'D',
                    },
                }
            )
        )
        self.assertEqual(
            expected,
            utils.format_dict(
                {
                    'a2': {
                        'b1': {
                            'c2': None,
                            'c1': 'B',
                        },
                        'b2': 'D',
                    },
                    'a1': 'A',
                }
            )
        )

    def test_format_dict_of_list(self):
        expected = "a=a1, a2; b=b1, b2; c=c1, c2; e="
        self.assertEqual(expected,
                         utils.format_dict_of_list({'a': ['a2', 'a1'],
                                                    'b': ['b2', 'b1'],
                                                    'c': ['c1', 'c2'],
                                                    'd': None,
                                                    'e': []})
                         )
        self.assertEqual(expected,
                         utils.format_dict_of_list({'c': ['c1', 'c2'],
                                                    'a': ['a2', 'a1'],
                                                    'b': ['b2', 'b1'],
                                                    'e': []})
                         )
        self.assertIsNone(utils.format_dict_of_list(None))

    def test_format_dict_of_list_with_separator(self):
        expected = "a=a1, a2\nb=b1, b2\nc=c1, c2\ne="
        self.assertEqual(expected,
                         utils.format_dict_of_list({'a': ['a2', 'a1'],
                                                    'b': ['b2', 'b1'],
                                                    'c': ['c1', 'c2'],
                                                    'd': None,
                                                    'e': []},
                                                   separator='\n')
                         )
        self.assertEqual(expected,
                         utils.format_dict_of_list({'c': ['c1', 'c2'],
                                                    'a': ['a2', 'a1'],
                                                    'b': ['b2', 'b1'],
                                                    'e': []},
                                                   separator='\n')
                         )
        self.assertIsNone(utils.format_dict_of_list(None,
                                                    separator='\n'))

    def test_format_list(self):
        expected = 'a, b, c'
        self.assertEqual(expected, utils.format_list(['a', 'b', 'c']))
        self.assertEqual(expected, utils.format_list(['c', 'b', 'a']))
        self.assertIsNone(utils.format_list(None))

    def test_format_list_of_dicts(self):
        expected = "a='b', c='d'\ne='f'"
        sorted_data = [{'a': 'b', 'c': 'd'}, {'e': 'f'}]
        unsorted_data = [{'c': 'd', 'a': 'b'}, {'e': 'f'}]
        self.assertEqual(expected, utils.format_list_of_dicts(sorted_data))
        self.assertEqual(expected, utils.format_list_of_dicts(unsorted_data))
        self.assertEqual('', utils.format_list_of_dicts([]))
        self.assertEqual('', utils.format_list_of_dicts([{}]))
        self.assertIsNone(utils.format_list_of_dicts(None))

    def test_format_list_separator(self):
        expected = 'a\nb\nc'
        actual_pre_sorted = utils.format_list(['a', 'b', 'c'], separator='\n')
        actual_unsorted = utils.format_list(['c', 'b', 'a'], separator='\n')
        self.assertEqual(expected, actual_pre_sorted)
        self.assertEqual(expected, actual_unsorted)


class TestAssertItemEqual(test_utils.TestCommand):

    def test_assert_normal_item(self):
        expected = ['a', 'b', 'c']
        actual = ['a', 'b', 'c']
        self.assertItemEqual(expected, actual)

    def test_assert_item_with_formattable_columns(self):
        expected = [format_columns.DictColumn({'a': 1, 'b': 2}),
                    format_columns.ListColumn(['x', 'y', 'z'])]
        actual = [format_columns.DictColumn({'a': 1, 'b': 2}),
                  format_columns.ListColumn(['x', 'y', 'z'])]
        self.assertItemEqual(expected, actual)

    def test_assert_item_different_length(self):
        expected = ['a', 'b', 'c']
        actual = ['a', 'b']
        self.assertRaises(AssertionError,
                          self.assertItemEqual, expected, actual)

    def test_assert_item_formattable_columns_vs_legacy_formatter(self):
        expected = [format_columns.DictColumn({'a': 1, 'b': 2}),
                    format_columns.ListColumn(['x', 'y', 'z'])]
        actual = [utils.format_dict({'a': 1, 'b': 2}),
                  utils.format_list(['x', 'y', 'z'])]
        self.assertRaises(AssertionError,
                          self.assertItemEqual, expected, actual)

    def test_assert_item_different_formattable_columns(self):

        class ExceptionColumn(cliff_columns.FormattableColumn):
            def human_readable(self):
                raise Exception('always fail')

        expected = [format_columns.DictColumn({'a': 1, 'b': 2})]
        actual = [ExceptionColumn({'a': 1, 'b': 2})]
        # AssertionError is a subclass of Exception
        # so raising AssertionError ensures ExceptionColumn.human_readable()
        # is not called.
        self.assertRaises(AssertionError,
                          self.assertItemEqual, expected, actual)

    def test_assert_list_item(self):
        expected = [
            ['a', 'b', 'c'],
            [format_columns.DictColumn({'a': 1, 'b': 2}),
             format_columns.ListColumn(['x', 'y', 'z'])]
        ]
        actual = [
            ['a', 'b', 'c'],
            [format_columns.DictColumn({'a': 1, 'b': 2}),
             format_columns.ListColumn(['x', 'y', 'z'])]
        ]
        self.assertListItemEqual(expected, actual)
