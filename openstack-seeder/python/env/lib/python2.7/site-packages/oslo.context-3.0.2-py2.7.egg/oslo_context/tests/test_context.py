# -*- encoding: utf-8 -*-
# Copyright 2011 OpenStack Foundation.
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

import fixtures
import hashlib
import uuid
import warnings

from oslotest import base as test_base

from oslo_context import context
from oslo_context import fixture


def generate_id(name):
    return hashlib.md5(name.encode('utf-8')).hexdigest()


class WarningsFixture(fixtures.Fixture):

    def __init__(self, action="always", category=DeprecationWarning):
        super(WarningsFixture, self).__init__()
        self.action = action
        self.category = category

    def setUp(self):
        super(WarningsFixture, self).setUp()
        self._w = warnings.catch_warnings(record=True)
        self.log = self._w.__enter__()
        self.addCleanup(self._w.__exit__)
        warnings.simplefilter(self.action, self.category)

    def __len__(self):
        return len(self.log)

    def __getitem__(self, item):
        return self.log[item]


class Object(object):
    pass


class TestContext(context.RequestContext):
    """A test context with additional members

    This is representative of how at least some of our consumers use the
    RequestContext class in their projects.
    """
    FROM_DICT_EXTRA_KEYS = ['auth_token_info']

    def __init__(self, auth_token_info=None, **kwargs):
        super(TestContext, self).__init__(**kwargs)
        self.auth_token_info = auth_token_info

    def to_dict(self):
        d = super(TestContext, self).to_dict()
        d['auth_token_info'] = self.auth_token_info
        return d


