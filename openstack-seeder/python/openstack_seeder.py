#!/usr/bin/env python

# Copyright 2017 SAP SE
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import copy
import logging
import os
import re
import sys
from urlparse import urlparse

import requests
import yaml
from designateclient.v2 import client as designateclient
from keystoneauth1 import session
from keystoneauth1.loading import cli
from keystoneclient import exceptions
from keystoneclient.v3 import client as keystoneclient
from neutronclient.v2_0 import client as neutronclient
from novaclient import client as novaclient
from novaclient import exceptions as novaexceptions
from osc_placement.http import SessionClient as placementclient
from osc_placement.resources.resource_class import PER_CLASS_URL
from raven.base import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler
from raven.transport.requests import RequestsHTTPTransport
from swiftclient import client as swiftclient
from urllib3.exceptions import InsecureRequestWarning

# caches
role_cache = {}
domain_cache = {}
project_cache = {}
user_cache = {}
group_cache = {}
subnetpool_cache = {}
network_cache = {}
subnet_cache = {}

# assignments to be resolved after everything else has been processed
group_members = {}
role_assignments = []


def get_role_id(name, keystone):
    """ get a (cached) role-id for a role name """
    result = None
    if name not in role_cache:
        roles = keystone.roles.list(name=name)
        if roles:
            result = role_cache[name] = roles[0].id
    else:
        result = role_cache[name]
    if not result:
        logging.error("role %s not found" % name)
    return result


def get_domain_id(name, keystone):
    """ get a (cached) domain-id for a domain name """
    result = None
    if name not in domain_cache:
        domains = keystone.domains.list(name=name)
        if domains:
            result = domain_cache[name] = domains[0].id
    else:
        result = domain_cache[name]
    if not result:
        logging.error("domain %s not found" % name)
    return result


def get_project_id(domain, name, keystone):
    """ get a (cached) project-id for a domain and project name """
    result = None
    if domain not in project_cache:
        project_cache[domain] = dict()
    if name not in project_cache[domain]:
        projects = keystone.projects.list(
            domain=get_domain_id(domain, keystone),
            name=name)
        if projects:
            result = project_cache[domain][name] = projects[0].id
    else:
        result = project_cache[domain][name]
    if not result:
        logging.error("project %s/%s not found" % (domain, name))
    return result


def get_user_id(domain, name, keystone):
    """ get a (cached) user-id for a domain and user name """
    result = None
    if domain not in user_cache:
        user_cache[domain] = dict()
    if name not in user_cache[domain]:
        users = keystone.users.list(
            domain=get_domain_id(domain, keystone),
            name=name)
        if users:
            result = user_cache[domain][name] = users[0].id
    else:
        result = user_cache[domain][name]
    if not result:
        logging.error("user %s/%s not found" % (domain, name))
    return result


def get_group_id(domain, name, keystone):
    """ get a (cached) group-id for a domain and group name """
    result = None
    if domain not in group_cache:
        group_cache[domain] = dict()
    if name not in group_cache[domain]:
        groups = keystone.groups.list(
            domain=get_domain_id(domain, keystone),
            name=name)
        if groups:
            result = group_cache[domain][name] = groups[0].id
    else:
        result = group_cache[domain][name]
    if not result:
        logging.error("group %s/%s not found" % (domain, name))
    return result


def get_subnetpool_id(project_id, name, neutron):
    """ get a (cached) subnetpool-id for a project-id and subnetpool name """
    if project_id not in subnetpool_cache:
        subnetpool_cache[project_id] = dict()
    if name not in subnetpool_cache[project_id]:
        query = {'tenant_id': project_id, 'name': name}
        result = neutron.list_subnetpools(retrieve_all=True, **query)
        if result and result['subnetpools']:
            result = subnetpool_cache[project_id][name] = \
            result['subnetpools'][0]['id']
        else:
            result = None
    else:
        result = subnetpool_cache[project_id][name]
    if not result:
        logging.error("subnetpool %s/%s not found" % (project_id, name))
    return result


def get_network_id(project_id, name, neutron):
    """ get a (cached) network-id for a project-id and network name """
    if project_id not in network_cache:
        network_cache[project_id] = dict()
    if name not in network_cache[project_id]:
        query = {'tenant_id': project_id, 'name': name}
        result = neutron.list_networks(retrieve_all=True, **query)
        if result and result['networks']:
            result = network_cache[project_id][name] = \
            result['networks'][0]['id']
        else:
            result = None
    else:
        result = network_cache[project_id][name]
    if not result:
        logging.error("network %s/%s not found" % (project_id, name))
    return result


def get_subnet_id(project_id, name, neutron):
    """ get a (cached) subnet-id for a project-id and subnet name """
    if project_id not in subnet_cache:
        subnet_cache[project_id] = dict()
    if name not in subnet_cache[project_id]:
        query = {'tenant_id': project_id, 'name': name}
        result = neutron.list_subnets(retrieve_all=True, **query)
        if result and result['subnets']:
            result = subnet_cache[project_id][name] = \
            result['subnets'][0]['id']
        else:
            result = None
    else:
        result = subnet_cache[project_id][name]
    if not result:
        logging.error("subnet %s/%s not found" % (project_id, name))
    return result


def sanitize(source, keys):
    result = {}
    for attr in keys:
        if attr in source:
            if isinstance(source[attr], str):
                result[attr] = source[attr].strip()
            else:
                result[attr] = source[attr]
    return result


def redact(source,
           keys=('password', 'secret', 'userPassword', 'cam_password')):
    def _blankout(data, k):
        if isinstance(data, list):
            for item in data:
                _blankout(item, k)
        elif isinstance(data, dict):
            for attr in keys:
                if attr in data:
                    if isinstance(data[attr], str):
                        data[attr] = '********'
            for k, v in data.iteritems():
                _blankout(v, keys)

    result = copy.deepcopy(source)
    _blankout(result, keys)
    return result


def seed_role(role, keystone):
    """ seed a keystone role """
    logging.debug("seeding role %s" % role)

    result = keystone.roles.list(name=role)
    if not result:
        logging.info("create role '%s'" % role)
        resource = keystone.roles.create(name=role)
    else:
        resource = result[0]

    role_cache[resource.name] = resource.id


def seed_region(region, keystone):
    """ seed a keystone region """
    logging.debug("seeding region %s" % region)

    region = sanitize(region,
                      ('id', 'description', 'parent_region'))
    if 'id' not in region or not region['id']:
        logging.warn(
            "skipping region '%s', since it is misconfigured" % region)
        return

    try:
        result = keystone.regions.get(region['id'])
    except exceptions.NotFound:
        result = None

    if not result:
        logging.info("create region '%s'" % region['id'])
        keystone.regions.create(**region)
    else:  # wtf: why can't they deal with parent_region(_id) consistently
        wtf = region.copy()
        if 'parent_region' in wtf:
            wtf['parent_region_id'] = wtf.pop('parent_region')
        for attr in wtf.keys():
            if wtf[attr] != result._info.get(attr, ''):
                logging.info(
                    "%s differs. update region '%s'" % (attr, region))
                keystone.regions.update(result.id, **region)
                break


