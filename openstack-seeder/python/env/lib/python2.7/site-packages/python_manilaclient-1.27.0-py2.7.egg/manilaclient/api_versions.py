# Copyright 2015 Chuck Fouts
# All Rights Reserved.
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

import functools
import logging
import re
import warnings

import manilaclient
from manilaclient.common._i18n import _
from manilaclient.common import cliutils
from manilaclient.common import constants
from manilaclient import exceptions
from manilaclient import utils

LOG = logging.getLogger(__name__)

MAX_VERSION = '2.49'
MIN_VERSION = '2.0'
DEPRECATED_VERSION = '1.0'
_VERSIONED_METHOD_MAP = {}


class APIVersion(object):
    """Top level object to support Manila API Versioning.

    This class represents an API Version with convenience
    methods for manipulation and comparison of version
    numbers that we need to do to implement microversions.
    """

    TYPE_ERROR_MSG = _("'%(other)s' should be an instance of '%(cls)s'")

    def __init__(self, version_str=None):
        """Create an API version object."""
        self.ver_major = 0
        self.ver_minor = 0

        if version_str is not None:
            match = re.match(r"^([1-9]\d*)\.([1-9]\d*|0)$", version_str)
            if match:
                self.ver_major = int(match.group(1))
                self.ver_minor = int(match.group(2))
            else:
                msg = _("Invalid format of client version '%s'. "
                        "Expected format 'X.Y', where X is a major part and Y "
                        "is a minor part of version.") % version_str
                raise exceptions.UnsupportedVersion(msg)

    def __str__(self):
        """Debug/Logging representation of object."""
        return ("API Version Major: %s, Minor: %s"
                % (self.ver_major, self.ver_minor))

    def __repr__(self):
        if self.is_null():
            return "<APIVersion: null>"
        else:
            return "<APIVersion: %s>" % self.get_string()

    def __lt__(self, other):
        if not isinstance(other, APIVersion):
            raise TypeError(self.TYPE_ERROR_MSG % {"other": other,
                                                   "cls": self.__class__})

        return ((self.ver_major, self.ver_minor) <
                (other.ver_major, other.ver_minor))

    def __eq__(self, other):
        if not isinstance(other, APIVersion):
            raise TypeError(self.TYPE_ERROR_MSG % {"other": other,
                                                   "cls": self.__class__})

        return ((self.ver_major, self.ver_minor) ==
                (other.ver_major, other.ver_minor))

    def __gt__(self, other):
        if not isinstance(other, APIVersion):
            raise TypeError(self.TYPE_ERROR_MSG % {"other": other,
                                                   "cls": self.__class__})
        return ((self.ver_major, self.ver_minor) >
                (other.ver_major, other.ver_minor))

    def __le__(self, other):
        return self < other or self == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __ge__(self, other):
        return self > other or self == other

    def is_null(self):
        return self.ver_major == 0 and self.ver_minor == 0

    def is_latest(self):
        return self == manilaclient.API_MAX_VERSION

    def matches(self, min_version, max_version):
        """Determines if version is within a range.

        Returns whether the version object represents a version
        greater than or equal to the minimum version and less than
        or equal to the maximum version.

        :param min_version: Minimum acceptable version.
        :param max_version: Maximum acceptable version.
        :returns: boolean

        If min_version is null then there is no minimum limit.
        If max_version is null then there is no maximum limit.
        If self is null then raise ValueError
        """

        if self.is_null():
            raise ValueError(_("Null APIVersion doesn't support 'matches'."))
        if max_version.is_null() and min_version.is_null():
            return True
        elif max_version.is_null():
            return min_version <= self
        elif min_version.is_null():
            return self <= max_version
        else:
            return min_version <= self <= max_version

    def get_string(self):
        """String representation of an APIVersion object."""
        if self.is_null():
            raise ValueError(
                _("Null APIVersion cannot be converted to string."))
        return "%s.%s" % (self.ver_major, self.ver_minor)

    def get_major_version(self):
        return "%s" % self.ver_major


