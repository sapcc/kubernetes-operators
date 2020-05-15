# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Author: Endre Karlson <endre.karlson@hp.com>
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

from oslo_utils import uuidutils
from six import iteritems
from six import iterkeys
from six.moves.urllib.parse import parse_qs
from six.moves.urllib.parse import urlparse

from designateclient import exceptions


def resolve_by_name(func, name, *args):
    """
    Helper to resolve a "name" a'la foo.com to it's ID by using REST api's
    query support and filtering on name.
    """
    if uuidutils.is_uuid_like(name):
        return name

    results = func(criterion={"name": "%s" % name}, *args)
    length = len(results)

    if length == 1:
        return results[0]["id"]
    elif length == 0:
        raise exceptions.NotFound("Name %s didn't resolve" % name)
    else:
        msg = "Multiple matches found for %s, please use ID instead." % name
        raise exceptions.NoUniqueMatch(msg)


def parse_query_from_url(url):
    """
    Helper to get key bits of data from the "next" url returned
    from the API on collections
    :param url:
    :return: dict
    """
    values = parse_qs(urlparse(url)[4])
    return {k: values[k][0] for k in iterkeys(values)}


def get_all(function, criterion=None, args=None):
    """

    :param function: Function to be called to get data
    :param criterion: dict of filters to be applied
    :param args: arguments to be given to the function
    :return: DesignateList()
    """

    criterion = criterion or {}
    args = args or []

    data = function(*args, criterion=criterion)
    returned_data = data
    while True:
        if data.next_page:
            for k, v in iteritems(data.next_link_criterion):
                criterion[k] = v
            data = function(*args, criterion=criterion)
            returned_data.extend(data)
        else:
            break

    return returned_data