def seed_endpoints(service, endpoints, keystone):
    """ seed a keystone service endpoints """
    logging.debug("seeding endpoints %s %s" % (service.name, endpoints))

    for endpoint in endpoints:
        endpoint = sanitize(endpoint, (
            'interface', 'region', 'url', 'enabled', 'name'))
        if 'interface' not in endpoint or not endpoint['interface']:
            logging.warn(
                "skipping endpoint '%s/%s', since it is misconfigured" % (
                    service['name'], endpoint))
            continue

        if 'url' not in endpoint or not endpoint['url']:
            logging.warn(
                "skipping endpoint '%s/%s', since it has no URL configured" % (
                    service.name, endpoint['interface']))
            continue
        try:
            parsed = urlparse(endpoint['url'])
            if not parsed.scheme or not parsed.netloc:
                logging.warn(
                    "skipping endpoint '%s/%s', since its URL is misconfigured" % (
                        service.name, endpoint['interface']))
                continue
        except Exception:
            logging.warn(
                "skipping endpoint '%s/%s', since its URL is misconfigured" % (
                    service.name, endpoint['interface']))
            continue

        region = None
        if 'region' in endpoint:
            region = endpoint['region']
            if not region or not region.strip():
                logging.warn(
                    "skipping endpoint '%s/%s', since its region is misconfigured" % (
                        service.name, endpoint['interface']))
                continue

        result = keystone.endpoints.list(service=service.id,
                                         interface=endpoint[
                                             'interface'],
                                         region_id=region)
        if not result:
            logging.info("create endpoint '%s/%s'" % (
            service.name, endpoint['interface']))
            keystone.endpoints.create(service.id, **endpoint)
        else:
            resource = result[0]
            for attr in endpoint.keys():
                if endpoint[attr] != resource._info.get(attr, ''):
                    logging.info("%s differs. update endpoint '%s/%s'" %
                                 (attr, service.name,
                                  endpoint['interface']))
                    keystone.endpoints.update(resource.id, **endpoint)
                    break


def seed_service(service, keystone):
    """ seed a keystone service """
    logging.debug("seeding service %s" % service)
    endpoints = None
    if 'endpoints' in service:
        endpoints = service.pop('endpoints', None)

    service = sanitize(service,
                       ('type', 'name', 'enabled', 'description'))
    if 'name' not in service or not service['name'] \
            or 'type' not in service or not service['type']:
        logging.warn(
            "skipping service '%s', since it is misconfigured" % service)
        return

    result = keystone.services.list(name=service['name'],
                                    type=service['type'])
    if not result:
        logging.info(
            "create service '%s/%s'" % (
            service['name'], service['type']))
        resource = keystone.services.create(**service)
    else:
        resource = result[0]
        for attr in service.keys():
            if service[attr] != resource._info.get(attr, ''):
                logging.info("%s differs. update service '%s/%s'" % (
                    attr, service['name'], service['type']))
                keystone.services.update(resource.id, **service)
                break

    if endpoints:
        seed_endpoints(resource, endpoints, keystone)


def seed_users(domain, users, keystone):
    """ seed keystone users and their role-assignments """
    logging.debug("seeding users %s %s" % (domain.name, users))

    for user in users:
        roles = None
        if 'roles' in user:
            roles = user.pop('roles')

        if '@' not in user['name']:
            user = sanitize(user, (
                'name', 'email', 'description', 'password', 'enabled',
                'default_project'))

            if 'name' not in user or not user['name']:
                logging.warn(
                    "skipping user '%s/%s', since it is misconfigured" % (
                        domain.name, redact(user)))
                continue

            result = keystone.users.list(domain=domain.id,
                                         name=user['name'])
            if not result:
                logging.info(
                    "create user '%s/%s'" % (domain.name, user['name']))
                resource = keystone.users.create(domain=domain, **user)
            else:
                resource = result[0]
                for attr in user.keys():
                    if attr == 'password':
                        continue
                    if user[attr] != resource._info.get(attr, ''):
                        logging.info(
                            "%s differs. update user '%s/%s' (%s)" % (
                                attr, domain.name, user['name'], attr))
                        keystone.users.update(resource.id, **user)
                        break

            # cache the user id
            if domain.name not in user_cache:
                user_cache[domain.name] = dict()
            user_cache[domain.name][resource.name] = resource.id

        # add the users role assignments to the list to be resolved later on
        if roles:
            for role in roles:
                assignment = dict()
                assignment['role'] = role['role']
                assignment['user'] = '%s@%s' % (
                user['name'], domain.name)
                if 'project' in role:
                    if '@' in role['project']:
                        assignment['project'] = role['project']
                    else:
                        assignment['project'] = '%s@%s' % (
                            role['project'], domain.name)
                elif 'project_id' in role:
                    assignment['project_id'] = role['project_id']
                elif 'domain' in role:
                    assignment['domain'] = role['domain']
                if 'inherited' in role:
                    assignment['inherited'] = role['inherited']

                role_assignments.append(assignment)


def seed_groups(domain, groups, keystone):
    """ seed keystone groups """
    logging.debug("seeding groups %s %s" % (domain.name, groups))

    for group in groups:
        users = None
        if 'users' in group:
            users = group.pop('users')
        roles = None
        if 'roles' in group:
            roles = group.pop('roles')

        group = sanitize(group, ('name', 'description'))

        if 'name' not in group or not group['name']:
            logging.warn(
                "skipping group '%s/%s', since it is misconfigured" %
                (domain.name, group))
            continue

        result = keystone.groups.list(domain=domain.id,
                                      name=group['name'])
        if not result:
            logging.info(
                "create group '%s/%s'" % (domain.name, group['name']))
            resource = keystone.groups.create(domain=domain, **group)
        else:
            resource = result[0]
            for attr in group.keys():
                if group[attr] != resource._info.get(attr, ''):
                    logging.info(
                        "%s differs. update group '%s/%s'" % (
                            attr, domain.name, group['name']))
                    keystone.groups.update(resource.id, **group)
                    break

        # cache the group id
        if domain.name not in group_cache:
            group_cache[domain.name] = {}
        group_cache[domain.name][resource.name] = resource.id

        if users:
            for user in users:
                if resource.id not in group_members:
                    group_members[resource.id] = []
                if '@' in user:
                    group_members[resource.id].append(user)
                else:
                    group_members[resource.id].append(
                        '%s@%s' % (user, domain.name))

        # add the groups role assignments to the list to be resolved later on
        if roles:
            for role in roles:
                assignment = dict()
                assignment['role'] = role['role']
                assignment['group'] = '%s@%s' % (
                group['name'], domain.name)
                if 'project' in role:
                    if '@' in role['project']:
                        assignment['project'] = role['project']
                    else:
                        assignment['project'] = '%s@%s' % (
                            role['project'], domain.name)
                elif 'project_id' in role:
                    assignment['project_id'] = role['project_id']
                elif 'domain' in role:
                    assignment['domain'] = role['domain']
                if 'inherited' in role:
                    assignment['inherited'] = role['inherited']
                role_assignments.append(assignment)


def seed_project_endpoints(project, endpoints, keystone):
    """ seed a keystone projects endpoints (OS-EP-FILTER)"""
    logging.debug(
        "seeding project endpoint %s %s" % (project.name, endpoints))

    for name, endpoint in endpoints.iteritems():
        if 'endpoint_id' in endpoint:
            try:
                ep = keystone.endpoints.find(id=endpoint['endpoint_id'])
                try:
                    keystone.endpoint_filter.check_endpoint_in_project(
                        project,
                        ep)
                except exceptions.NotFound:
                    logging.info(
                        "add project endpoint '%s %s'" % (
                            project.name, ep))
                    keystone.endpoint_filter.add_endpoint_to_project(
                        project,
                        ep)
            except exceptions.NotFound as e:
                logging.error(
                    'could not configure project endpoints for %s: endpoint %s not found: %s' % (
                        project.name, endpoint, e))
        else:
            try:
                svc = keystone.services.find(name=endpoint['service'])
                result = keystone.endpoints.list(service=svc.id,
                                                 region_id=endpoint[
                                                     'region'])
                for ep in result:
                    try:
                        keystone.endpoint_filter.check_endpoint_in_project(
                            project, ep)
                    except exceptions.NotFound:
                        logging.info(
                            "add project endpoint '%s %s'" % (
                                project.name, ep))
                        keystone.endpoint_filter.add_endpoint_to_project(
                            project,
                            ep)
                    except Exception as e:
                        logging.error(
                            'could not configure project endpoints for %s: endpoint %s not found: %s' % (
                                project.name, ep, e))
            except exceptions.NotFound as e:
                logging.error(
                    'could not configure project endpoints for %s: service %s not found: %s' % (
                        project.name, endpoint, e))
                raise


