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

import json

import mock
import six

import keystoneauth1.exceptions.http as ks_exceptions
import osc_lib.exceptions as exceptions
import oslotest.base as base

import osc_placement.http as http


class TestSessionClient(base.BaseTestCase):
    def test_wrap_http_exceptions(self):
        def go():
            with http._wrap_http_exceptions():
                error = {
                    "errors": [
                        {"status": 404,
                         "detail": ("The resource could not be found.\n\n"
                                    "No resource provider with uuid 123 "
                                    "found for delete")}
                    ]
                }
                response = mock.Mock(content=json.dumps(error))
                raise ks_exceptions.NotFound(response=response)

        exc = self.assertRaises(exceptions.NotFound, go)
        self.assertEqual(404, exc.http_status)
        self.assertIn('No resource provider with uuid 123 found',
                      six.text_type(exc))
