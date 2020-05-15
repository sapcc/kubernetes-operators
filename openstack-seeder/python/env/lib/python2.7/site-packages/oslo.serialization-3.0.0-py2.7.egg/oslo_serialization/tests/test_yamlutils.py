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

import os
import tempfile
import textwrap
import uuid

from oslotest import base

from oslo_serialization import yamlutils as yaml


class BehaviorTestCase(base.BaseTestCase):

    def test_loading(self):
        payload = textwrap.dedent('''
            - foo: bar
            - list:
            - [one, two]
            - {check: yaml, in: test}
        ''')
        expected = [
            {'foo': 'bar'},
            {'list': None},
            ['one', 'two'],
            {'check': 'yaml', 'in': 'test'}
        ]
        loaded = yaml.load(payload)
        self.assertEqual(loaded, expected)

    def test_loading_with_unsafe(self):
        payload = textwrap.dedent('''
            !!python/object/apply:os.system ['echo "hello"']
        ''')
        loaded = yaml.load(payload, is_safe=False)
        expected = 0
        self.assertEqual(loaded, expected)

    def test_dumps(self):
        payload = [
            {'foo': 'bar'},
            {'list': None},
            ['one', 'two'],
            {'check': 'yaml', 'in': 'test'}
        ]
        dumped = yaml.dumps(payload)
        expected = textwrap.dedent('''\
            - foo: bar
            - list: null
            - - one
              - two
            - check: yaml
              in: test
        ''')
        self.assertEqual(dumped, expected)

    def test_dump(self):
        payload = [
            {'foo': 'bar'},
            {'list': None},
            ['one', 'two'],
            {'check': 'yaml', 'in': 'test'}
        ]
        tmpfile = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
        with open(tmpfile, 'w+') as fp:
            yaml.dump(payload, fp)
        with open(tmpfile, 'r') as fp:
            file_content = fp.read()
            expected = textwrap.dedent('''\
                - foo: bar
                - list: null
                - - one
                  - two
                - check: yaml
                  in: test
            ''')
            self.assertEqual(file_content, expected)
