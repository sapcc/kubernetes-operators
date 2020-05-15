# Copyright 2010 Jacob Kaplan-Moss

# Copyright (c) 2011 OpenStack Foundation
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

"""
Base utilities to build API operation managers and objects on top of.
"""
import abc
import contextlib
import hashlib
import os

import six

from cinderclient.apiclient import base as common_base
from cinderclient import exceptions
from cinderclient import utils


# Valid sort directions and client sort keys
SORT_DIR_VALUES = ('asc', 'desc')
SORT_KEY_VALUES = ('id', 'status', 'size', 'availability_zone', 'name',
                   'bootable', 'created_at', 'reference')
SORT_MANAGEABLE_KEY_VALUES = ('size', 'reference')
# Mapping of client keys to actual sort keys
SORT_KEY_MAPPINGS = {'name': 'display_name'}
# Additional sort keys for resources
SORT_KEY_ADD_VALUES = {
    'backups': ('data_timestamp', ),
    'messages': ('resource_type', 'event_id', 'resource_uuid',
                 'message_level', 'guaranteed_until', 'request_id'),
}

Resource = common_base.Resource


def getid(obj):
    """
    Abstracts the common pattern of allowing both an object or an object's ID
    as a parameter when dealing with relationships.
    """
    return getattr(obj, 'id', obj)