def seed_projects(domain, projects, args, sess):
    """
    seed keystone projects and their dependant objects
    """

    logging.debug("seeding projects %s %s" % (domain.name, projects))

    # grab a keystone client
    keystone = keystoneclient.Client(session=sess,
                                     interface=args.interface)

    for project in projects:
        roles = None
        if 'roles' in project:
            roles = project.pop('roles', None)
        endpoints = None
        if 'project_endpoints' in project:
            endpoints = project.pop('project_endpoints', None)

        network_quota = None
        if 'network_quota' in project:
            network_quota = project.pop('network_quota', None)

        address_scopes = None
        if 'address_scopes' in project:
            address_scopes = project.pop('address_scopes', None)

        subnet_pools = None
        if 'subnet_pools' in project:
            subnet_pools = project.pop('subnet_pools', None)

        networks = None
        if 'networks' in project:
            networks = project.pop('networks', None)

        routers = None
        if 'routers' in project:
            routers = project.pop('routers', None)

        swift = project.pop('swift', None)

        dns_quota = project.pop('dns_quota', None)

        dns_zones = project.pop('dns_zones', None)

        dns_tsig_keys = project.pop('dns_tsigkeys', None)

        flavors = project.pop('flavors', None)

        project = sanitize(project,
                           ('name', 'description', 'enabled', 'parent'))

        if 'name' not in project or not project['name']:
            logging.warn(
                "skipping project '%s/%s', since it is misconfigured" % (
                    domain.name, project))
            continue

        # resolve parent project if specified
        if 'parent' in project:
            parent_id = get_project_id(domain.name, project['parent'],
                                       keystone)
            if not parent_id:
                logging.warn(
                    "skipping project '%s/%s', since its parent project is missing" % (
                        domain.name, project))
                continue
            else:
                project['parent_id'] = parent_id

        project.pop('parent', None)

        result = keystone.projects.list(domain=domain.id,
                                        name=project['name'])
        if not result:
            logging.info(
                "create project '%s/%s'" % (
                domain.name, project['name']))
            resource = keystone.projects.create(domain=domain,
                                                **project)
        else:
            resource = result[0]
            for attr in project.keys():
                if project[attr] != resource._info.get(attr, ''):
                    logging.info(
                        "%s differs. update project '%s/%s'" % (
                            attr, domain.name, project['name']))
                    keystone.projects.update(resource.id, **project)
                    break

        # cache the project id
        if domain.name not in project_cache:
            project_cache[domain.name] = {}
        project_cache[domain.name][resource.name] = resource.id

        # seed the projects endpoints
        if endpoints:
            seed_project_endpoints(resource, endpoints, keystone)

        # add the projects role assignments to the list to be resolved later on
        if roles:
            for role in roles:
                assignment = dict()
                assignment['role'] = role['role']
                assignment['project'] = '%s@%s' % (
                    project['name'], domain.name)
                if 'user' in role:
                    if '@' in role['user']:
                        assignment['user'] = role['user']
                    else:
                        assignment['user'] = '%s@%s' % (
                            role['user'], domain.name)
                elif 'group' in role:
                    if '@' in role['group']:
                        assignment['group'] = role['group']
                    else:
                        assignment['group'] = '%s@%s' % (
                            role['group'], domain.name)
                if 'inherited' in role:
                    assignment['inherited'] = role['inherited']
                role_assignments.append(assignment)

        # seed the projects network quota
        if network_quota:
            seed_project_network_quota(resource, network_quota, args,
                                       sess)

        # seed the projects network address scopes
        if address_scopes:
            seed_project_address_scopes(resource, address_scopes, args,
                                        sess)

        # seed the projects network subnet-pools
        if subnet_pools:
            seed_project_subnet_pools(resource, subnet_pools, args,
                                      sess)

        # seed the projects networks
        if networks:
            seed_project_networks(resource, networks, args, sess)

        # seed the projects routers
        if routers:
            seed_project_routers(resource, routers, args, sess)

        # seed swift account
        if swift:
            seed_swift(resource, swift, args, sess)

        # seed designate quota
        if dns_quota:
            seed_project_designate_quota(resource, dns_quota, args)

        # seed designate zone
        if dns_zones:
            seed_project_dns_zones(resource, dns_zones, args)

        # seed designate tsig keys
        if dns_tsig_keys:
            seed_project_tsig_keys(resource, dns_tsig_keys, args)

        # seed flavors
        if flavors:
            seed_project_flavors(resource, flavors, args, sess)


def seed_project_flavors(project, flavors, args, sess):
    """
    seed a projects compute flavors
    """

    logging.debug("seeding flavors of project %s" % project.name)

    # grab a nova client
    nova = novaclient.Client("2.1", session=sess,
                             endpoint_type=args.interface + 'URL')
    for flavorid in flavors:
        try:
            # validate flavor-id
            nova.flavors.get(flavorid)
            # check if project has access
            access = set([a.tenant_id for a in
                          nova.flavor_access.list(flavor=flavorid)])
            if project.id not in access:
                # add it
                logging.info(
                    "adding flavor '%s' access to project '%s" % (
                    flavorid, project.name))
                nova.flavor_access.add_tenant_access(flavorid,
                                                     project.id)
        except Exception as e:
            logging.error(
                "could not add flavor-id '%s' access for project '%s': %s" % (
                flavorid, project.name, e))
            raise


def seed_project_network_quota(project, quota, args, sess):
    """
    seed a projects network quota
    """

    logging.debug("seeding network-quota of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    quota = sanitize(quota, (
        'floatingip', 'healthmonitor', 'l7policy', 'listener',
        'loadbalancer',
        'network', 'pool', 'port', 'rbac_policy', 'router',
        'security_group',
        'security_group_rule', 'subnet', 'subnetpool'))

    body = {'quota': quota.copy()}
    result = neutron.show_quota(project.id)
    if not result or not result['quota']:
        logging.info(
            "set project %s network quota to '%s'" % (
            project.name, quota))
        neutron.update_quota(project.id, body)
    else:
        resource = result['quota']
        new_quota = {}
        for attr in quota.keys():
            if int(quota[attr]) > int(resource.get(attr, '')):
                logging.info(
                    "%s differs. set project %s network quota to '%s'" % (
                        attr, project.name, quota))
                new_quota[attr] = quota[attr]
        if len(new_quota):
            neutron.update_quota(project.id, {'quota': new_quota})


