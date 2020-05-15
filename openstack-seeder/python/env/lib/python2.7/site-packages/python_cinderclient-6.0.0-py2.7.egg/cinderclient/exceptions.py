# Copyright 2010 Jacob Kaplan-Moss
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

"""
Exception definitions.
"""
from datetime import datetime

from oslo_utils import timeutils


class ResourceInErrorState(Exception):
    """When resource is in Error state"""
    def __init__(self, obj, fault_msg):
        msg = "'%s' resource is in the error state" % obj.__class__.__name__
        if fault_msg:
            msg += " due to '%s'" % fault_msg
        self.message = "%s." % msg

    def __str__(self):
        return self.message


class TimeoutException(Exception):
    """When an action exceeds the timeout period to complete the action"""
    def __init__(self, obj, action):
        self.message = ("The '%(action)s' of the '%(object_name)s' exceeded "
                    "the timeout period." % {"action": action,
                    "object_name": obj.__class__.__name__})

    def __str__(self):
        return self.message


class UnsupportedVersion(Exception):
    """Indicates that the user is trying to use an unsupported
    version of the API.
    """
    pass


class UnsupportedAttribute(AttributeError):
    """Indicates that the user is trying to transmit the argument to a method,
    which is not supported by selected version.
    """

    def __init__(self, argument_name, start_version, end_version):
        if start_version and end_version:
            self.message = (
                "'%(name)s' argument is only allowed for microversions "
                "%(start)s - %(end)s." % {"name": argument_name,
                                          "start": start_version.get_string(),
                                          "end": end_version.get_string()})
        elif start_version:
            self.message = (
                "'%(name)s' argument is only allowed since microversion "
                "%(start)s." % {"name": argument_name,
                                "start": start_version.get_string()})

        elif end_version:
            self.message = (
                "'%(name)s' argument is not allowed after microversion "
                "%(end)s." % {"name": argument_name,
                              "end": end_version.get_string()})

    def __str__(self):
        return self.message


class InvalidAPIVersion(Exception):
    pass


class CommandError(Exception):
    pass


class AuthorizationFailure(Exception):
    pass


class NoUniqueMatch(Exception):
    pass


class AuthSystemNotFound(Exception):
    """When the user specifies an AuthSystem but not installed."""
    def __init__(self, auth_system):
        self.auth_system = auth_system

    def __str__(self):
        return "AuthSystemNotFound: %s" % repr(self.auth_system)


class NoTokenLookupException(Exception):
    """This form of authentication does not support looking up
       endpoints from an existing token.
    """
    pass


class EndpointNotFound(Exception):
    """Could not find Service or Region in Service Catalog."""
    pass


class ConnectionError(Exception):
    """Could not open a connection to the API service."""
    pass


class AmbiguousEndpoints(Exception):
    """Found more than one matching endpoint in Service Catalog."""
    def __init__(self, endpoints=None):
        self.endpoints = endpoints

    def __str__(self):
        return "AmbiguousEndpoints: %s" % repr(self.endpoints)


class ClientException(Exception):
    """
    The base exception class for all exceptions this library raises.
    """
    def __init__(self, code, message=None, details=None,
                 request_id=None, response=None):
        self.code = code
        # NOTE(mriedem): Use getattr on self.__class__.message since
        # BaseException.message was dropped in python 3, see PEP 0352.
        self.message = message or getattr(self.__class__, 'message', None)
        self.details = details
        self.request_id = request_id

    def __str__(self):
        formatted_string = "%s" % self.message
        if self.code >= 100:
            # HTTP codes start at 100.
            formatted_string += " (HTTP %s)" % self.code
        if self.request_id:
            formatted_string += " (Request-ID: %s)" % self.request_id

        return formatted_string


class BadRequest(ClientException):
    """
    HTTP 400 - Bad request: you sent some malformed data.
    """
    http_status = 400
    message = "Bad request"


class Unauthorized(ClientException):
    """
    HTTP 401 - Unauthorized: bad credentials.
    """
    http_status = 401
    message = "Unauthorized"


class Forbidden(ClientException):
    """
    HTTP 403 - Forbidden: your credentials don't give you access to this
    resource.
    """
    http_status = 403
    message = "Forbidden"


class NotFound(ClientException):
    """
    HTTP 404 - Not found
    """
    http_status = 404
    message = "Not found"


class NotAcceptable(ClientException):
    """
    HTTP 406 - Not Acceptable
    """
    http_status = 406
    message = "Not Acceptable"


class OverLimit(ClientException):
    """
    HTTP 413 - Over limit: you're over the API limits for this time period.
    """
    http_status = 413
    message = "Over limit"

    def __init__(self, code, message=None, details=None,
                 request_id=None, response=None):
        super(OverLimit, self).__init__(code, message=message,
                                        details=details, request_id=request_id,
                                        response=response)
        self.retry_after = 0
        self._get_rate_limit(response)

    def _get_rate_limit(self, resp):
        if (resp is not None) and resp.headers:
            utc_now = timeutils.utcnow()
            value = resp.headers.get('Retry-After', '0')
            try:
                value = datetime.strptime(value, '%a, %d %b %Y %H:%M:%S %Z')
                if value > utc_now:
                    self.retry_after = ((value - utc_now).seconds)
                else:
                    self.retry_after = 0
            except ValueError:
                self.retry_after = int(value)


# NotImplemented is a python keyword.
class HTTPNotImplemented(ClientException):
    """
    HTTP 501 - Not Implemented: the server does not support this operation.
    """
    http_status = 501
    message = "Not Implemented"


# In Python 2.4 Exception is old-style and thus doesn't have a __subclasses__()
# so we can do this:
#     _code_map = dict((c.http_status, c)
#                      for c in ClientException.__subclasses__())
#
# Instead, we have to hardcode it:
_code_map = dict((c.http_status, c) for c in [BadRequest, Unauthorized,
                                              Forbidden, NotFound,
                                              NotAcceptable,
                                              OverLimit, HTTPNotImplemented])


def from_response(response, body):
    """
    Return an instance of a ClientException or subclass
    based on a requests response.

    Usage::

        resp, body = requests.request(...)
        if resp.status_code != 200:
            raise exceptions.from_response(resp, resp.text)
    """
    cls = _code_map.get(response.status_code, ClientException)
    if response.headers:
        request_id = response.headers.get('x-compute-request-id')
    else:
        request_id = None
    if body:
        message = "n/a"
        details = "n/a"
        if hasattr(body, 'keys'):
            # Only in webob>=1.6.0
            if 'message' in body:
                message = body.get('message')
                details = body.get('details')
            else:
                error = body[list(body)[0]]
                message = error.get('message', message)
                details = error.get('details', details)
        return cls(code=response.status_code, message=message, details=details,
                   request_id=request_id, response=response)
    else:
        return cls(code=response.status_code, request_id=request_id,
                   message=response.reason, response=response)


class VersionNotFoundForAPIMethod(Exception):
    msg_fmt = "API version '%(vers)s' is not supported on '%(method)s' method."

    def __init__(self, version, method):
        self.version = version
        self.method = method

    def __str__(self):
        return self.msg_fmt % {"vers": self.version, "method": self.method}