class Manager(common_base.HookableMixin):
    """
    Managers interact with a particular type of API (servers, flavors, images,
    etc.) and provide CRUD operations for them.
    """
    resource_class = None

    def __init__(self, api):
        self.api = api

    @property
    def api_version(self):
        return self.api.api_version

    def _list(self, url, response_key, obj_class=None, body=None,
              limit=None, items=None):
        resp = None
        if items is None:
            items = []
        if body:
            resp, body = self.api.client.post(url, body=body)
        else:
            resp, body = self.api.client.get(url)

        if obj_class is None:
            obj_class = self.resource_class

        data = body[response_key]
        # NOTE(ja): keystone returns values as list as {'values': [ ... ]}
        #           unlike other services which just return the list...
        if isinstance(data, dict):
            try:
                data = data['values']
            except KeyError:
                pass

        items_new = [obj_class(self, res, loaded=True)
                     for res in data if res]
        if limit:
            limit = int(limit)
            margin = limit - len(items)
            if margin <= len(items_new):
                # If the limit is reached, return the items.
                items = items + items_new[:margin]
                if "count" in body:
                    return common_base.ListWithMeta(items, resp), body['count']
                else:
                    return common_base.ListWithMeta(items, resp)
            else:
                items = items + items_new
        else:
            items = items + items_new

        # It is possible that the length of the list we request is longer
        # than osapi_max_limit, so we have to retrieve multiple times to
        # get the complete list.
        next = None
        link_name = response_key + '_links'
        if link_name in body:
            links = body[link_name]
            if links:
                for link in links:
                    if 'rel' in link and 'next' == link['rel']:
                        next = link['href']
                        break
            if next:
                # As long as the 'next' link is not empty, keep requesting it
                # till there is no more items.
                items = self._list(next, response_key, obj_class, None,
                                   limit, items)
        if "count" in body:
            return common_base.ListWithMeta(items, resp), body['count']
        else:
            return common_base.ListWithMeta(items, resp)

    def _build_list_url(self, resource_type, detailed=True, search_opts=None,
                        marker=None, limit=None, sort=None, offset=None):

        if search_opts is None:
            search_opts = {}

        query_params = {}
        for key, val in search_opts.items():
            if val:
                query_params[key] = val

        if marker:
            query_params['marker'] = marker

        if limit:
            query_params['limit'] = limit

        if sort:
            query_params['sort'] = self._format_sort_param(sort,
                                                           resource_type)

        if offset:
            query_params['offset'] = offset
        query_params = utils.unicode_key_value_to_string(query_params)
        # Transform the dict to a sequence of two-element tuples in fixed
        # order, then the encoded string will be consistent in Python 2&3.

        query_string = utils.build_query_param(query_params, sort=True)

        detail = ""
        if detailed:
            detail = "/detail"

        return ("/%(resource_type)s%(detail)s%(query_string)s" %
                {"resource_type": resource_type, "detail": detail,
                 "query_string": query_string})

    def _format_sort_param(self, sort, resource_type=None):
        """Formats the sort information into the sort query string parameter.

        The input sort information can be any of the following:
        - Comma-separated string in the form of <key[:dir]>
        - List of strings in the form of <key[:dir]>
        - List of either string keys, or tuples of (key, dir)

        For example, the following import sort values are valid:
        - 'key1:dir1,key2,key3:dir3'
        - ['key1:dir1', 'key2', 'key3:dir3']
        - [('key1', 'dir1'), 'key2', ('key3', dir3')]

        :param sort: Input sort information
        :returns: Formatted query string parameter or None
        :raise ValueError: If an invalid sort direction or invalid sort key is
                           given
        """
        if not sort:
            return None

        if isinstance(sort, six.string_types):
            # Convert the string into a list for consistent validation
            sort = [s for s in sort.split(',') if s]

        sort_array = []
        for sort_item in sort:
            sort_key, _sep, sort_dir = sort_item.partition(':')
            sort_key = sort_key.strip()
            sort_key = self._format_sort_key_param(sort_key, resource_type)
            if sort_dir:
                sort_dir = sort_dir.strip()
                if sort_dir not in SORT_DIR_VALUES:
                    msg = ('sort_dir must be one of the following: %s.'
                           % ', '.join(SORT_DIR_VALUES))
                    raise ValueError(msg)
                sort_array.append('%s:%s' % (sort_key, sort_dir))
            else:
                sort_array.append(sort_key)
        return ','.join(sort_array)

    def _format_sort_key_param(self, sort_key, resource_type=None):
        valid_sort_keys = SORT_KEY_VALUES
        if resource_type:
            add_sort_keys = SORT_KEY_ADD_VALUES.get(resource_type, None)
            if add_sort_keys:
                valid_sort_keys += add_sort_keys

        if sort_key in valid_sort_keys:
            return SORT_KEY_MAPPINGS.get(sort_key, sort_key)

        msg = ('sort_key must be one of the following: %s.' %
               ', '.join(valid_sort_keys))
        raise ValueError(msg)

    @contextlib.contextmanager
    def completion_cache(self, cache_type, obj_class, mode):
        """
        The completion cache store items that can be used for bash
        autocompletion, like UUIDs or human-friendly IDs.

        A resource listing will clear and repopulate the cache.

        A resource create will append to the cache.

        Delete is not handled because listings are assumed to be performed
        often enough to keep the cache reasonably up-to-date.
        """
        base_dir = utils.env('CINDERCLIENT_UUID_CACHE_DIR',
                             default="~/.cache/cinderclient")

        # NOTE(sirp): Keep separate UUID caches for each username + endpoint
        # pair
        username = utils.env('OS_USERNAME', 'CINDER_USERNAME')
        url = utils.env('OS_URL', 'CINDER_URL')
        uniqifier = hashlib.sha1(username.encode('utf-8') +        # nosec
                                 url.encode('utf-8')).hexdigest()

        cache_dir = os.path.expanduser(os.path.join(base_dir, uniqifier))

        try:
            os.makedirs(cache_dir, 0o750)
        except OSError:
            # NOTE(kiall): This is typically either permission denied while
            #              attempting to create the directory, or the directory
            #              already exists. Either way, don't fail.
            pass

        resource = obj_class.__name__.lower()
        filename = "%s-%s-cache" % (resource, cache_type.replace('_', '-'))
        path = os.path.join(cache_dir, filename)

        cache_attr = "_%s_cache" % cache_type

        try:
            setattr(self, cache_attr, open(path, mode))
        except IOError:
            # NOTE(kiall): This is typically a permission denied while
            #              attempting to write the cache file.
            pass

        try:
            yield
        finally:
            cache = getattr(self, cache_attr, None)
            if cache:
                cache.close()
                try:
                    delattr(self, cache_attr)
                except AttributeError:
                    # NOTE(kiall): If this attr is deleted by another
                    #              operation, don't fail any way.
                    pass

    def write_to_completion_cache(self, cache_type, val):
        cache = getattr(self, "_%s_cache" % cache_type, None)
        if cache:
            try:
                cache.write("%s\n" % val)
            except UnicodeEncodeError:
                pass

    def _get(self, url, response_key=None):
        resp, body = self.api.client.get(url)
        if response_key:
            return self.resource_class(self, body[response_key], loaded=True,
                                       resp=resp)
        else:
            return self.resource_class(self, body, loaded=True, resp=resp)

    def _create(self, url, body, response_key, return_raw=False, **kwargs):
        self.run_hooks('modify_body_for_create', body, **kwargs)
        resp, body = self.api.client.post(url, body=body)
        if return_raw:
            return common_base.DictWithMeta(body[response_key], resp)

        return self.resource_class(self, body[response_key], resp=resp)

    def _delete(self, url):
        resp, body = self.api.client.delete(url)
        return common_base.TupleWithMeta((resp, body), resp)

    def _update(self, url, body, response_key=None, **kwargs):
        self.run_hooks('modify_body_for_update', body, **kwargs)
        resp, body = self.api.client.put(url, body=body, **kwargs)
        if response_key:
            return self.resource_class(self, body[response_key], loaded=True,
                                       resp=resp)

        # (NOTE)ankit: In case of qos_specs.unset_keys method, None is
        # returned back to the caller and in all other cases dict is
        # returned but in order to return request_ids to the caller, it's
        # not possible to return None so returning DictWithMeta for all cases.
        body = body or {}
        return common_base.DictWithMeta(body, resp)

    def _get_with_base_url(self, url, response_key=None):
        resp, body = self.api.client.get_with_base_url(url)
        if response_key:
            return [self.resource_class(self, res, loaded=True)
                    for res in body[response_key] if res]
        else:
            return self.resource_class(self, body, loaded=True)


