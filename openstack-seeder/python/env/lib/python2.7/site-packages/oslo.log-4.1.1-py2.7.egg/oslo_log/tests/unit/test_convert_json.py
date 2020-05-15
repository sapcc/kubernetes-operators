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

import io

from oslo_log.cmds import convert_json
from oslo_serialization import jsonutils
from oslotest import base as test_base


TRIVIAL_RECORD = {'message': 'msg'}
DEBUG_LEVELNAME_RECORD = {
    'message': 'msg',
    'levelname': 'DEBUG',
}
DEBUG_LEVELNO_RECORD = {
    'message': 'msg',
    'levelno': 0,
}
TRACEBACK_RECORD = {
    'message': 'msg',
    'traceback': "abc\ndef",
}
DEBUG_LEVEL_KEY_RECORD = {
    'message': 'msg',
    'level': 'DEBUG',
}
EXCEPTION_RECORD = {
    'message': 'msg',
    'exception': "abc\ndef",
}


class ConvertJsonTestCase(test_base.BaseTestCase):
    def setUp(self):
        super(ConvertJsonTestCase, self).setUp()

    def _reformat(self, text):
        fh = io.StringIO(text)
        return list(convert_json.reformat_json(fh, lambda x: [x]))

    def test_reformat_json_single(self):
        text = jsonutils.dumps(TRIVIAL_RECORD)
        self.assertEqual([TRIVIAL_RECORD], self._reformat(text))

    def test_reformat_json_blanks(self):
        text = jsonutils.dumps(TRIVIAL_RECORD)
        self.assertEqual([TRIVIAL_RECORD], self._reformat(text + "\n\n"))

    def test_reformat_json_double(self):
        text = jsonutils.dumps(TRIVIAL_RECORD)
        self.assertEqual(
            [TRIVIAL_RECORD, TRIVIAL_RECORD],
            self._reformat("\n".join([text, text])))

    def _lines(self, record, pre='pre', loc='loc', **args):
        return list(convert_json.console_format(pre, loc, record, **args))

    def test_console_format_trivial(self):
        lines = self._lines(TRIVIAL_RECORD)
        self.assertEqual(['pre msg'], lines)

    def test_console_format_debug_levelname(self):
        lines = self._lines(DEBUG_LEVELNAME_RECORD)
        self.assertEqual(['pre msg'], lines)

    def test_console_format_debug_levelno(self):
        lines = self._lines(DEBUG_LEVELNO_RECORD)
        self.assertEqual(['pre msg'], lines)

    def test_console_format_debug_level_key(self):
        lines = self._lines(DEBUG_LEVEL_KEY_RECORD, level_key='level')
        self.assertEqual(['pre msg'], lines)

    def test_console_format_traceback(self):
        lines = self._lines(TRACEBACK_RECORD)
        self.assertEqual(['pre msg', 'pre abc', 'pre def'], lines)

    def test_console_format_exception(self):
        lines = self._lines(EXCEPTION_RECORD, traceback_key='exception')
        self.assertEqual(['pre msg', 'pre abc', 'pre def'], lines)
