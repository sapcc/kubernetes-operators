# Copyright 2015 IBM Corp.
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

"""Tests the cinderclient.exceptions module."""

import datetime
import mock
import requests

from cinderclient import exceptions
from cinderclient.tests.unit import utils


class ExceptionsTest(utils.TestCase):

    def test_from_response_no_body_message(self):
        # Tests that we get ClientException back since we don't have 500 mapped
        response = requests.Response()
        response.status_code = 500
        body = {'keys': ({})}
        ex = exceptions.from_response(response, body)
        self.assertIs(exceptions.ClientException, type(ex))
        self.assertEqual('n/a', ex.message)

    def test_from_response_overlimit(self):
        response = requests.Response()
        response.status_code = 413
        response.headers = {"Retry-After": '10'}
        body = {'keys': ({})}
        ex = exceptions.from_response(response, body)
        self.assertEqual(10, ex.retry_after)
        self.assertIs(exceptions.OverLimit, type(ex))

    @mock.patch('oslo_utils.timeutils.utcnow',
                return_value=datetime.datetime(2016, 6, 30, 12, 41, 55))
    def test_from_response_overlimit_gmt(self, mock_utcnow):
        response = requests.Response()
        response.status_code = 413
        response.headers = {"Retry-After": "Thu, 30 Jun 2016 12:43:20 GMT"}
        body = {'keys': ({})}
        ex = exceptions.from_response(response, body)
        self.assertEqual(85, ex.retry_after)
        self.assertIs(exceptions.OverLimit, type(ex))
        self.assertTrue(mock_utcnow.called)

    def test_from_response_overlimit_without_header(self):
        response = requests.Response()
        response.status_code = 413
        response.headers = {}
        body = {'keys': ({})}
        ex = exceptions.from_response(response, body)
        self.assertEqual(0, ex.retry_after)
        self.assertIs(exceptions.OverLimit, type(ex))