class ContextTest(test_base.BaseTestCase):

    def setUp(self):
        super(ContextTest, self).setUp()
        self.warnings = self.useFixture(WarningsFixture())
        self.useFixture(fixture.ClearRequestContext())

    def test_context(self):
        ctx = context.RequestContext()
        self.assertTrue(ctx)

    def test_store_when_no_overwrite(self):
        # If no context exists we store one even if overwrite is false
        # (since we are not overwriting anything).
        ctx = context.RequestContext(overwrite=False)
        self.assertIs(context.get_current(), ctx)

    def test_no_overwrite(self):
        # If there is already a context in the cache a new one will
        # not overwrite it if overwrite=False.
        ctx1 = context.RequestContext(overwrite=True)
        context.RequestContext(overwrite=False)
        self.assertIs(context.get_current(), ctx1)

    def test_admin_no_overwrite(self):
        # If there is already a context in the cache creating an admin
        # context will not overwrite it.
        ctx1 = context.RequestContext(overwrite=True)
        context.get_admin_context()
        self.assertIs(context.get_current(), ctx1)
        self.assertFalse(ctx1.is_admin)

    def test_store_current(self):
        # By default a new context is stored.
        ctx = context.RequestContext()
        self.assertIs(context.get_current(), ctx)

    def test_no_context(self):
        self.assertIsNone(context.get_current())

    def test_admin_context_show_deleted_flag_default(self):
        ctx = context.get_admin_context()
        self.assertIsInstance(ctx, context.RequestContext)
        self.assertTrue(ctx.is_admin)
        self.assertFalse(ctx.show_deleted)
        self.assertIsNone(ctx.project_id)

    def test_admin_context_show_deleted_flag_set(self):
        ctx = context.get_admin_context(show_deleted=True)
        self.assertTrue(ctx.is_admin)
        self.assertTrue(ctx.show_deleted)

    def test_from_dict(self):
        dct = {
            "auth_token": "token1",
            "user": "user1",
            "user_name": "user1_name",
            "tenant": "tenant1",
            "project_name": "tenant1_name",
            "domain": "domain1",
            "domain_name": "domain1_name",
            "user_domain": "user_domain1",
            "user_domain_name": "user_domain1_name",
            "project_domain": "project_domain1",
            "project_domain_name": "project_domain1_name",
            "is_admin": True,
            "read_only": True,
            "show_deleted": True,
            "request_id": "request1",
            "global_request_id": "req-uuid",
            "resource_uuid": "instance1",
            "extra_data": "foo"
        }
        ctx = context.RequestContext.from_dict(dct)
        self.assertEqual(dct['auth_token'], ctx.auth_token)
        self.assertEqual(dct['user'], ctx.user_id)
        self.assertEqual(dct['tenant'], ctx.project_id)
        self.assertEqual(dct['domain'], ctx.domain_id)
        self.assertEqual(dct['user_domain'], ctx.user_domain_id)
        self.assertEqual(dct['project_domain'], ctx.project_domain_id)
        self.assertTrue(ctx.is_admin)
        self.assertTrue(ctx.read_only)
        self.assertTrue(ctx.show_deleted)
        self.assertEqual(dct['request_id'], ctx.request_id)
        self.assertEqual(dct['global_request_id'], ctx.global_request_id)
        self.assertEqual(dct['resource_uuid'], ctx.resource_uuid)
        self.assertEqual(dct['user_name'], ctx.user_name)
        self.assertEqual(dct['project_name'], ctx.project_name)
        self.assertEqual(dct['domain_name'], ctx.domain_name)
        self.assertEqual(dct['user_domain_name'], ctx.user_domain_name)
        self.assertEqual(dct['project_domain_name'], ctx.project_domain_name)

    def test_from_dict_unknown_keys(self):
        dct = {
            "auth_token": "token1",
            "user": "user1",
            "read_only": True,
            "roles": "role1,role2,role3",  # future review provides this
            "color": "red",
            "unknown": ""
        }
        ctx = context.RequestContext.from_dict(dct)
        self.assertEqual("token1", ctx.auth_token)
        self.assertEqual("user1", ctx.user_id)
        self.assertIsNone(ctx.project_id)
        self.assertFalse(ctx.is_admin)
        self.assertTrue(ctx.read_only)
        self.assertRaises(KeyError, lambda: ctx.__dict__['color'])

    def test_from_dict_overrides(self):
        dct = {
            "auth_token": "token1",
            "user": "user1",
            "read_only": True,
            "roles": "role1,role2,role3",
            "color": "red",
            "unknown": ""
        }
        ctx = context.RequestContext.from_dict(dct,
                                               user="user2",
                                               project_name="project1")
        self.assertEqual("token1", ctx.auth_token)
        self.assertEqual("user2", ctx.user)
        self.assertEqual("project1", ctx.project_name)
        self.assertIsNone(ctx.tenant)
        self.assertFalse(ctx.is_admin)
        self.assertTrue(ctx.read_only)

    def test_from_dict_extended(self):
        initial = TestContext(auth_token_info='foo')
        dct = initial.to_dict()
        final = TestContext.from_dict(dct)
        self.assertEqual('foo', final.auth_token_info)
        self.assertEqual(dct, final.to_dict())

    def test_is_user_context(self):
        self.assertFalse(context.is_user_context(None))
        ctx = context.RequestContext(is_admin=True)
        self.assertFalse(context.is_user_context(ctx))
        ctx = context.RequestContext(is_admin=False)
        self.assertTrue(context.is_user_context(ctx))
        self.assertFalse(context.is_user_context("non context object"))

    def test_from_environ_variables(self):
        auth_token = uuid.uuid4().hex
        user_name = uuid.uuid4().hex
        user_id = generate_id(user_name)
        project_name = uuid.uuid4().hex
        project_id = generate_id(project_name)
        domain_name = uuid.uuid4().hex
        domain_id = generate_id(domain_name)
        user_domain_name = uuid.uuid4().hex
        user_domain_id = generate_id(user_domain_name)
        project_domain_name = uuid.uuid4().hex
        project_domain_id = generate_id(project_domain_name)
        roles = [uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex]
        request_id = uuid.uuid4().hex
        global_request_id = uuid.uuid4().hex
        service_token = uuid.uuid4().hex
        service_user_id = uuid.uuid4().hex
        service_user_name = uuid.uuid4().hex
        service_user_domain_id = uuid.uuid4().hex
        service_user_domain_name = uuid.uuid4().hex
        service_project_id = uuid.uuid4().hex
        service_project_name = uuid.uuid4().hex
        service_project_domain_id = uuid.uuid4().hex
        service_project_domain_name = uuid.uuid4().hex
        service_roles = [uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex]

        environ = {
            'HTTP_X_AUTH_TOKEN': auth_token,
            'HTTP_X_USER_ID': user_id,
            'HTTP_X_PROJECT_ID': project_id,
            'HTTP_X_DOMAIN_ID': domain_id,
            'HTTP_X_USER_DOMAIN_ID': user_domain_id,
            'HTTP_X_PROJECT_DOMAIN_ID': project_domain_id,
            'HTTP_X_ROLES': ','.join(roles),
            'HTTP_X_USER_NAME': user_name,
            'HTTP_X_PROJECT_NAME': project_name,
            'HTTP_X_USER_DOMAIN_NAME': user_domain_name,
            'HTTP_X_PROJECT_DOMAIN_NAME': project_domain_name,
            'HTTP_X_SERVICE_TOKEN': service_token,
            'HTTP_X_SERVICE_USER_ID': service_user_id,
            'HTTP_X_SERVICE_USER_NAME': service_user_name,
            'HTTP_X_SERVICE_USER_DOMAIN_ID': service_user_domain_id,
            'HTTP_X_SERVICE_USER_DOMAIN_NAME': service_user_domain_name,
            'HTTP_X_SERVICE_PROJECT_ID': service_project_id,
            'HTTP_X_SERVICE_PROJECT_NAME': service_project_name,
            'HTTP_X_SERVICE_PROJECT_DOMAIN_ID': service_project_domain_id,
            'HTTP_X_SERVICE_PROJECT_DOMAIN_NAME': service_project_domain_name,
            'HTTP_X_SERVICE_ROLES': ','.join(service_roles),
            'openstack.request_id': request_id,
            'openstack.global_request_id': global_request_id,
        }

        ctx = context.RequestContext.from_environ(environ)

        self.assertEqual(auth_token, ctx.auth_token)
        self.assertEqual(user_id, ctx.user_id)
        self.assertEqual(user_name, ctx.user_name)
        self.assertEqual(project_id, ctx.project_id)
        self.assertEqual(domain_id, ctx.domain_id)
        self.assertEqual(project_name, ctx.project_name)
        self.assertEqual(user_domain_id, ctx.user_domain_id)
        self.assertEqual(user_domain_name, ctx.user_domain_name)
        self.assertEqual(project_domain_id, ctx.project_domain_id)
        self.assertEqual(project_domain_name, ctx.project_domain_name)
        self.assertEqual(roles, ctx.roles)
        self.assertEqual(request_id, ctx.request_id)
        self.assertEqual(global_request_id, ctx.global_request_id)
        self.assertEqual(service_token, ctx.service_token)
        self.assertEqual(service_user_id, ctx.service_user_id)
        self.assertEqual(service_user_name, ctx.service_user_name)
        self.assertEqual(service_user_domain_id, ctx.service_user_domain_id)
        self.assertEqual(service_user_domain_name,
                         ctx.service_user_domain_name)
        self.assertEqual(service_project_id, ctx.service_project_id)
        self.assertEqual(service_project_name, ctx.service_project_name)
        self.assertEqual(service_project_domain_id,
                         ctx.service_project_domain_id)
        self.assertEqual(service_project_domain_name,
                         ctx.service_project_domain_name)
        self.assertEqual(service_roles, ctx.service_roles)

    def test_from_environ_no_roles(self):
        ctx = context.RequestContext.from_environ(environ={})
        self.assertEqual([], ctx.roles)

        ctx = context.RequestContext.from_environ(environ={'HTTP_X_ROLES': ''})
        self.assertEqual([], ctx.roles)

    def test_from_environ_deprecated_variables(self):
        value = uuid.uuid4().hex

        environ = {'HTTP_X_USER': value}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(value, ctx.user)

        environ = {'HTTP_X_TENANT_ID': value}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(value, ctx.project_id)

        environ = {'HTTP_X_STORAGE_TOKEN': value}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(value, ctx.auth_token)

        environ = {'HTTP_X_TENANT': value}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(value, ctx.tenant)

        environ = {'HTTP_X_ROLE': value}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual([value], ctx.roles)

        environ = {'HTTP_X_TENANT_NAME': value}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(value, ctx.project_name)

    def test_from_environ_deprecated_precendence(self):
        old = uuid.uuid4().hex
        new = uuid.uuid4().hex
        override = uuid.uuid4().hex

        environ = {'HTTP_X_USER': old,
                   'HTTP_X_USER_ID': new}

        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(new, ctx.user)

        ctx = context.RequestContext.from_environ(environ=environ,
                                                  user=override)
        self.assertEqual(override, ctx.user)

        environ = {'HTTP_X_TENANT': old,
                   'HTTP_X_PROJECT_ID': new}

        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(new, ctx.project_id)

        ctx = context.RequestContext.from_environ(environ=environ,
                                                  tenant=override)
        self.assertEqual(override, ctx.project_id)

        environ = {'HTTP_X_TENANT_NAME': old,
                   'HTTP_X_PROJECT_NAME': new}

        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(new, ctx.project_name)

    def test_from_environ_strip_roles(self):
        environ = {'HTTP_X_ROLES': ' abc\t,\ndef\n,ghi\n\n',
                   'HTTP_X_SERVICE_ROLES': ' jkl\t,\nmno\n,pqr\n\n'}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertEqual(['abc', 'def', 'ghi'], ctx.roles)
        self.assertEqual(['jkl', 'mno', 'pqr'], ctx.service_roles)

    def test_environ_admin_project(self):
        environ = {}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertIs(True, ctx.is_admin_project)
        self.assertIs(True, ctx.to_policy_values()['is_admin_project'])

        environ = {'HTTP_X_IS_ADMIN_PROJECT': 'True'}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertIs(True, ctx.is_admin_project)
        self.assertIs(True, ctx.to_policy_values()['is_admin_project'])

        environ = {'HTTP_X_IS_ADMIN_PROJECT': 'False'}
        ctx = context.RequestContext.from_environ(environ=environ)
        self.assertIs(False, ctx.is_admin_project)
        self.assertIs(False, ctx.to_policy_values()['is_admin_project'])

    def test_from_function_and_args(self):
        ctx = context.RequestContext(user="user1")
        arg = []
        kw = dict(c=ctx, s="s")
        fn = context.get_context_from_function_and_args
        ctx1 = context.get_context_from_function_and_args(fn, arg, kw)
        self.assertIs(ctx1, ctx)

    def test_not_in_from_function_and_args(self):
        arg = []
        kw = dict()
        fn = context.get_context_from_function_and_args
        ctx1 = context.get_context_from_function_and_args(fn, arg, kw)
        self.assertIsNone(ctx1)

    def test_values(self):
        auth_token = "token1"
        # test unicode support
        user_name = u"John Gāo"
        user_id = generate_id(user_name)
        project_name = 'tenant1'
        project_id = generate_id(project_name)
        domain_name = 'domain1'
        domain_id = generate_id(domain_name)
        user_domain_name = 'user_domain1'
        user_domain_id = generate_id(user_domain_name)
        project_domain_name = 'project_domain1'
        project_domain_id = generate_id(project_domain_name)
        is_admin = True
        read_only = True
        show_deleted = True
        request_id = "id1"
        global_request_id = "req-id1"
        resource_uuid = "uuid1"

        ctx = context.RequestContext(auth_token=auth_token,
                                     user=user_id,
                                     user_name=user_name,
                                     tenant=project_id,
                                     project_name=project_name,
                                     domain=domain_id,
                                     domain_name=domain_name,
                                     user_domain=user_domain_id,
                                     user_domain_name=user_domain_name,
                                     project_domain=project_domain_id,
                                     project_domain_name=project_domain_name,
                                     is_admin=is_admin,
                                     read_only=read_only,
                                     show_deleted=show_deleted,
                                     request_id=request_id,
                                     global_request_id=global_request_id,
                                     resource_uuid=resource_uuid)
        self.assertEqual(auth_token, ctx.auth_token)
        self.assertEqual(user_id, ctx.user_id)
        self.assertEqual(user_name, ctx.user_name)
        self.assertEqual(project_id, ctx.project_id)
        self.assertEqual(project_name, ctx.project_name)
        self.assertEqual(domain_id, ctx.domain_id)
        self.assertEqual(domain_name, ctx.domain_name)
        self.assertEqual(user_domain_id, ctx.user_domain_id)
        self.assertEqual(user_domain_name, ctx.user_domain_name)
        self.assertEqual(project_domain_id, ctx.project_domain_id)
        self.assertEqual(project_domain_name, ctx.project_domain_name)
        self.assertEqual(is_admin, ctx.is_admin)
        self.assertEqual(read_only, ctx.read_only)
        self.assertEqual(show_deleted, ctx.show_deleted)
        self.assertEqual(request_id, ctx.request_id)
        self.assertEqual(resource_uuid, ctx.resource_uuid)

        d = ctx.to_dict()
        self.assertIn('auth_token', d)
        self.assertIn('user', d)
        self.assertIn('tenant', d)
        self.assertIn('domain', d)
        self.assertIn('user_domain', d)
        self.assertIn('project_domain', d)
        self.assertIn('is_admin', d)
        self.assertIn('read_only', d)
        self.assertIn('show_deleted', d)
        self.assertIn('request_id', d)
        self.assertIn('resource_uuid', d)
        self.assertIn('user_identity', d)
        self.assertIn('roles', d)
        self.assertNotIn('user_name', d)
        self.assertNotIn('project_name', d)
        self.assertNotIn('domain_name', d)
        self.assertNotIn('user_domain_name', d)
        self.assertNotIn('project_domain_name', d)

        self.assertEqual(auth_token, d['auth_token'])
        self.assertEqual(project_id, d['tenant'])
        self.assertEqual(domain_id, d['domain'])
        self.assertEqual(user_domain_id, d['user_domain'])
        self.assertEqual(project_domain_id, d['project_domain'])
        self.assertEqual(is_admin, d['is_admin'])
        self.assertEqual(read_only, d['read_only'])
        self.assertEqual(show_deleted, d['show_deleted'])
        self.assertEqual(request_id, d['request_id'])
        self.assertEqual(resource_uuid, d['resource_uuid'])
        user_identity = "%s %s %s %s %s" % (user_id, project_id, domain_id,
                                            user_domain_id, project_domain_id)
        self.assertEqual(user_identity, d['user_identity'])
        self.assertEqual([], d['roles'])

        d = ctx.get_logging_values()
        self.assertIn('auth_token', d)
        self.assertEqual(d['auth_token'], '***')
        self.assertIn('user', d)
        self.assertIn('tenant', d)
        self.assertIn('domain', d)
        self.assertIn('user_domain', d)
        self.assertIn('project_domain', d)
        self.assertIn('is_admin', d)
        self.assertIn('read_only', d)
        self.assertIn('show_deleted', d)
        self.assertIn('request_id', d)
        self.assertIn('global_request_id', d)
        self.assertIn('resource_uuid', d)
        self.assertIn('user_identity', d)
        self.assertIn('roles', d)
        self.assertIn('user_name', d)
        self.assertIn('project_name', d)
        self.assertIn('domain_name', d)
        self.assertIn('user_domain_name', d)
        self.assertIn('project_domain_name', d)

        self.assertEqual(user_name, d['user_name'])
        self.assertEqual(project_name, d['project_name'])
        self.assertEqual(domain_name, d['domain_name'])
        self.assertEqual(user_domain_name, d['user_domain_name'])
        self.assertEqual(project_domain_name, d['project_domain_name'])

    def test_auth_token_info_removed(self):
        ctx = TestContext(auth_token_info={'auth_token': 'topsecret'})
        d = ctx.get_logging_values()
        self.assertNotIn('auth_token_info', d)

    def test_dict_empty_user_identity(self):
        ctx = context.RequestContext()
        d = ctx.to_dict()
        self.assertEqual("- - - - -", d['user_identity'])

    def test_generate_request_id(self):
        id = context.generate_request_id()
        self.assertEqual("req-", id[:4])

    def test_generate_request_id_unique(self):
        id1 = context.generate_request_id()
        id2 = context.generate_request_id()
        self.assertNotEqual(id1, id2)

    def test_no_global_id_by_default(self):
        ctx = context.RequestContext()
        self.assertIsNone(ctx.global_request_id)
        d = ctx.to_dict()
        self.assertIsNone(d['global_request_id'])

    def test_policy_dict(self):
        user = uuid.uuid4().hex
        user_domain = uuid.uuid4().hex
        tenant = uuid.uuid4().hex
        project_domain = uuid.uuid4().hex
        roles = [uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex]
        service_user_id = uuid.uuid4().hex
        service_project_id = uuid.uuid4().hex
        service_roles = [uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex]

        # default is_admin_project is True
        ctx = context.RequestContext(user=user,
                                     user_domain=user_domain,
                                     tenant=tenant,
                                     project_domain=project_domain,
                                     roles=roles,
                                     service_user_id=service_user_id,
                                     service_project_id=service_project_id,
                                     service_roles=service_roles)

        self.assertEqual({'user_id': user,
                          'user_domain_id': user_domain,
                          'system_scope': None,
                          'domain_id': None,
                          'project_id': tenant,
                          'project_domain_id': project_domain,
                          'roles': roles,
                          'is_admin_project': True,
                          'service_user_id': service_user_id,
                          'service_user_domain_id': None,
                          'service_project_id': service_project_id,
                          'service_project_domain_id': None,
                          'service_roles': service_roles},
                         ctx.to_policy_values())

        # NOTE(lbragstad): This string has special meaning in that the value
        # ``all`` represents the entire deployment system.
        system_all = 'all'

        ctx = context.RequestContext(user=user,
                                     user_domain=user_domain,
                                     system_scope=system_all,
                                     roles=roles,
                                     service_user_id=service_user_id,
                                     service_project_id=service_project_id,
                                     service_roles=service_roles)

        self.assertEqual({'user_id': user,
                          'user_domain_id': user_domain,
                          'system_scope': system_all,
                          'domain_id': None,
                          'project_id': None,
                          'project_domain_id': None,
                          'roles': roles,
                          'is_admin_project': True,
                          'service_user_id': service_user_id,
                          'service_user_domain_id': None,
                          'service_project_id': service_project_id,
                          'service_project_domain_id': None,
                          'service_roles': service_roles},
                         ctx.to_policy_values())

        # context representing a domain-scoped token.
        domain_id = uuid.uuid4().hex
        ctx = context.RequestContext(user=user,
                                     user_domain=user_domain,
                                     domain_id=domain_id,
                                     roles=roles,
                                     service_user_id=service_user_id,
                                     service_project_id=service_project_id,
                                     service_roles=service_roles)

        self.assertEqual({'user_id': user,
                          'user_domain_id': user_domain,
                          'system_scope': None,
                          'domain_id': domain_id,
                          'project_id': None,
                          'project_domain_id': None,
                          'roles': roles,
                          'is_admin_project': True,
                          'service_user_id': service_user_id,
                          'service_user_domain_id': None,
                          'service_project_id': service_project_id,
                          'service_project_domain_id': None,
                          'service_roles': service_roles},
                         ctx.to_policy_values())

        ctx = context.RequestContext(user=user,
                                     user_domain=user_domain,
                                     tenant=tenant,
                                     project_domain=project_domain,
                                     roles=roles,
                                     is_admin_project=False,
                                     service_user_id=service_user_id,
                                     service_project_id=service_project_id,
                                     service_roles=service_roles)

        self.assertEqual({'user_id': user,
                          'user_domain_id': user_domain,
                          'system_scope': None,
                          'domain_id': None,
                          'project_id': tenant,
                          'project_domain_id': project_domain,
                          'roles': roles,
                          'is_admin_project': False,
                          'service_user_id': service_user_id,
                          'service_user_domain_id': None,
                          'service_project_id': service_project_id,
                          'service_project_domain_id': None,
                          'service_roles': service_roles},
                         ctx.to_policy_values())

    def test_policy_deprecations(self):
        user = uuid.uuid4().hex
        user_domain = uuid.uuid4().hex
        tenant = uuid.uuid4().hex
        project_domain = uuid.uuid4().hex
        roles = [uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex]

        ctx = context.RequestContext(user=user,
                                     user_domain=user_domain,
                                     tenant=tenant,
                                     project_domain=project_domain,
                                     roles=roles)

        policy = ctx.to_policy_values()
        key = uuid.uuid4().hex
        val = uuid.uuid4().hex

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # no warning triggered by adding key to dict
            policy[key] = val
            self.assertEqual(0, len(w))

            # warning triggered by fetching key from dict
            self.assertIs(val, policy[key])
            self.assertEqual(1, len(w))
            self.assertIn(key, str(w[0].message))

    def test_deprecated_args(self):
        user_id = uuid.uuid4().hex
        project_id = uuid.uuid4().hex
        domain_id = uuid.uuid4().hex
        user_domain_id = uuid.uuid4().hex
        project_domain_id = uuid.uuid4().hex

        ctx = context.RequestContext(user_id=user_id,
                                     project_id=project_id,
                                     domain_id=domain_id,
                                     user_domain_id=user_domain_id,
                                     project_domain_id=project_domain_id)

        self.assertEqual(0, len(self.warnings))
        self.assertEqual(user_id, ctx.user_id)
        self.assertEqual(project_id, ctx.project_id)
        self.assertEqual(domain_id, ctx.domain_id)
        self.assertEqual(user_domain_id, ctx.user_domain_id)
        self.assertEqual(project_domain_id, ctx.project_domain_id)

        self.assertEqual(0, len(self.warnings))
        self.assertEqual(user_id, ctx.user)
        self.assertEqual(1, len(self.warnings))
        self.assertEqual(project_id, ctx.tenant)
        self.assertEqual(2, len(self.warnings))
        self.assertEqual(domain_id, ctx.domain)
        self.assertEqual(3, len(self.warnings))
        self.assertEqual(user_domain_id, ctx.user_domain)
        self.assertEqual(4, len(self.warnings))
        self.assertEqual(project_domain_id, ctx.project_domain)
        self.assertEqual(5, len(self.warnings))
