# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import six
import testtools

from manilaclient import utils


class TestCommonUtils(testtools.TestCase):

    def test_unicode_key_value_to_string(self):
        src = {u'key': u'\u70fd\u7231\u5a77'}
        expected = {'key': '\xe7\x83\xbd\xe7\x88\xb1\xe5\xa9\xb7'}
        if six.PY2:
            self.assertEqual(expected, utils.unicode_key_value_to_string(src))
        else:
            # u'xxxx' in PY3 is str, we will not get extra 'u' from cli
            # output in PY3
            self.assertEqual(src, utils.unicode_key_value_to_string(src))
