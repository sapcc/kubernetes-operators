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

import contextlib
import json

import keystoneauth1.exceptions.http as ks_exceptions
import osc_lib.exceptions as exceptions
import six


_http_error_to_exc = {
    cls.http_status: cls
    for cls in exceptions.ClientException.__subclasses__()
}


@contextlib.contextmanager
def _wrap_http_exceptions():
    """Reraise osc-lib exceptions with detailed messages."""

    try:
        yield
    except ks_exceptions.HttpError as exc:
        detail = json.loads(exc.response.content)['errors'][0]['detail']
        msg = detail.split('\n')[-1].strip()
        exc_class = _http_error_to_exc.get(exc.http_status,
                                           exceptions.CommandError)

        six.raise_from(exc_class(exc.http_status, msg), exc)


class SessionClient(object):
    def __init__(self, session, ks_filter, api_version='1.0'):
        self.session = session
        self.ks_filter = ks_filter
        self.api_version = api_version

    def request(self, method, url, **kwargs):
        version = kwargs.pop('version', None)
        api_version = (self.ks_filter['service_type'] + ' ' +
                       (version or self.api_version))
        headers = kwargs.pop('headers', {})
        headers.setdefault('OpenStack-API-Version', api_version)
        headers.setdefault('Accept', 'application/json')

        with _wrap_http_exceptions():
            return self.session.request(url, method,
                                        headers=headers,
                                        endpoint_filter=self.ks_filter,
                                        **kwargs)