def seed_project_address_scopes(project, address_scopes, args, sess):
    """
    seed a projects neutron address scopes and dependent objects
    :param project: 
    :param address_scopes: 
    :param args: 
    :param sess: 
    :return: 
    """

    logging.debug("seeding address-scopes of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for scope in address_scopes:
        try:
            subnet_pools = None
            if 'subnet_pools' in scope:
                subnet_pools = scope.pop('subnet_pools', None)

            scope = sanitize(scope, ('name', 'ip_version', 'shared'))

            if 'name' not in scope or not scope['name']:
                logging.warn(
                    "skipping address-scope '%s/%s', since it is misconfigured" % (
                        project.name, scope))
                continue

            body = {'address_scope': scope.copy()}
            body['address_scope']['tenant_id'] = project.id
            query = {'tenant_id': project.id, 'name': scope['name']}
            result = neutron.list_address_scopes(retrieve_all=True,
                                                 **query)
            if not result or not result['address_scopes']:
                logging.info(
                    "create address-scope '%s/%s'" % (
                        project.name, scope['name']))
                result = neutron.create_address_scope(body)
                resource = result['address_scope']
            else:
                resource = result['address_scopes'][0]
                for attr in scope.keys():
                    if scope[attr] != resource.get(attr, ''):
                        logging.info(
                            "%s differs. update address-cope'%s/%s'" % (
                                attr, project.name, scope['name']))
                        # drop read-only attributes
                        body['address_scope'].pop('tenant_id', None)
                        body['address_scope'].pop('ip_version', None)
                        neutron.update_address_scope(resource['id'],
                                                     body)
                        break

            if subnet_pools:
                kvargs = {'address_scope_id': resource['id']}
                seed_project_subnet_pools(project, subnet_pools, args,
                                          sess,
                                          **kvargs)
        except Exception as e:
            logging.error("could not seed address scope %s/%s: %s" % (
                project.name, scope['name'], e))
            raise


def seed_project_subnet_pools(project, subnet_pools, args, sess,
                              **kvargs):
    logging.debug(
        "seeding subnet-pools of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for subnet_pool in subnet_pools:
        try:
            subnet_pool = sanitize(subnet_pool, (
                'name', 'default_quota', 'prefixes', 'min_prefixlen',
                'shared',
                'default_prefixlen', 'max_prefixlen', 'description',
                'address_scope_id', 'is_default'))

            if 'name' not in subnet_pool or not subnet_pool['name']:
                logging.warn(
                    "skipping subnet-pool '%s/%s', since it is misconfigured" % (
                        project.name, subnet_pool))
                continue

            if kvargs:
                subnet_pool = dict(subnet_pool.items() + kvargs.items())

            body = {'subnetpool': subnet_pool.copy()}
            body['subnetpool']['tenant_id'] = project.id

            query = {'tenant_id': project.id,
                     'name': subnet_pool['name']}
            result = neutron.list_subnetpools(retrieve_all=True,
                                              **query)
            if not result or not result['subnetpools']:
                logging.info(
                    "create subnet-pool '%s/%s'" % (
                        project.name, subnet_pool['name']))
                result = neutron.create_subnetpool(body)
                # cache the subnetpool-id
                if project.id not in subnetpool_cache:
                    subnetpool_cache[project.id] = {}
                subnetpool_cache[project.id][subnet_pool['name']] = \
                    result['subnetpool']['id']
            else:
                resource = result['subnetpools'][0]
                # cache the subnetpool-id
                if project.id not in subnetpool_cache:
                    subnetpool_cache[project.id] = {}
                subnetpool_cache[project.id][subnet_pool['name']] = \
                resource[
                    'id']

                for attr in subnet_pool.keys():
                    if attr == 'prefixes':
                        for prefix in subnet_pool['prefixes']:
                            if prefix not in resource.get('prefixes',
                                                          []):
                                logging.info(
                                    "update subnet-pool prefixes '%s/%s'" % (
                                        project.name,
                                        subnet_pool['name']))
                                # drop read-only attributes
                                body['subnetpool'].pop('tenant_id',
                                                       None)
                                body['subnetpool'].pop('shared', None)
                                neutron.update_subnetpool(
                                    resource['id'], body)
                                break
                    else:
                        # a hacky comparison due to the neutron api not dealing with string/int attributes consistently
                        if str(subnet_pool[attr]) != str(
                                resource.get(attr, '')):
                            logging.info(
                                "%s differs. update subnet-pool'%s/%s'" % (
                                    attr, project.name,
                                    subnet_pool['name']))
                            # drop read-only attributes
                            body['subnetpool'].pop('tenant_id', None)
                            body['subnetpool'].pop('shared', None)
                            neutron.update_subnetpool(resource['id'],
                                                      body)
                            break
        except Exception as e:
            logging.error("could not seed subnet pool %s/%s: %s" % (
                project.name, subnet_pool['name'], e))
            raise


def seed_project_networks(project, networks, args, sess):
    """
    seed a projects neutron networks and dependent objects
    :param project:
    :param networks:
    :param args:
    :param sess:
    :return:
    """

    # network attribute name mappings
    rename = {'router_external': 'router:external',
              'provider_network_type': 'provider:network_type',
              'provider_physical_network': 'provider:physical_network',
              'provider_segmentation_id': 'provider:segmentation_id'}

    logging.debug("seeding networks of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for network in networks:
        try:
            subnets = network.pop('subnets', None)

            tags = network.pop('tags', None)

            # rename some yaml unfriendly network attributes
            for key, value in rename.items():
                if key in network:
                    network[value] = network.pop(key)

            network = sanitize(network, (
                'name', 'admin_state_up', 'port_security_enabled',
                'provider:network_type', 'provider:physical_network',
                'provider:segmentation_id', 'qos_policy_id',
                'router:external',
                'shared', 'vlan_transparent', 'description'))

            if 'name' not in network or not network['name']:
                logging.warn(
                    "skipping network '%s/%s', since it is misconfigured" % (
                        project.name, network))
                continue

            body = {'network': network.copy()}
            body['network']['tenant_id'] = project.id
            query = {'tenant_id': project.id, 'name': network['name']}
            result = neutron.list_networks(retrieve_all=True, **query)
            if not result or not result['networks']:
                logging.info(
                    "create network '%s/%s'" % (
                    project.name, network['name']))
                result = neutron.create_network(body)
                resource = result['network']
            else:
                resource = result['networks'][0]
                for attr in network.keys():
                    if network[attr] != resource.get(attr, ''):
                        logging.info(
                            "%s differs. update network'%s/%s'" % (
                                attr, project.name, network['name']))
                        # drop read-only attributes
                        body['network'].pop('tenant_id', None)
                        neutron.update_network(resource['id'], body)
                        break

            if tags:
                seed_network_tags(resource, tags, args, sess)

            if subnets:
                seed_network_subnets(resource, subnets, args, sess)
        except Exception as e:
            logging.error("could not seed network %s/%s: %s" % (
                project.name, network['name'], e))
            raise


def seed_project_routers(project, routers, args, sess):
    """
    seed a projects neutron routers and dependent objects
    :param project:
    :param routers:
    :param args:
    :param sess:
    :return:
    """

    def external_fixed_ip_subnets_differ(desired, actual):
        subnets = {}
        for subnet in actual:
            subnets[subnet['subnet_id']] = subnet['ip_address']

        for entry in desired:
            if 'subnet_id' in entry:
                if not entry['subnet_id'] in subnets:
                    return True

        return False

    regex = r"^([^@]+)@([^@]+)@([^@]+)$"

    logging.debug("seeding routers of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    # grab a keystone client
    keystone = keystoneclient.Client(session=sess,
                                     interface=args.interface)

    for router in routers:
        try:
            interfaces = None
            if 'interfaces' in router:
                interfaces = router.pop('interfaces', None)

            router = sanitize(router, (
                'name', 'admin_state_up', 'description',
                'external_gateway_info', 'distributed', 'ha',
                'availability_zone_hints', 'flavor_id',
                'service_type_id', 'routes'))

            if 'name' not in router or not router['name']:
                logging.warn(
                    "skipping router '%s %s', since it is misconfigured" % (
                        project.name, router))
                continue

            if 'external_gateway_info' in router:
                # lookup network-id
                if 'network' in router['external_gateway_info']:
                    network_id = None

                    # network@project@domain ?
                    match = re.match(regex,
                                     router['external_gateway_info'][
                                         'network'])
                    if match:
                        project_id = get_project_id(match.group(3),
                                                    match.group(2),
                                                    keystone)
                        if project_id:
                            network_id = get_network_id(project_id,
                                                        match.group(1),
                                                        neutron)
                    else:
                        # network of this project
                        network_id = get_network_id(project.id, router[
                            'external_gateway_info']['network'],
                                                    neutron)
                    if not network_id:
                        logging.warn(
                            "skipping router '%s/%s': external_gateway_info.network %s not found" % (
                                project.name, router['name'],
                                router['external_gateway_info'][
                                    'network']))
                        continue
                    router['external_gateway_info'][
                        'network_id'] = network_id
                    router['external_gateway_info'].pop('network', None)

                if 'external_fixed_ips' in router[
                    'external_gateway_info']:
                    for index, efi in enumerate(
                            router['external_gateway_info'][
                                'external_fixed_ips']):
                        if 'subnet' in efi:
                            subnet_id = None

                            # subnet@project@domain ?
                            match = re.match(regex, efi['subnet'])
                            if match:
                                project_id = get_project_id(
                                    match.group(3), match.group(2),
                                    keystone)
                                if project_id:
                                    subnet_id = get_subnet_id(
                                        project_id, match.group(1),
                                        neutron)
                            else:
                                # subnet of this project
                                subnet_id = get_subnet_id(project.id,
                                                          efi['subnet'],
                                                          neutron)
                            if not subnet_id:
                                logging.warn(
                                    "skipping router '%s/%s': external_gateway_info.external_fixed_ips.subnet %s not found" % (
                                        project.name, router['name'],
                                        efi['subnet']))
                                continue
                            efi['subnet_id'] = subnet_id
                            efi.pop('subnet', None)
                        router['external_gateway_info'][
                            'external_fixed_ips'][index] = sanitize(efi,
                                                                    (
                                                                    'subnet_id',
                                                                    'ip_address'))

            router['external_gateway_info'] = sanitize(
                router['external_gateway_info'],
                ('network_id', 'enable_snat', 'external_fixed_ips'))

            body = {'router': router.copy()}
            body['router']['tenant_id'] = project.id
            query = {'tenant_id': project.id, 'name': router['name']}
            result = neutron.list_routers(retrieve_all=True, **query)
            if not result or not result['routers']:
                logging.info(
                    "create router '%s/%s': %s" % (
                    project.name, router['name'], body))
                result = neutron.create_router(body)
                resource = result['router']
            else:
                resource = result['routers'][0]
                update = False
                for attr in router.keys():
                    if attr == 'external_gateway_info':
                        if 'network_id' in router[attr] and resource.get(attr, ''):
                            if router[attr]['network_id'] != resource[attr]['network_id']:
                                update = True

                        if ('external_fixed_ips' in router[
                            'external_gateway_info'] and
                            external_fixed_ip_subnets_differ(
                            router['external_gateway_info'][
                                'external_fixed_ips'],
                            resource['external_gateway_info'][
                                'external_fixed_ips'])):
                                update = True
                    elif router[attr] != resource.get(attr, ''):
                        update = True


                if update:
                    logging.info("update router '%s/%s': %s" % (
                    project.name, router['name'], body))
                    # drop read-only attributes
                    body['router'].pop('tenant_id', None)
                    result = neutron.update_router(resource['id'], body)
                    resource = result['router']

            if interfaces:
                seed_router_interfaces(resource, interfaces, args, sess)
        except Exception as e:
            logging.error("could not seed router %s/%s: %s" % (
                project.name, router['name'], e))
            raise


def seed_router_interfaces(router, interfaces, args, sess):
    """
    seed a routers interfaces (routes)
    :param router:
    :param interfaces:
    :param args:
    :param sess:
    :return:
    """

    logging.debug("seeding interfaces of router %s" % router['name'])

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    # grab a keystone client
    keystone = keystoneclient.Client(session=sess,
                                     interface=args.interface)

    for interface in interfaces:
        if 'subnet' in interface:
            subnet_id = None
            # subnet@project@domain ?
            if '@' in interface['subnet']:
                parts = interface['subnet'].split('@')
                if len(parts) > 2:
                    project_id = get_project_id(parts[2], parts[1],
                                                keystone)
                    if project_id:
                        subnet_id = get_subnet_id(project_id, parts[0],
                                                  neutron)
            else:
                # lookup subnet-id
                subnet_id = get_subnet_id(router['tenant_id'],
                                          interface['subnet'], neutron)

            if subnet_id:
                interface['subnet_id'] = subnet_id

        interface = sanitize(interface, ('subnet_id', 'port_id'))

        if 'subnet_id' not in interface and 'port_id' not in interface:
            logging.warn(
                "skipping router interface '%s/%s', since it is misconfigured" % (
                    router['name'], interface))
            continue

        # check if the interface is already configured for the router
        query = {'device_id': router['id']}
        result = neutron.list_ports(retrieve_all=True, **query)
        found = False
        for port in result['ports']:
            if 'port_id' in interface and port['id'] == interface[
                'port_id']:
                found = True
                break
            elif 'subnet_id' in interface:
                for ip in port['fixed_ips']:
                    if 'subnet_id' in ip and ip['subnet_id'] == \
                            interface['subnet_id']:
                        found = True
                        break
            if found:
                break

        if found:
            continue

        # add router interface
        neutron.add_interface_router(router['id'], interface)
        logging.info("added interface %s to router'%s'" % (
        interface, router['name']))


def seed_network_tags(network, tags, args, sess):
    """
    seed neutron tags of a network
    :param network:
    :param tags:
    :param args:
    :param sess:
    :return:
    """

    logging.debug("seeding tags of network %s" % network['name'])

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for tag in tags:
        if not tag or len(tag) > 60:
            logging.warn(
                "skipping tag '%s/%s', since it is invalid" % (
                    network['name'], tag))
            continue

        if tag not in network['tags']:
            logging.info(
                "adding tag %s to network '%s'" % (
                tag, network['name']))
            neutron.add_tag('networks', network['id'], tag)


def seed_network_subnets(network, subnets, args, sess):
    """
    seed neutron subnets of a network
    :param network:
    :param subnets:
    :param args:
    :param sess:
    :return:
    """

    logging.debug("seeding subnets of network %s" % network['name'])

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for subnet in subnets:
        # lookup subnetpool-id
        if 'subnetpool' in subnet:
            subnet['subnetpool_id'] = get_subnetpool_id(
                network['tenant_id'],
                subnet['subnetpool'],
                neutron)
            if not subnet['subnetpool_id']:
                logging.warn(
                    "skipping subnet '%s/%s', since its subnetpool is invalid" % (
                        network['name'], subnet))
                continue
            subnet.pop('subnetpool', None)

        subnet = sanitize(subnet, (
            'name', 'enable_dhcp', 'dns_nameservers',
            'allocation_pools', 'host_routes', 'ip_version',
            'gateway_ip', 'cidr', 'prefixlen', 'subnetpool_id',
            'description'))

        if 'name' not in subnet or not subnet['name']:
            logging.warn(
                "skipping subnet '%s/%s', since it is misconfigured" % (
                    network['name'], subnet))
            continue

        if 'gateway_ip' in subnet and subnet['gateway_ip'] == 'null':
            subnet['gateway_ip'] = None

        body = {'subnet': subnet.copy()}
        body['subnet']['network_id'] = network['id']
        body['subnet']['tenant_id'] = network['tenant_id']

        query = {'network_id': network['id'], 'name': subnet['name']}
        result = neutron.list_subnets(retrieve_all=True, **query)
        if not result or not result['subnets']:
            logging.info(
                "create subnet '%s/%s'" % (
                network['name'], subnet['name']))
            neutron.create_subnet(body)
        else:
            resource = result['subnets'][0]
            for attr in subnet.keys():
                if subnet[attr] != resource.get(attr, ''):
                    logging.info(
                        "%s differs. update subnet'%s/%s'" % (
                            attr, network['name'], subnet['name']))
                    # drop read-only attributes
                    body['subnet'].pop('cidr', None)
                    body['subnet'].pop('segment_id', None)
                    body['subnet'].pop('tenant_id', None)
                    body['subnet'].pop('network_id', None)
                    body['subnet'].pop('subnetpool_id', None)
                    body['subnet'].pop('ip_version', None)
                    body['subnet'].pop('prefixlen', None)
                    neutron.update_subnet(resource['id'], body)
                    break


def seed_swift(project, swift, args, sess):
    """
    Seeds swift account and containers for a project
    :param project:
    :param swift:
    :param args:
    :param sess:
    :return:
    """

    if 'enabled' in swift and swift['enabled']:
        logging.debug(
            "seeding swift account for project %s" % project.name)

        try:
            service_token = sess.get_token()

            # poor mans storage-url generation
            try:
                swift_endpoint = sess.get_endpoint(
                    service_type='object-store',
                    interface=args.interface)
            except exceptions.EndpointNotFound:
                swift_endpoint = sess.get_endpoint(
                    service_type='object-store',
                    interface='admin')

            storage_url = swift_endpoint.split('/AUTH_')[
                              0] + '/AUTH_' + project.id

            # Create swiftclient Connection
            conn = swiftclient.Connection(session=sess,
                                          preauthurl=storage_url,
                                          preauthtoken=service_token,
                                          insecure=True)
            try:
                # see if the account already exists
                conn.head_account()
            except swiftclient.ClientException:
                # nope, go create it
                logging.info(
                    'creating swift account for project %s' % project.name)
                swiftclient.put_object(storage_url, token=service_token)

            # seed swift containers
            if 'containers' in swift:
                seed_swift_containers(project, swift['containers'],
                                      conn)

        except Exception as e:
            logging.error(
                "could not seed swift account for project %s: %s" % (
                    project.name, e))
            raise


def seed_swift_containers(project, containers, conn):
    """
    Creates swift containers for a project
    :param project:
    :param containers:
    :param conn:
    :return:
    """

    logging.debug(
        "seeding swift containers for project %s" % project.name)

    for container in containers:
        try:
            # prepare the container metadata
            headers = {}
            if 'metadata' in container:
                for meta in container['metadata'].keys():
                    header = 'x-container-%s' % meta
                    headers[header] = str(container['metadata'][meta])
            try:
                # see if the container already exists
                result = conn.head_container(container['name'])
                for header in headers.keys():
                    if headers[header] != result.get(header, ''):
                        logging.info(
                            "%s differs. update container %s/%s" % (
                                header, project.name,
                                container['name']))
                        conn.post_container(container['name'], headers)
                        break
            except swiftclient.ClientException:
                # nope, go create it
                logging.info(
                    'creating swift container %s/%s' % (
                        project.name, container['name']))
                conn.put_container(container['name'], headers)
        except Exception as e:
            logging.error(
                "could not seed swift container for project %s: %s" % (
                    project.name, e))
            raise


def seed_project_designate_quota(project, config, args):
    """
    Seeds designate quota for a project
    :param project:
    :param config:
    :param args:
    :return:
    """

    # seed designate quota
    logging.debug(
        "seeding designate quota for project %s" % project.name)

    try:
        # the designate client needs a token scoped to a project.id
        # due to a crappy bugfix in https://review.openstack.org/#/c/187570/
        designate_args = copy.copy(args)
        designate_args.os_project_id = project.id
        designate_args.os_domain_id = None
        designate_args.os_domain_name = None
        plugin = cli.load_from_argparse_arguments(designate_args)
        sess = session.Session(auth=plugin,
                               user_agent='openstack-seeder',
                               verify=not args.insecure)

        designate = designateclient.Client(session=sess,
                                           endpoint_type=args.interface + 'URL',
                                           all_projects=True)

        result = designate.quotas.list(project.id)
        new_quota = {}
        for attr in config.keys():
            if int(config[attr]) > int(result.get(attr, '')):
                logging.info(
                    "%s differs. set project %s designate quota to '%s'" % (
                        attr, project.name, config))
                new_quota[attr] = config[attr]
        if len(new_quota):
            designate.quotas.update(project.id, new_quota)

    except Exception as e:
        logging.error(
            "could not seed designate quota for project %s: %s" % (
                project.name, e))
        raise


def seed_project_dns_zones(project, zones, args):
    """
    Seed a projects designate zones and dependent objects
    :param project:
    :param zones:
    :param args:
    :return:
    """

    logging.debug("seeding dns zones of project %s" % project.name)

    try:
        # the designate client needs a token scoped to a project.id,
        # due to a crappy bugfix in https://review.openstack.org/#/c/187570/
        designate_args = copy.copy(args)
        designate_args.os_project_id = project.id
        designate_args.os_domain_id = None
        designate_args.os_domain_name = None
        plugin = cli.load_from_argparse_arguments(designate_args)
        sess = session.Session(auth=plugin,
                               user_agent='openstack-seeder',
                               verify=not args.insecure)

        designate = designateclient.Client(session=sess,
                                           endpoint_type=args.interface + 'URL',
                                           all_projects=True)

        for zone in zones:
            recordsets = zone.pop('recordsets', None)

            zone = sanitize(zone, (
                'name', 'email', 'ttl', 'description', 'masters',
                'type'))

            if 'name' not in zone or not zone['name']:
                logging.warn(
                    "skipping dns zone '%s/%s', since it is misconfigured" % (
                        project.name, zone))
                continue

            try:
                resource = designate.zones.get(zone['name'])
                for attr in zone.keys():
                    if zone[attr] != resource.get(attr, ''):
                        logging.info(
                            "%s differs. update dns zone'%s/%s'" % (
                                attr, project.name, zone['name']))
                        designate.zones.update(resource['id'], zone)
                        break
            except designateclient.exceptions.NotFound:
                logging.info(
                    "create dns zone '%s/%s'" % (
                        project.name, zone['name']))
                # wtf
                if 'type' in zone:
                    zone['type_'] = zone.pop('type')
                resource = designate.zones.create(zone.pop('name'),
                                                  **zone)

            if recordsets:
                seed_dns_zone_recordsets(resource, recordsets,
                                         designate)

    except Exception as e:
        logging.error("could not seed project dns zones %s: %s" % (
            project.name, e))
        raise


def seed_dns_zone_recordsets(zone, recordsets, designate):
    """
    seed a designate zones recordsets
    :param zone:
    :param recordsets:
    :param designate:
    :return:
    """

    logging.debug("seeding recordsets of dns zones %s" % zone['name'])

    for recordset in recordsets:
        try:
            # records = recordset.pop('records', None)

            recordset = sanitize(recordset, (
                'name', 'ttl', 'description', 'type', 'records'))

            if 'name' not in recordset or not recordset['name']:
                logging.warn(
                    "skipping recordset %s of dns zone %s, since it is misconfigured" % (
                        recordset, zone['name']))
                continue
            if 'type' not in recordset or not recordset['type']:
                logging.warn(
                    "skipping recordset %s of dns zone %s, since it is misconfigured" % (
                        recordset, zone['name']))
                continue

            query = {'name': recordset['name'],
                     'type': recordset['type']}
            result = designate.recordsets.list(zone['id'],
                                               criterion=query)
            if not result:
                logging.info(
                    "create dns zones %s recordset %s" % (
                        zone['name'], recordset['name']))
                designate.recordsets.create(zone['id'],
                                            recordset['name'],
                                            recordset['type'],
                                            recordset['records'],
                                            description=recordset.get(
                                                'description'),
                                            ttl=recordset.get('ttl'))
            else:
                resource = result[0]
                for attr in recordset.keys():
                    if attr == 'records':
                        for record in recordset['records']:
                            if record not in resource.get('records',
                                                          []):
                                logging.info(
                                    "update dns zone %s recordset %s record %s" % (
                                        zone['name'], recordset['name'],
                                        record))
                                designate.recordsets.update(zone['id'],
                                                            resource[
                                                                'id'],
                                                            recordset)
                                break
                    elif recordset[attr] != resource.get(attr, ''):
                        logging.info(
                            "%s differs. update dns zone'%s recordset %s'" % (
                                attr, zone['name'], recordset['name']))
                        designate.recordsets.update(zone['id'],
                                                    resource['id'],
                                                    recordset)
                        break

        except Exception as e:
            logging.error(
                "could not seed dns zone %s recordsets: %s" % (
                    zone['name'], e))
            raise


def seed_project_tsig_keys(project, keys, args):
    """
    Seed a projects designate tsig keys
    :param project:
    :param keys:
    :param args:
    :return:
    """

    logging.debug("seeding dns tsig keys of project %s" % project.name)

    try:
        # the designate client needs a token scoped to a project.id,
        # due to a crappy bugfix in https://review.openstack.org/#/c/187570/
        designate_args = copy.copy(args)
        designate_args.os_project_id = project.id
        designate_args.os_domain_id = None
        designate_args.os_domain_name = None
        plugin = cli.load_from_argparse_arguments(designate_args)
        sess = session.Session(auth=plugin,
                               user_agent='openstack-seeder',
                               verify=not args.insecure)
        designate = designateclient.Client(session=sess,
                                           endpoint_type=args.interface + 'URL',
                                           all_projects=True)

        for key in keys:
            key = sanitize(key, (
                'name', 'algorithm', 'secret', 'scope', 'resource_id'))

            if 'name' not in key or not key['name']:
                logging.warn(
                    "skipping dns tsig key '%s/%s', since it is misconfigured" % (
                        project.name, key))
                continue
            try:
                resource = designate.tsigkeys.get(key['name'])
                for attr in key.keys():
                    if key[attr] != resource.get(attr, ''):
                        logging.info(
                            "%s differs. update dns tsig key '%s/%s'" % (
                                attr, project.name, key['name']))
                        designate.tsigkeys.update(resource['id'], key)
                        break
            except designateclient.exceptions.NotFound:
                logging.info(
                    "create dns tsig key '%s/%s'" % (
                        project.name, key['name']))
                designate.tsigkeys.create(key.pop('name'), **key)

    except Exception as e:
        logging.error("could not seed project dns tsig keys %s: %s" % (
            project.name, e))
        raise


def domain_config_equal(new, current):
    """
    compares domain configurations (and ignores passwords in the comparison)
    :param new:
    :param current:
    :return:
    """
    for key, value in new.items():
        if key in current:
            if isinstance(value, dict):
                if not domain_config_equal(value, current[key]):
                    return False
            elif new[key] != current[key]:
                return False
        elif 'password' in key:
            continue  # ignore, since it is supressed during config get
        else:
            return False
    return True


def seed_domain_config(domain, driver, keystone):
    logging.debug(
        "seeding domain config %s %s" % (domain.name, redact(driver)))

    # get the current domain configuration
    try:
        result = keystone.domain_configs.get(domain)
        if not domain_config_equal(driver, result.to_dict()):
            logging.info('updating domain config %s' % domain.name)
            keystone.domain_configs.update(domain, driver)
    except exceptions.NotFound:
        logging.info('creating domain config %s' % domain.name)
        keystone.domain_configs.create(domain, driver)
    except Exception as e:
        logging.error(
            'could not configure domain %s: %s' % (domain.name, e))


def seed_domain(domain, args, sess):
    logging.debug("seeding domain %s" % domain)

    # grab a keystone client
    keystone = keystoneclient.Client(session=sess,
                                     interface=args.interface)

    users = None
    if 'users' in domain:
        users = domain.pop('users', None)
    groups = None
    if 'groups' in domain:
        groups = domain.pop('groups', None)
    projects = None
    if 'projects' in domain:
        projects = domain.pop('projects', None)
    driver = None
    if 'config' in domain:
        driver = domain.pop('config', None)
    roles = None
    if 'roles' in domain:
        roles = domain.pop('roles', None)

    domain = sanitize(domain, ('name', 'description', 'enabled'))

    if 'name' not in domain or not domain['name']:
        logging.warn(
            "skipping domain '%s', since it is misconfigured" % domain)
        return

    result = keystone.domains.list(name=domain['name'])
    if not result:
        logging.info("create domain '%s'" % domain['name'])
        resource = keystone.domains.create(**domain)
    else:
        resource = result[0]
        for attr in domain.keys():
            if domain[attr] != resource._info.get(attr, ''):
                logging.info(
                    "%s differs. update domain '%s'" % (
                    attr, domain['name']))
                keystone.domains.update(resource.id, **domain)
                break

    # cache the domain id
    if resource.name not in domain_cache:
        domain_cache[resource.name] = resource.id

    if driver:
        seed_domain_config(resource, driver, keystone)
    if projects:
        seed_projects(resource, projects, args, sess)
    if users:
        seed_users(resource, users, keystone)
    if groups:
        seed_groups(resource, groups, keystone)
    if roles:
        for role in roles:
            assignment = dict()
            assignment['role'] = role['role']
            assignment['domain'] = domain['name']
            if 'user' in role:
                if '@' in role['user']:
                    assignment['user'] = role['user']
                else:
                    assignment['user'] = '%s@%s' % (
                        role['user'], domain['name'])
            elif 'group' in role:
                if '@' in role['group']:
                    assignment['group'] = role['group']
                else:
                    assignment['group'] = '%s@%s' % (
                        role['group'], domain['name'])
            if 'inherited' in role:
                assignment['inherited'] = role['inherited']
            role_assignments.append(assignment)

def seed_resource_class(resource_class, args, sess):
    logging.debug("seeding resource-class %s" % resource_class)

    try:
        ks_filter = {
            'service_type': 'placement',
            'interface': args.interface,
        }

        # api_version=1.7 -> idempotent resource class creation
        http = placementclient(session=sess, ks_filter=ks_filter, api_version='1.7')
        logging.debug(resource_class)
        http.request('PUT', PER_CLASS_URL.format(name=resource_class))
    except Exception as e:
        logging.error("Failed to seed resource-class %s: %s" % (resource_class, e))


def seed_flavor(flavor, args, sess):
    logging.debug("seeding flavor %s" % flavor)

    try:
        nova = novaclient.Client("2.1", session=sess,
                                 endpoint_type=args.interface + 'URL')

        extra_specs = None
        if 'extra_specs' in flavor:
            extra_specs = flavor.pop('extra_specs', None)
            if not isinstance(extra_specs, dict):
                logging.warn(
                    "skipping flavor '%s', since it has invalid extra_specs" % flavor)

        flavor = sanitize(flavor, (
            'id', 'name', 'ram', 'disk', 'vcpus', 'swap', 'rxtx_factor',
            'is_public', 'disabled', 'ephemeral'))
        if 'name' not in flavor or not flavor['name']:
            logging.warn(
                "skipping flavor '%s', since it has no name" % flavor)
            return
        if 'id' not in flavor or not flavor['id']:
            logging.warn(
                "skipping flavor '%s', since its id is missing" % flavor)
            return

        # wtf, flavors has no update(): needs to be dropped and re-created instead
        create = False
        resource = None
        try:
            resource = nova.flavors.get(flavor['id'])

            # 'rename' some attributes, since api and internal representation differ
            flavor_cmp = flavor.copy()
            if 'is_public' in flavor_cmp:
                flavor_cmp[
                    'os-flavor-access:is_public'] = flavor_cmp.pop(
                    'is_public')
            if 'disabled' in flavor_cmp:
                flavor_cmp['OS-FLV-DISABLED:disabled'] = flavor_cmp.pop(
                    'disabled')
            if 'ephemeral' in flavor_cmp:
                flavor_cmp[
                    'OS-FLV-EXT-DATA:ephemeral'] = flavor_cmp.pop(
                    'ephemeral')

            # check for delta
            for attr in flavor_cmp.keys():
                if flavor_cmp[attr] != getattr(resource, attr):
                    logging.info(
                        "deleting flavor '%s' to re-create, since '%s' differs" %
                        (flavor['name'], attr))
                    resource.delete()
                    create = True
                break
        except novaexceptions.NotFound:
            create = True

        # (re-) create the flavor
        if create:
            logging.info("creating flavor '%s'" % flavor['name'])
            flavor['flavorid'] = flavor.pop('id')
            resource = nova.flavors.create(**flavor)

        # take care of the flavors extra specs
        if extra_specs and resource:
            set_extra_specs = False
            try:
                keys = resource.get_keys()
                for k, v in extra_specs.iteritems():
                    if v != keys.get(k, ''):
                        keys[k] = v
                        set_extra_specs = True
            except novaexceptions.NotFound:
                set_extra_specs = True
                keys = extra_specs

            if set_extra_specs:
                logging.info(
                    "updating extra-specs '%s' of flavor '%s'" % (
                    keys, flavor['name']))
                resource.set_keys(keys)
    except Exception as e:
        logging.error("Failed to seed flavor %s: %s" % (flavor, e))
        raise


def resolve_group_members(keystone):
    for group, users in group_members.iteritems():
        logging.debug("resolving group members %s %s" % (group, users))
        for uid in users:
            username, domain = uid.split('@')
            user = get_user_id(domain, username, keystone)

            if user:
                try:
                    keystone.users.check_in_group(user, group)
                except exceptions.NotFound:
                    logging.info(
                        "add user '%s' to group '%s'" % (uid, group))
                    keystone.users.add_to_group(user, group)
            else:
                logging.warn(
                    "could not add user '%s' to group '%s'" % (
                    uid, group))


def resolve_role_assignments(keystone):
    for assignment in role_assignments:
        logging.debug("resolving role assignment %s" % assignment)

        try:
            role_assignment = dict()
            role = assignment.pop('role')
            role_id = get_role_id(role, keystone)
            if 'user' in assignment:
                user, domain = assignment['user'].split('@')
                id = get_user_id(domain, user, keystone)
                if not id:
                    logging.warn(
                        "user %s not found, skipping role assignment.." %
                        assignment['user'])
                    continue
                role_assignment['user'] = id
            elif 'group' in assignment:
                group, domain = assignment['group'].split('@')
                id = get_group_id(domain, group, keystone)
                if not id:
                    logging.warn(
                        "group %s not found, skipping role assignment.." %
                        assignment['group'])
                    continue
                role_assignment['group'] = id
            if 'domain' in assignment:
                id = get_domain_id(assignment['domain'], keystone)
                if not id:
                    logging.warn(
                        "domain %s not found, skipping role assignment.." %
                        assignment['domain'])
                    continue
                role_assignment['domain'] = id
            if 'project' in assignment:
                project, domain = assignment['project'].split('@')
                id = get_project_id(domain, project, keystone)
                if not id:
                    logging.warn(
                        "project %s not found, skipping role assignment.." %
                        assignment['project'])
                    continue
                role_assignment['project'] = id
            elif 'project_id' in assignment:
                role_assignment['project'] = assignment['project_id']

            if 'inherited' in assignment:
                role_assignment['os_inherit_extension_inherited'] = \
                assignment['inherited']

            try:
                keystone.roles.check(role_id, **role_assignment)
            except exceptions.NotFound:
                logging.info("grant '%s' to '%s'" % (role, assignment))
                keystone.roles.grant(role_id, **role_assignment)
        except ValueError as e:
            logging.error(
                "skipped role assignment %s since it is invalid: %s" % (
                assignment, e))


def seed_config(config, args, sess):
    global group_members, role_assignments

    # reset
    group_members = {}
    role_assignments = []

    # grab a keystone client
    keystone = keystoneclient.Client(session=sess,
                                     interface=args.interface)

    if 'roles' in config:
        for role in config['roles']:
            if role:
                seed_role(role, keystone)

    if 'regions' in config:
        # seed parent regions
        for region in config['regions']:
            if 'parent_region' not in region:
                seed_region(region, keystone)
        # seed child regions
        for region in config['regions']:
            if 'parent_region' in region:
                seed_region(region, keystone)

    if 'services' in config:
        for service in config['services']:
            seed_service(service, keystone)

    if 'resource_classes' in config:
        for resource_class in config['resource_classes']:
            seed_resource_class(resource_class, args, sess)

    if 'flavors' in config:
        for flavor in config['flavors']:
            seed_flavor(flavor, args, sess)

    if 'domains' in config:
        for domain in config['domains']:
            seed_domain(domain, args, sess)

    if group_members:
        resolve_group_members(keystone)

    if role_assignments:
        resolve_role_assignments(keystone)


def seed(args):
    try:
        if args.input:
            # get seed content from file
            with open(args.input, 'r') as f:
                config = yaml.load(f)
        else:
            # get seed content from stdin
            seed_content = sys.stdin.read()
            config = yaml.load(seed_content)
    except Exception as e:
        logging.error("could not parse seed input: %s" % e)
        return 1

    try:
        logging.info("seeding openstack with '%s'" % redact(config))

        if not args.dry_run:
            plugin = cli.load_from_argparse_arguments(args)
            sess = session.Session(auth=plugin,
                                   user_agent='openstack-seeder',
                                   verify=not args.insecure)
            seed_config(config, args, sess)
        return 0
    except Exception as e:
        logging.error("seed failed: %s" % e)
        return 1


def main():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    parser = argparse.ArgumentParser()
    parser.add_argument('--input',
                        help='the yaml file with the identity configuration')
    parser.add_argument('--interface',
                        help='the keystone interface-type to use',
                        default='internal',
                        choices=['admin', 'public', 'internal'])
    parser.add_argument('--insecure',
                        help='do not verify SSL certificates',
                        default=False,
                        action='store_true')
    parser.add_argument("-l", "--log", dest="logLevel",
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                 'CRITICAL'],
                        help="Set the logging level",
                        default='INFO')
    parser.add_argument('--dry-run', default=False, action='store_true',
                        help='Only parse the seed, do no actual seeding.')
    cli.register_argparse_arguments(parser, sys.argv[1:])
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
        datefmt='%d.%m.%Y %H:%M:%S',
        level=getattr(logging, args.logLevel))

    # setup sentry logging
    if 'SENTRY_DSN' in os.environ:
        dsn = os.environ['SENTRY_DSN']
        if 'verify_ssl' not in dsn:
            dsn = "%s?verify_ssl=0" % os.environ['SENTRY_DSN']
        client = Client(dsn=dsn, transport=RequestsHTTPTransport)
        handler = SentryHandler(client)
        handler.setLevel(logging.ERROR)
        setup_logging(handler)

    return seed(args)


if __name__ == "__main__":
    sys.exit(main())