class VersionedMethod(object):

    def __init__(self, name, start_version, end_version, func):
        """Versioning information for a single method

        :param name: Name of the method
        :param start_version: Minimum acceptable version
        :param end_version: Maximum acceptable_version
        :param func: Method to call

        Minimum and maximums are inclusive
        """
        self.name = name
        self.start_version = start_version
        self.end_version = end_version
        self.func = func

    def __str__(self):
        return ("Version Method %s: min: %s, max: %s"
                % (self.name, self.start_version, self.end_version))

    def __repr__(self):
        return "<VersionedMethod %s>" % self.name


def check_version_supported(api_version):
    """Returns True if the API version is supported.

    :warn Sends warning if version is not supported.
    """
    if (check_version_matches_min_max(api_version) or
            check_version_deprecated(api_version)):
        return True
    return False


def check_version_matches_min_max(api_version):
    """Returns True if the API version is within the supported range."""
    if (not api_version.matches(
            manilaclient.API_MIN_VERSION,
            manilaclient.API_MAX_VERSION)):
        msg = _("Invalid client version '%(version)s'. "
                "Current version range is '%(min)s' through "
                " '%(max)s'") % {
            "version": api_version.get_string(),
            "min": manilaclient.API_MIN_VERSION.get_string(),
            "max": manilaclient.API_MAX_VERSION.get_string()}
        warnings.warn(msg)
        return False
    return True


def check_version_deprecated(api_version):
    """Returns True if API version is deprecated."""
    if api_version == manilaclient.API_DEPRECATED_VERSION:
        msg = _("Client version '%(version)s' is deprecated.") % {
            "version": api_version.get_string()}
        warnings.warn(msg)
        return True
    return False


def get_api_version(version_string):
    """Returns checked APIVersion object."""
    version_string = str(version_string)

    api_version = APIVersion(version_string)
    check_version_supported(api_version)
    return api_version


def _get_server_version_range(client):
    """Obtain version range from server."""
    response = client.services.server_api_version('')

    server_version = None
    for resource in response:
        if hasattr(resource, 'version'):
            if resource.status == "CURRENT":
                server_version = resource
                break

    if not hasattr(server_version, 'version') or not server_version.version:
        return APIVersion(), APIVersion()

    min_version = APIVersion(server_version.min_version)
    max_version = APIVersion(server_version.version)

    return min_version, max_version


def discover_version(client, requested_version):
    """Discovers the most recent version for client and API.

    Checks 'requested_version' and returns the most recent version
    supported by both the API and the client. If there is not a supported
    version then an UnsupportedVersion exception is thrown.

    :param client: client object
    :param requested_version: requested version represented by APIVersion obj
    :returns: APIVersion
    """
    server_start_version, server_end_version = _get_server_version_range(
        client)

    valid_version = requested_version
    if server_start_version.is_null() and server_end_version.is_null():
        msg = ("Server does not support microversions. Changing server "
               "version to %(min_version)s.")
        LOG.debug(msg, {"min_version": DEPRECATED_VERSION})
        valid_version = APIVersion(DEPRECATED_VERSION)
    else:
        valid_version = _validate_requested_version(
            requested_version,
            server_start_version,
            server_end_version)

        _validate_server_version(server_start_version, server_end_version)
    return valid_version


def _validate_requested_version(requested_version,
                                server_start_version,
                                server_end_version):
    """Validates the requested version.

    Checks 'requested_version' is within the min/max range supported by the
    server. If 'requested_version' is not within range then attempts to
    downgrade to 'server_end_version'. Otherwise an UnsupportedVersion
    exception is thrown.

    :param requested_version: requestedversion represented by APIVersion obj
    :param server_start_version: APIVersion object representing server min
    :param server_end_version: APIVersion object representing server max
    """
    valid_version = requested_version
    if not requested_version.matches(server_start_version, server_end_version):
        if server_end_version <= requested_version:
            if (manilaclient.API_MIN_VERSION <= server_end_version and
                    server_end_version <= manilaclient.API_MAX_VERSION):
                msg = _("Requested version %(requested_version)s is "
                        "not supported. Downgrading requested version "
                        "to %(server_end_version)s.")
                LOG.debug(msg, {
                    "requested_version": requested_version,
                    "server_end_version": server_end_version})
            valid_version = server_end_version
        else:
            raise exceptions.UnsupportedVersion(
                _("The specified version isn't supported by server. The valid "
                  "version range is '%(min)s' to '%(max)s'") % {
                    "min": server_start_version.get_string(),
                    "max": server_end_version.get_string()})

    return valid_version


