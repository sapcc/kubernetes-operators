# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
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
import abc
import json

import six
from six.moves.urllib import parse
from stevedore import extension

from designateclient import exceptions


@six.add_metaclass(abc.ABCMeta)
class Controller(object):

    def __init__(self, client):
        self.client = client

    def build_url(self, url, criterion=None, marker=None, limit=None):
        params = criterion or {}

        if marker is not None:
            params['marker'] = marker
        if limit is not None:
            params['limit'] = limit

        q = parse.urlencode(params) if params else ''
        return '%(url)s%(params)s' % {
            'url': url,
            'params': '?%s' % q
        }

    def _serialize(self, kwargs):
        headers = kwargs.get('headers')
        content_type = headers.get('Content-Type') if headers else None

        if 'data' in kwargs and content_type in {None, 'application/json'}:
            kwargs['data'] = json.dumps(kwargs['data'])

    def _post(self, url, response_key=None, **kwargs):
        self._serialize(kwargs)

        resp, body = self.client.session.post(url, **kwargs)
        if response_key is not None:
            return body[response_key]
        return body

    def _get(self, url, response_key=None):
        resp, body = self.client.session.get(url)
        if response_key is not None:
            return body[response_key]
        return body

    def _patch(self, url, response_key=None, **kwargs):
        self._serialize(kwargs)

        resp, body = self.client.session.patch(url, **kwargs)
        if response_key is not None:
            return body[response_key]
        return body

    def _put(self, url, response_key=None, **kwargs):
        self._serialize(kwargs)

        resp, body = self.client.session.put(url, **kwargs)
        if response_key is not None:
            return body[response_key]
        return body

    def _delete(self, url, response_key=None, **kwargs):
        resp, body = self.client.session.delete(url, **kwargs)
        if response_key is not None:
            return body[response_key]
        return body


@six.add_metaclass(abc.ABCMeta)
class CrudController(Controller):

    @abc.abstractmethod
    def list(self, *args, **kw):
        """
        List a resource
        """

    @abc.abstractmethod
    def get(self, *args, **kw):
        """
        Get a resource
        """

    @abc.abstractmethod
    def create(self, *args, **kw):
        """
        Create a resource
        """

    @abc.abstractmethod
    def update(self, *args, **kw):
        """
        Update a resource
        """

    @abc.abstractmethod
    def delete(self, *args, **kw):
        """
        Delete a resource
            """


def get_versions():
    mgr = extension.ExtensionManager('designateclient.versions')
    return dict([(ep.name, ep.plugin) for ep in mgr.extensions])


def Client(version, *args, **kwargs):  # noqa
    versions = get_versions()
    if version not in versions:
        msg = 'Version %s is not supported, use one of (%s)' % (
            version, list(six.iterkeys(versions)))
        raise exceptions.UnsupportedVersion(msg)
    return versions[version](*args, **kwargs)
