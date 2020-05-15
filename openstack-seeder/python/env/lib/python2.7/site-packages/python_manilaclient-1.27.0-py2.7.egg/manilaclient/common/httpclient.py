# Copyright 2010 Jacob Kaplan-Moss
# Copyright 2011 OpenStack Foundation
# Copyright 2011 Piston Cloud Computing, Inc.
# Copyright 2015 Mirantis Inc.
#
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

import copy
import logging

from oslo_serialization import jsonutils
from oslo_utils import strutils
import re
import requests
import six
from six.moves.urllib import parse

from manilaclient import exceptions

try:
    from eventlet import sleep
except ImportError:
    from time import sleep  # noqa


class HTTPClient(object):
    """HTTP Client class used by multiple clients.

    The imported Requests module caches and reuses objects with the same
    destination. To avoid the problem of sending duplicate requests it is
    necessary that the Requests module is only imported once during client
    execution. This class is shared by multiple client versions so that the
    client can be changed to another version during execution.
    """
    API_VERSION_HEADER = "X-Openstack-Manila-Api-Version"

    def __init__(self, endpoint_url, token, user_agent, api_version,
                 insecure=False, cacert=None, timeout=None, retries=None,
                 http_log_debug=False):
        self.endpoint_url = endpoint_url
        self.base_url = self._get_base_url(self.endpoint_url)
        self.retries = int(retries or 0)
        self.http_log_debug = http_log_debug

        self.request_options = self._set_request_options(
            insecure, cacert, timeout)

        self.default_headers = {
            'X-Auth-Token': token,
            self.API_VERSION_HEADER: api_version.get_string(),
            'User-Agent': user_agent,
            'Accept': 'application/json',
        }

        self._add_log_handlers(http_log_debug)

    def _add_log_handlers(self, http_log_debug):
        self._logger = logging.getLogger(__name__)

        # check that handler hasn't already been added
        if http_log_debug and not self._logger.handlers:
            ch = logging.StreamHandler()
            ch._name = 'http_client_handler'
            self._logger.setLevel(logging.DEBUG)
            self._logger.addHandler(ch)

            if hasattr(requests, 'logging'):
                rql = requests.logging.getLogger(requests.__name__)
                rql.addHandler(ch)

    def _get_base_url(self, url):
        """Truncates url and returns base endpoint"""
        service_endpoint = parse.urlparse(url)
        service_endpoint_base_path = re.search(
            '(.+?)/v([0-9]+|[0-9]+\.[0-9]+)(/.*|$)', service_endpoint.path)
        base_path = (service_endpoint_base_path.group(1)
                     if service_endpoint_base_path else '')
        base_url = service_endpoint._replace(path=base_path)
        return parse.urlunparse(base_url) + '/'

    def _set_request_options(self, insecure, cacert, timeout=None):
        options = {'verify': True}

        if insecure:
            options['verify'] = False
        elif cacert:
            options['verify'] = cacert

        if timeout:
            options['timeout'] = timeout

        return options

    def request(self, url, method, **kwargs):
        headers = copy.deepcopy(self.default_headers)
        headers.update(kwargs.get('headers', {}))

        options = copy.deepcopy(self.request_options)

        if 'body' in kwargs:
            headers['Content-Type'] = 'application/json'
            options['data'] = jsonutils.dumps(kwargs['body'])

        self.log_request(method, url, headers, options.get('data', None))
        resp = requests.request(method, url, headers=headers, **options)
        self.log_response(resp)

        body = None

        if resp.text:
            try:
                body = jsonutils.loads(resp.text)
            except ValueError:
                pass

        if resp.status_code >= 400:
            raise exceptions.from_response(resp, method, url)

        return resp, body

    def _cs_request(self, url, method, **kwargs):
        return self._cs_request_with_retries(
            self.endpoint_url + url,
            method,
            **kwargs)

    def _cs_request_base_url(self, url, method, **kwargs):
        return self._cs_request_with_retries(
            self.base_url + url,
            method,
            **kwargs)

    def _cs_request_with_retries(self, url, method, **kwargs):
        attempts = 0
        timeout = 1
        while True:
            attempts += 1
            try:
                resp, body = self.request(url, method, **kwargs)
                return resp, body
            except (exceptions.BadRequest,
                    requests.exceptions.RequestException,
                    exceptions.ClientException) as e:
                if attempts > self.retries:
                    raise

                self._logger.debug("Request error: %s", six.text_type(e))

            self._logger.debug(
                "Failed attempt(%(current)s of %(total)s), "
                " retrying in %(sec)s seconds", {
                    'current': attempts,
                    'total': self.retries,
                    'sec': timeout
                })
            sleep(timeout)
            timeout *= 2

    def get_with_base_url(self, url, **kwargs):
        return self._cs_request_base_url(url, 'GET', **kwargs)

    def get(self, url, **kwargs):
        return self._cs_request(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        return self._cs_request(url, 'POST', **kwargs)

    def put(self, url, **kwargs):
        return self._cs_request(url, 'PUT', **kwargs)

    def delete(self, url, **kwargs):
        return self._cs_request(url, 'DELETE', **kwargs)

    def log_request(self, method, url, headers, data=None):
        if not self.http_log_debug:
            return

        string_parts = ['curl -i', ' -X %s' % method, ' %s' % url]

        for element in headers:
            header = ' -H "%s: %s"' % (element, headers[element])
            string_parts.append(header)

        if data:
            if "password" in data:
                data = strutils.mask_password(data)
            string_parts.append(" -d '%s'" % data)
        self._logger.debug("\nREQ: %s\n", "".join(string_parts))

    def log_response(self, resp):
        if not self.http_log_debug:
            return
        self._logger.debug(
            "RESP: [%(code)s] %(headers)s\nRESP BODY: %(body)s\n", {
                'code': resp.status_code,
                'headers': resp.headers,
                'body': resp.text
            })
