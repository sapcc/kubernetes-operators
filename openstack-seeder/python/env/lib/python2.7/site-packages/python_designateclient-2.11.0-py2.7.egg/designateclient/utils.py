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

import json
import os
import uuid

from debtcollector import removals
from keystoneauth1 import adapter
from keystoneauth1.identity import generic
from keystoneauth1 import session as ks_session
from keystoneauth1 import token_endpoint
import pkg_resources
import six

from designateclient import exceptions


def resource_string(*args, **kwargs):
    if len(args) == 0:
        raise ValueError()

    package = kwargs.pop('package', None)

    if not package:
        package = 'designateclient'

    resource_path = os.path.join('resources', *args)

    if not pkg_resources.resource_exists(package, resource_path):
        raise exceptions.ResourceNotFound('Could not find the requested '
                                          'resource: %s' % resource_path)

    return pkg_resources.resource_string(package, resource_path)


def load_schema(version, name, package=None):
    schema_string = resource_string('schemas', version, '%s.json' % name,
                                    package=package)

    return json.loads(schema_string.decode('utf-8'))


def get_item_properties(item, fields, mixed_case_fields=[], formatters={}):
    """Return a tuple containing the item properties.

    :param item: a single item resource (e.g. Server, Tenant, etc)
    :param fields: tuple of strings with the desired field names
    :param mixed_case_fields: tuple of field names to preserve case
    :param formatters: dictionary mapping field names to callables
        to format the values
    """
    row = []

    for field in fields:
        if field in formatters:
            row.append(formatters[field](item))
        else:
            if field in mixed_case_fields:
                field_name = field.replace(' ', '_')
            else:
                field_name = field.lower().replace(' ', '_')
            if not hasattr(item, field_name) and \
                    (isinstance(item, dict) and field_name in item):
                data = item[field_name]
            else:
                data = getattr(item, field_name, '')
            if data is None:
                data = ''
            row.append(data)
    return tuple(row)


def get_columns(data):
    """
    Some row's might have variable count of columns, ensure that we have the
    same.

    :param data: Results in [{}, {]}]
    """
    columns = set()

    def _seen(col):
        columns.add(str(col))

    six.moves.map(lambda item: six.moves.map(_seen,
                  list(six.iterkeys(item))), data)
    return list(columns)


@removals.removed_kwarg('all_tenants', removal_version='1.3.0')
@removals.removed_kwarg('edit_managed', removal_version='1.3.0')
def get_session(auth_url, endpoint, domain_id, domain_name, project_id,
                project_name, project_domain_name, project_domain_id, username,
                user_id, password, user_domain_id, user_domain_name, token,
                insecure, cacert, all_tenants=False, edit_managed=False):
    # NOTE: all_tenants and edit_managed are here for backwards compat
    #       reasons, do not add additional modifiers here.

    session = ks_session.Session()

    # Build + Attach Authentication Plugin
    auth_args = {
        'auth_url': auth_url,
        'domain_id': domain_id,
        'domain_name': domain_name,
        'project_id': project_id,
        'project_name': project_name,
        'project_domain_name': project_domain_name,
        'project_domain_id': project_domain_id,
    }

    if token and endpoint:
        session.auth = token_endpoint.Token(endpoint, token)

    elif token:
        auth_args.update({
            'token': token
        })
        session.auth = generic.Token(**auth_args)

    else:
        auth_args.update({
            'username': username,
            'user_id': user_id,
            'password': password,
            'user_domain_id': user_domain_id,
            'user_domain_name': user_domain_name,
        })
        session.auth = generic.Password(**auth_args)

    # SSL/TLS Server Cert Verification
    if insecure is True:
        session.verify = False
    else:
        session.verify = cacert

    # NOTE: all_tenants and edit_managed are here for backwards compat
    #       reasons, do not add additional modifiers here.
    session.all_tenants = all_tenants
    session.edit_managed = edit_managed

    return session


def find_resourceid_by_name_or_id(resource_client, name_or_id):
    """Find resource id from its id or name."""
    try:
        # Try to return an uuid
        return str(uuid.UUID(name_or_id))
    except ValueError:
        # Not an uuid => assume it is resource name
        pass

    resources = resource_client.list()
    candidate_ids = [r['id'] for r in resources if r.get('name') == name_or_id]
    if not candidate_ids:
        raise exceptions.ResourceNotFound(
            'Could not find resource with name "%s"' % name_or_id)
    elif len(candidate_ids) > 1:
        str_ids = ','.join(candidate_ids)
        raise exceptions.NoUniqueMatch(
            'Multiple resources with name "%s": %s' % (name_or_id, str_ids))
    return candidate_ids[0]


class AdapterWithTimeout(adapter.Adapter):
    """adapter.Adapter wraps around a Session.

    The user can pass a timeout keyword that will apply only to
    the Designate Client, in order:

    - timeout keyword passed to ``request()``
    - timeout keyword passed to ``AdapterWithTimeout()``
    - timeout attribute on keystone session
    """
    def __init__(self, *args, **kw):
        self.timeout = kw.pop('timeout', None)
        super(self.__class__, self).__init__(*args, **kw)

    def request(self, *args, **kwargs):
        if self.timeout is not None:
            kwargs.setdefault('timeout', self.timeout)

        return super(AdapterWithTimeout, self).request(*args, **kwargs)
