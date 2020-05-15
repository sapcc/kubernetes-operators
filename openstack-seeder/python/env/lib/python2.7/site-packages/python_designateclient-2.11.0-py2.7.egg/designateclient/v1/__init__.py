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
from debtcollector import removals
from stevedore import extension

from designateclient import exceptions
from designateclient import utils
from designateclient import version


@removals.removed_class(
    'designateclient.v1.Client',
    replacement='designateclient.v2.client.Client',
    message='Designate v1 API is being retired, and the v1 Client class will '
    'stop functioning. Please update code to the '
    'designateclient.v2.client.Client class. The API is deprecated',
    version='2.2.0',
    removal_version='?',
    stacklevel=3)
class Client(object):
    """Client for the Designate v1 API"""

    def __init__(self, endpoint=None, username=None, user_id=None,
                 user_domain_id=None, user_domain_name=None, password=None,
                 tenant_name=None, tenant_id=None, domain_name=None,
                 domain_id=None, project_name=None,
                 project_id=None, project_domain_name=None,
                 project_domain_id=None, auth_url=None, token=None,
                 endpoint_type='publicURL', region_name=None,
                 service_type='dns', insecure=False, session=None,
                 cacert=None, all_tenants=None, edit_managed=None,
                 timeout=None):
        """
        :param endpoint: Endpoint URL
        :param token: A token instead of username / password
        :param insecure: Allow "insecure" HTTPS requests
        """

        if endpoint:
            endpoint = endpoint.rstrip('/')
            if not endpoint.endswith('v1'):
                endpoint = "%s/v1" % endpoint

        # Compatibility code to mimic the old behaviour of the client
        if session is None:
            session = utils.get_session(
                auth_url=auth_url,
                endpoint=endpoint,
                domain_id=domain_id,
                domain_name=domain_name,
                project_id=project_id or tenant_id,
                project_name=project_name or tenant_name,
                project_domain_name=project_domain_name,
                project_domain_id=project_domain_id,
                username=username,
                user_id=user_id,
                password=password,
                user_domain_id=user_domain_id,
                user_domain_name=user_domain_name,
                token=token,
                insecure=insecure,
                cacert=cacert,
            )

        # NOTE: all_tenants and edit_managed are pulled from the session for
        #       backwards compat reasons, do not pull additional modifiers from
        #       here. Once removed, the kwargs above should default to False.
        if all_tenants is None:
            self.all_tenants = getattr(session, 'all_tenants', False)
        else:
            self.all_tenants = all_tenants

        if edit_managed is None:
            self.edit_managed = getattr(session, 'edit_managed', False)
        else:
            self.edit_managed = edit_managed

        # Since we have to behave nicely like a legacy client/bindings we use
        # an adapter around the session to not modify it's state.
        interface = endpoint_type.rstrip('URL')

        self.session = utils.AdapterWithTimeout(
            session,
            auth=session.auth,
            endpoint_override=endpoint,
            region_name=region_name,
            service_type=service_type,
            interface=interface,
            user_agent='python-designateclient-%s' % version.version_info,
            version='1',
            timeout=timeout,
        )

        def _load_controller(ext):
            controller = ext.plugin(client=self)
            setattr(self, ext.name, controller)

        # Load all controllers
        mgr = extension.ExtensionManager('designateclient.v1.controllers')
        mgr.map(_load_controller)

    def wrap_api_call(self, func, *args, **kw):
        """
        Wrap a self.<rest function> with exception handling

        :param func: The function to wrap
        """
        kw['raise_exc'] = False
        kw.setdefault('headers', {})
        kw['headers'].setdefault('Content-Type', 'application/json')
        if self.all_tenants:
            kw['headers'].update({'X-Auth-All-Projects': 'true'})
        if self.edit_managed:
            kw['headers'].update({'X-Designate-Edit-Managed-Records': 'true'})

        # Trigger the request
        response = func(*args, **kw)

        # Decode is response, if possible
        try:
            response_payload = response.json()
        except ValueError:
            response_payload = {}

        if response.status_code == 400:
            raise exceptions.BadRequest(**response_payload)
        elif response.status_code in (401, 403, 413):
            raise exceptions.Forbidden(**response_payload)
        elif response.status_code == 404:
            raise exceptions.NotFound(**response_payload)
        elif response.status_code == 409:
            raise exceptions.Conflict(**response_payload)
        elif response.status_code >= 500:
            raise exceptions.Unknown(**response_payload)
        else:
            return response

    def get(self, path, **kw):
        return self.wrap_api_call(self.session.get, path, **kw)

    def post(self, path, **kw):
        return self.wrap_api_call(self.session.post, path, **kw)

    def put(self, path, **kw):
        return self.wrap_api_call(self.session.put, path, **kw)

    def delete(self, path, **kw):
        return self.wrap_api_call(self.session.delete, path, **kw)
