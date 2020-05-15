# Copyright 2015 Rackspace Inc.
#
# Author: James Li <james.li@rackspace.com>
#
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

from designateclient import exceptions
from designateclient.tests import base


class RemoteErrorTestCase(base.TestCase):
    response_dict = {
        'message': None,
        'code': 500,
        'type': None,
        'errors': None,
        'request_id': 1234
    }

    def test_get_error_message(self):
        expected_msg = 'something wrong'
        self.response_dict['message'] = expected_msg
        remote_err = exceptions.RemoteError(**self.response_dict)
        self.assertEqual(expected_msg, remote_err.message)

    def test_get_error_message_with_errors(self):
        expected_msg = "u'nodot.com' is not a 'domainname'"
        errors = {"errors": [
            {"path": ["name"],
             "message": expected_msg,
             "validator": "format",
             "validator_value": "domainname"}
        ]
        }
        self.response_dict['message'] = None
        self.response_dict['errors'] = errors
        remote_err = exceptions.RemoteError(**self.response_dict)
        self.assertEqual(expected_msg, remote_err.message)

    def test_get_error_message_with_type(self):
        expected_msg = 'invalid_object'
        self.response_dict['message'] = None
        self.response_dict['errors'] = None
        self.response_dict['type'] = expected_msg
        remote_err = exceptions.RemoteError(**self.response_dict)
        self.assertEqual(expected_msg, remote_err.message)

    def test_get_error_message_with_unknown_response(self):
        expected_msg = 'invalid_object'
        self.response_dict['message'] = expected_msg
        self.response_dict['unknown'] = 'fake'
        remote_err = exceptions.RemoteError(**self.response_dict)
        self.assertEqual(expected_msg, remote_err.message)