def _validate_server_version(server_start_version, server_end_version):
    """Validates the server version.

    Checks that the 'server_end_version' is greater than the minimum version
    supported by the client. Then checks that the 'server_start_version' is
    less than the maximum version supported by the client.

    :param server_start_version:
    :param server_end_version:
    :return:
    """
    if manilaclient.API_MIN_VERSION > server_end_version:
        raise exceptions.UnsupportedVersion(
            _("Server's version is too old. The client's valid version range "
              "is '%(client_min)s' to '%(client_max)s'. The server valid "
              "version range is '%(server_min)s' to '%(server_max)s'.") % {
                  'client_min': manilaclient.API_MIN_VERSION.get_string(),
                  'client_max': manilaclient.API_MAX_VERSION.get_string(),
                  'server_min': server_start_version.get_string(),
                  'server_max': server_end_version.get_string()})
    elif manilaclient.API_MAX_VERSION < server_start_version:
        raise exceptions.UnsupportedVersion(
            _("Server's version is too new. The client's valid version range "
              "is '%(client_min)s' to '%(client_max)s'. The server valid "
              "version range is '%(server_min)s' to '%(server_max)s'.") % {
                  'client_min': manilaclient.API_MIN_VERSION.get_string(),
                  'client_max': manilaclient.API_MAX_VERSION.get_string(),
                  'server_min': server_start_version.get_string(),
                  'server_max': server_end_version.get_string()})


def add_versioned_method(versioned_method):
    _VERSIONED_METHOD_MAP.setdefault(versioned_method.name, [])
    _VERSIONED_METHOD_MAP[versioned_method.name].append(versioned_method)


def get_versioned_methods(func_name, api_version=None):
    versioned_methods = _VERSIONED_METHOD_MAP.get(func_name, [])
    if api_version and not api_version.is_null():
        return [m for m in versioned_methods
                if api_version.matches(m.start_version, m.end_version)]
    return versioned_methods


def experimental_api(f):
    """Adds to HTTP Header to indicate this is an experimental API call."""

    @functools.wraps(f)
    def _wrapper(*args, **kwargs):
        client = args[0]
        if (isinstance(client, manilaclient.v2.client.Client) or
                hasattr(client, 'client')):
            dh = client.client.default_headers
            dh[constants.EXPERIMENTAL_HTTP_HEADER] = 'true'
        return f(*args, **kwargs)
    return _wrapper


def wraps(start_version, end_version=MAX_VERSION):
    """Annotation used to return the correct method based on requested version.

    Creates a VersionedMethod based on data from the method using the 'wraps'
    annotation. The VersionedMethod is stored in the _VERSIONED_METHOD_MAP.
    Also, adds a 'substitution' method that is used to look up the latest
    method matching the start_version.

    :param start_version: String obj representing first supported version.
    :param end_version: String obj representing last supported version.
    """
    start_version = APIVersion(start_version)
    end_version = APIVersion(end_version)

    def decor(func):
        func.versioned = True
        name = utils.get_function_name(func)
        versioned_method = VersionedMethod(name, start_version,
                                           end_version, func)
        add_versioned_method(versioned_method)

        @functools.wraps(func)
        def substitution(obj, *args, **kwargs):
            methods = get_versioned_methods(name, obj.api_version)

            if not methods:
                raise exceptions.UnsupportedVersion(
                    _("API version '%(version)s' is not supported on "
                      "'%(method)s' method.") % {
                        "version": obj.api_version.get_string(),
                        "method": name,
                    })

            method = max(methods, key=lambda f: f.start_version)

            return method.func(obj, *args, **kwargs)

        if hasattr(func, 'arguments'):
            for cli_args, cli_kwargs in func.arguments:
                cliutils.add_arg(substitution, *cli_args, **cli_kwargs)
        return substitution

    return decor
