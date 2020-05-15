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

import mock

import oslotest.base as base

from osc_placement import version


class TestVersion(base.BaseTestCase):
    def test_compare(self):
        self.assertTrue(version._compare('1.0', version.gt('0.9')))
        self.assertTrue(version._compare('1.0', version.ge('0.9')))
        self.assertTrue(version._compare('1.0', version.ge('1.0')))
        self.assertTrue(version._compare('1.0', version.eq('1.0')))
        self.assertTrue(version._compare('1.0', version.le('1.0')))
        self.assertTrue(version._compare('1.0', version.le('1.1')))
        self.assertTrue(version._compare('1.0', version.lt('1.1')))
        self.assertTrue(
            version._compare('1.1', version.gt('1.0'), version.lt('1.2')))
        self.assertTrue(
            version._compare(
                '0.3', version.eq('0.2'), version.eq('0.3'), op=any))
        self.assertFalse(version._compare('1.0', version.gt('1.0')))
        self.assertFalse(version._compare('1.0', version.ge('1.1')))
        self.assertFalse(version._compare('1.0', version.eq('1.1')))
        self.assertFalse(version._compare('1.0', version.le('0.9')))
        self.assertFalse(version._compare('1.0', version.lt('0.9')))
        self.assertRaises(
            ValueError, version._compare, 'abc', version.le('1.1'))
        self.assertRaises(
            ValueError, version._compare, '1.0', version.le('.0'))
        self.assertRaises(
            ValueError, version._compare, '1', version.le('2'))

    def test_compare_with_exc(self):
        self.assertTrue(version.compare('1.05', version.gt('1.4')))
        self.assertFalse(version.compare('1.3', version.gt('1.4'), exc=False))
        self.assertRaisesRegex(
            ValueError,
            'Operation or argument is not supported',
            version.compare, '3.1.2', version.gt('3.1.3'))

    def test_check_decorator(self):
        fake_api = mock.Mock()
        fake_api_dec = version.check(version.gt('2.11'))(fake_api)
        obj = mock.Mock()
        obj.app.client_manager.placement.api_version = '2.12'
        fake_api_dec(obj, 1, 2, 3)
        fake_api.assert_called_once_with(obj, 1, 2, 3)
        fake_api.reset_mock()
        obj.app.client_manager.placement.api_version = '2.10'
        self.assertRaisesRegex(
            ValueError,
            'Operation or argument is not supported',
            fake_api_dec,
            obj, 1, 2, 3)
        fake_api.assert_not_called()

    def test_check_mixin(self):

        class Test(version.CheckerMixin):
            app = mock.Mock()
            app.client_manager.placement.api_version = '1.2'

        t = Test()
        self.assertTrue(t.compare_version(version.le('1.3')))
        self.assertTrue(t.check_version(version.ge('1.0')))
        self.assertRaisesRegex(
            ValueError,
            'Operation or argument is not supported',
            t.check_version, version.lt('1.2'))