class ManagerWithFind(six.with_metaclass(abc.ABCMeta, Manager)):
    """
    Like a `Manager`, but with additional `find()`/`findall()` methods.
    """

    @abc.abstractmethod
    def list(self):
        pass

    def find(self, **kwargs):
        """
        Find a single item with attributes matching ``**kwargs``.

        This isn't very efficient for search options which require the
        Python side filtering(e.g. 'human_id')
        """
        matches = self.findall(**kwargs)
        num_matches = len(matches)
        if num_matches == 0:
            msg = "No %s matching %s." % (self.resource_class.__name__, kwargs)
            raise exceptions.NotFound(404, msg)
        elif num_matches > 1:
            raise exceptions.NoUniqueMatch
        else:
            matches[0].append_request_ids(matches.request_ids)
            return matches[0]

    def findall(self, **kwargs):
        """
        Find all items with attributes matching ``**kwargs``.

        This isn't very efficient for search options which require the
        Python side filtering(e.g. 'human_id')
        """

        # Want to search for all tenants here so that when attempting to delete
        # that a user like admin doesn't get a failure when trying to delete
        # another tenant's volume by name.
        search_opts = {'all_tenants': 1}

        # Pass 'name' or 'display_name' search_opts to server filtering to
        # increase search performance.
        if 'name' in kwargs:
            search_opts['name'] = kwargs['name']
        elif 'display_name' in kwargs:
            search_opts['display_name'] = kwargs['display_name']

        found = common_base.ListWithMeta([], None)
        # list_volume is used for group query, it's not resource's property.
        list_volume = kwargs.pop('list_volume', False)
        searches = kwargs.items()
        if list_volume:
            listing = self.list(search_opts=search_opts,
                                list_volume=list_volume)
        else:
            listing = self.list(search_opts=search_opts)
        found.append_request_ids(listing.request_ids)
        # Not all resources attributes support filters on server side
        # (e.g. 'human_id' doesn't), so when doing findall some client
        # side filtering is still needed.
        for obj in listing:
            try:
                if all(getattr(obj, attr) == value
                       for (attr, value) in searches):
                    found.append(obj)
            except AttributeError:
                continue

        return found
