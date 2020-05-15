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

from unittest import mock

from oslotest import base as test_base

from oslo_log import helpers


class LogHelpersTestCase(test_base.BaseTestCase):

    def test_log_decorator(self):
        '''Test that LOG.debug is called with proper arguments.'''

        class test_class(object):
            @helpers.log_method_call
            def test_method(self, arg1, arg2, arg3, *args, **kwargs):
                pass

            @classmethod
            @helpers.log_method_call
            def test_classmethod(cls, arg1, arg2, arg3, *args, **kwargs):
                pass

        args = tuple(range(6))
        kwargs = {'kwarg1': 6, 'kwarg2': 7}

        obj = test_class()
        for method_name in ('test_method', 'test_classmethod'):
            data = {'caller': helpers._get_full_class_name(test_class),
                    'method_name': method_name,
                    'args': args,
                    'kwargs': kwargs}

            method = getattr(obj, method_name)
            with mock.patch('logging.Logger.debug') as debug:
                method(*args, **kwargs)
                debug.assert_called_with(mock.ANY, data)

    def test_log_decorator_for_static(self):
        '''Test that LOG.debug is called with proper arguments.'''

        @helpers.log_method_call
        def _static_method():
            pass

        class test_class(object):
            @staticmethod
            @helpers.log_method_call
            def test_staticmethod(arg1, arg2, arg3, *args, **kwargs):
                pass

        data = {'caller': 'static',
                'method_name': '_static_method',
                'args': (),
                'kwargs': {}}
        with mock.patch('logging.Logger.debug') as debug:
            _static_method()
            debug.assert_called_with(mock.ANY, data)

        args = tuple(range(6))
        kwargs = {'kwarg1': 6, 'kwarg2': 7}
        data = {'caller': 'static',
                'method_name': 'test_staticmethod',
                'args': args,
                'kwargs': kwargs}
        with mock.patch('logging.Logger.debug') as debug:
            test_class.test_staticmethod(*args, **kwargs)
            debug.assert_called_with(mock.ANY, data)
