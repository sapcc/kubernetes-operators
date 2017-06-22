#!/usr/bin/env python
import argparse
import sys
import yaml
import logging
import traceback
import requests
from urlparse import urlparse
from urllib3.exceptions import InsecureRequestWarning

from keystoneauth1 import session
from keystoneauth1.loading import cli
from keystoneclient import exceptions
from keystoneclient.v3 import client as keystoneclient
from novaclient import client as novaclient
from neutronclient.v2_0 import client as neutronclient

# todo: subnet pools, networks

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
        users = keystone.users.list(domain=get_domain_id(domain, keystone),
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
        groups = keystone.groups.list(domain=get_domain_id(domain, keystone),
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
        query = {'project_id': project_id, 'name': name}
        result = neutron.list_subnetpools(retrieve_all=True, **query)
        if result and result['subnetpools']:
            result = subnetpool_cache[project_id][name] = result['subnetpools'][0]['id']
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
        query = {'project_id': project_id, 'name': name}
        result = neutron.list_networks(retrieve_all=True, **query)
        if result and result['networks']:
            result = network_cache[project_id][name] = result['networks'][0]['id']
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
        query = {'project_id': project_id, 'name': name}
        result = neutron.list_subnets(retrieve_all=True, **query)
        if result and result['subnets']:
            result = subnet_cache[project_id][name] = result['subnets'][0]['id']
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
                logging.info("update region '%s'" % region)
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
        result = keystone.endpoints.list(service=service.id,
                                         interface=endpoint['interface'],
                                         region_id=region)
        if not result:
            logging.info("create endpoint '%s/%s'" % \
                         (service.name, endpoint['interface']))
            keystone.endpoints.create(service.id, **endpoint)
        else:
            resource = result[0]
            for attr in endpoint.keys():
                if endpoint[attr] != resource._info.get(attr, ''):
                    logging.info("update endpoint '%s/%s'" % \
                                 (service.name, endpoint['interface']))
                    keystone.endpoints.update(resource.id, **endpoint)
                    break


def seed_service(service, keystone):
    """ seed a keystone service """
    logging.debug("seeding service %s" % service)
    endpoints = None
    if 'endpoints' in service:
        endpoints = service.pop('endpoints', None)

    service = sanitize(service, ('type', 'name', 'enabled', 'description'))
    if 'name' not in service or not service['name'] \
            or 'type' not in service or not service['type']:
        logging.warn(
            "skipping service '%s', since it is misconfigured" % service)
        return

    result = keystone.services.list(name=service['name'], type=service['type'])
    if not result:
        logging.info(
            "create service '%s/%s'" % (service['name'], service['type']))
        resource = keystone.services.create(**service)
    else:
        resource = result[0]
        for attr in service.keys():
            if service[attr] != resource._info.get(attr, ''):
                logging.info("update service '%s/%s'" % (
                    service['name'], service['type']))
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
                'default_project_id'))

            if 'name' not in user or not user['name']:
                logging.warn(
                    "skipping user '%s/%s', since it is misconfigured" % (
                        domain.name, user))
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
                            "update user '%s/%s' (%s)" % (
                                domain.name, user['name'], attr))
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
                assignment['user'] = '%s@%s' % (user['name'], domain.name)
                if 'project' in role:
                    if '@' in role['project']:
                        assignment['project'] = role['project']
                    else:
                        assignment['project'] = '%s@%s' % (
                            role['project'], domain.name)
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
            logging.info("create group '%s/%s'" % (domain.name, group['name']))
            resource = keystone.groups.create(domain=domain, **group)
        else:
            resource = result[0]
            for attr in group.keys():
                if group[attr] != resource._info.get(attr, ''):
                    logging.info(
                        "update group '%s/%s'" % (domain.name, group['name']))
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
                assignment['group'] = '%s@%s' % (group['name'], domain.name)
                if 'project' in role:
                    if '@' in role['project']:
                        assignment['project'] = role['project']
                    else:
                        assignment['project'] = '%s@%s' % (
                            role['project'], domain.name)
                elif 'domain' in role:
                    assignment['domain'] = role['domain']
                if 'inherited' in role:
                    assignment['inherited'] = role['inherited']
                role_assignments.append(assignment)


def seed_project_endpoints(project, endpoints, keystone):
    """ seed a keystone projects endpoints (OS-EP-FILTER)"""
    logging.debug("seeding project endpoint %s %s" % (project.name, endpoints))

    for name, endpoint in endpoints.iteritems():
        if 'endpoint_id' in endpoint:
            try:
                ep = keystone.endpoints.find(id=endpoint['endpoint_id'])
                try:
                    keystone.endpoint_filter.check_endpoint_in_project(project,
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
                                                 region_id=endpoint['region'])
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


def seed_projects(domain, projects, args, sess):
    """
    seed keystone projects and their dependant objects
    """

    logging.debug("seeding projects %s %s" % (domain.name, projects))

    # grab a keystone client
    keystone = keystoneclient.Client(session=sess,
                                     interface=args.interface)

    # todo: test parent support
    for project in projects:
        roles = None
        if 'roles' in project:
            roles = project.pop('roles')
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

        project = sanitize(project,
                           ('name', 'description', 'enabled', 'parent'))

        if 'name' not in project or not project['name']:
            logging.warn(
                "skipping project '%s/%s', since it is misconfigured" % (
                    domain.name, project))
            continue

        result = keystone.projects.list(domain=domain.id,
                                        name=project['name'])
        if not result:
            logging.info(
                "create project '%s/%s'" % (domain.name, project['name']))
            resource = keystone.projects.create(domain=domain, **project)
        else:
            resource = result[0]
            for attr in project.keys():
                if project[attr] != resource._info.get(attr, ''):
                    logging.info(
                        "update project '%s/%s'" % (
                            domain.name, project['name']))
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
            seed_project_network_quota(resource, network_quota, args, sess)

        # seed the projects network address scopes
        if address_scopes:
            seed_project_address_scopes(resource, address_scopes, args, sess)

        # seed the projects network subnet-pools
        if subnet_pools:
            seed_project_subnet_pools(resource, subnet_pools, args, sess)

        # seed the projects networks
        if networks:
            seed_project_networks(resource, networks, args, sess)

        # seed the projects routers
        if routers:
            seed_project_routers(resource, routers, args, sess)


def seed_project_network_quota(project, quota, args, sess):
    """
    seed a projects network quota
    """

    logging.debug("seeding network-quota of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    quota = sanitize(quota, (
        'floatingip', 'healthmonitor', 'l7policy', 'listener', 'loadbalancer',
        'network', 'pool', 'port', 'rbac_policy', 'router', 'security_group',
        'security_group_rule', 'subnet', 'subnetpool'))

    body = {'quota': quota.copy()}
    result = neutron.show_quota(project.id)
    if not result or not result['quota']:
        logging.info(
            "set project %s network quota to '%s'" % (project.name, quota))
        neutron.update_quota(project.id, body)
    else:
        resource = result['quota']
        for attr in quota.keys():
            if quota[attr] != resource.get(attr, ''):
                logging.info(
                    "set project %s network quota to '%s'" % (
                        project.name, quota))
                neutron.update_quota(project.id, body)
                break


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
        query = {'project_id': project.id, 'name': scope['name']}
        result = neutron.list_address_scopes(retrieve_all=True, **query)
        if not result or not result['address_scopes']:
            logging.info(
                "create address-scope '%s/%s'" % (project.name, scope['name']))
            result = neutron.create_address_scope(body)
            resource = result['address_scope']
        else:
            resource = result['address_scopes'][0]
            for attr in scope.keys():
                if scope[attr] != resource.get(attr, ''):
                    logging.info(
                        "update address-cope'%s/%s'" % (
                            project.name, scope['name']))
                    # drop read-only attributes
                    body['address_scope'].pop('tenant_id')
                    body['address_scope'].pop('ip_version')
                    neutron.update_address_scope(resource['id'], body)
                    break

        if subnet_pools:
            kvargs = {'address_scope_id': resource['id']}
            seed_project_subnet_pools(project, subnet_pools, args, sess,
                                      **kvargs)


def seed_project_subnet_pools(project, subnet_pools, args, sess, **kvargs):
    logging.debug(
        "seeding subnet-pools of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for subnet_pool in subnet_pools:
        subnet_pool = sanitize(subnet_pool, (
            'name', 'default_quota', 'prefixes', 'min_prefixlen', 'shared',
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

        query = {'project_id': project.id, 'name': subnet_pool['name']}
        result = neutron.list_subnetpools(retrieve_all=True, **query)
        if not result or not result['subnetpools']:
            logging.info(
                "create subnet-pool '%s/%s'" % (
                    project.name, subnet_pool['name']))
            result = neutron.create_subnetpool(body)
            # cache the subnetpool-id
            if project.id not in subnetpool_cache:
                subnetpool_cache[project.id] = {}
            subnetpool_cache[project.id][subnet_pool['name']] = result['subnetpool']['id']
        else:
            resource = result['subnetpools'][0]
            # cache the subnetpool-id
            if project.id not in subnetpool_cache:
                subnetpool_cache[project.id] = {}
            subnetpool_cache[project.id][subnet_pool['name']] = resource['id']

            for attr in subnet_pool.keys():
                if attr == 'prefixes':
                    for prefix in subnet_pool['prefixes']:
                        if prefix not in resource.get('prefixes', []):
                            logging.info(
                                "update subnet-pool prefixes '%s/%s'" % (
                                    project.name, subnet_pool['name']))
                            # drop read-only attributes
                            body['subnetpool'].pop('tenant_id')
                            body['subnetpool'].pop('shared')
                            neutron.update_subnetpool(resource['id'], body)
                            break
                else:
                    # a hacky comparison due to the neutron api not dealing with string/int attributes consistently
                    if str(subnet_pool[attr]) != str(resource.get(attr, '')):
                        logging.info(
                            "update subnet-pool'%s/%s'" % (
                                project.name, subnet_pool['name']))
                        # drop read-only attributes
                        body['subnetpool'].pop('tenant_id')
                        body['subnetpool'].pop('shared')
                        neutron.update_subnetpool(resource['id'], body)
                        break


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
        subnets = None
        if 'subnets' in network:
            subnets = network.pop('subnets', None)

        # rename some yaml unfriendly network attributes
        for key, value in rename.items():
            if key in network:
                network[value] = network.pop(key)

        network = sanitize(network, (
            'name', 'admin_state_up', 'port_security_enabled',
            'provider:network_type', 'provider:physical_network',
            'provider:segmentation_id', 'qos_policy_id', 'router:external',
            'shared', 'vlan_transparent', 'description'))

        if 'name' not in network or not network['name']:
            logging.warn(
                "skipping network '%s/%s', since it is misconfigured" % (
                    project.name, network))
            continue

        body = {'network': network.copy()}
        body['network']['tenant_id'] = project.id
        query = {'project_id': project.id, 'name': network['name']}
        result = neutron.list_networks(retrieve_all=True, **query)
        if not result or not result['networks']:
            logging.info(
                "create network '%s/%s'" % (project.name, network['name']))
            result = neutron.create_network(body)
            resource = result['network']
        else:
            resource = result['networks'][0]
            for attr in network.keys():
                if network[attr] != resource.get(attr, ''):
                    logging.info(
                        "update network'%s/%s'" % (
                            project.name, network['name']))
                    # drop read-only attributes
                    body['network'].pop('tenant_id')
                    neutron.update_network(resource['id'], body)
                    break

        if subnets:
            seed_network_subnets(resource, subnets, args, sess)


def seed_project_routers(project, routers, args, sess):
    """
    seed a projects neutron routers and dependent objects
    :param project:
    :param routers:
    :param args:
    :param sess:
    :return:
    """

    logging.debug("seeding routers of project %s" % project.name)

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for router in routers:
        interfaces = None
        if 'interfaces' in router:
            interfaces = router.pop('interfaces', None)

        router = sanitize(router, (
            'name', 'admin_state_up', 'description', 'external_gateway_info', 'distributed', 'ha', 'availability_zone_hints'))

        if 'name' not in router or not router['name']:
            logging.warn(
                "skipping router '%s/%s', since it is misconfigured" % (
                    project.name, router))
            continue

        if 'external_gateway_info' in router:
            # lookup network-id
            if 'network' in router['external_gateway_info']:
                network_id = get_network_id(project.id, router['external_gateway_info']['network'], neutron)
                if not network_id:
                    logging.warn(
                        "skipping router '%s/%s': external_gateway_info.network not found" % (
                            project.name, router))
                    continue
                router['external_gateway_info']['network_id'] = network_id
                router['external_gateway_info'].pop('network')

        body = {'router': router.copy()}
        body['router']['tenant_id'] = project.id
        query = {'project_id': project.id, 'name': router['name']}
        result = neutron.list_routers(retrieve_all=True, **query)
        if not result or not result['routers']:
            logging.info(
                "create router '%s/%s'" % (project.name, router['name']))
            result = neutron.create_router(body)
            resource = result['router']
        else:
            resource = result['routers'][0]
            for attr in router.keys():
                if router[attr] != resource.get(attr, ''):
                    # only evaluate external_gateway_info.network_id for now..
                    if attr == 'external_gateway_info':
                        if 'network_id' in router[attr] and 'network_id' in resource.get(attr, ''):
                            if router[attr]['network_id'] == resource[attr]['network_id']:
                                continue
                        else:
                            continue
                    logging.info(
                        "update router'%s/%s'" % (
                            project.name, router['name']))
                    # drop read-only attributes
                    body['router'].pop('tenant_id')
                    result = neutron.update_router(resource['id'], body)
                    resource = result['router']
                    break

        if interfaces:
            seed_router_interfaces(resource, interfaces, args, sess)


def seed_router_interfaces(router, interfaces, args, sess):
    """
    seed a routers interfaces (routes)
    :param router:
    :param interfaces:
    :param args:
    :param sess:
    :return:
    """

    logging.debug("seeding routes of router %s" % router['name'])

    # grab a neutron client
    neutron = neutronclient.Client(session=sess,
                                   interface=args.interface)

    for interface in interfaces:
        if 'subnet' in interface:
            # lookup subnet-id
            subnet_id = get_subnet_id(router['tenant_id'], interface['subnet'], neutron)
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
            if 'port_id' in interface and port['id'] == interface['port_id']:
                found = True
                break
            elif 'subnet_id' in interface:
                for ip in port['fixed_ips']:
                    if 'subnet_id' in ip and ip['subnet_id'] == interface['subnet_id']:
                        found = True
                        break
            if found:
                break

        if found:
            continue

        # add router interface
        neutron.add_interface_router(router['id'], interface)
        logging.info(
            "added interface %s to router'%s'" % (interface, router['name']))




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
            subnet['subnetpool_id'] = get_subnetpool_id(network['tenant_id'], subnet['subnetpool'], neutron)
            if not subnet['subnetpool_id']:
                logging.warn(
                    "skipping subnet '%s/%s', since its subnetpool is invalid" % (
                        network['name'], subnet))
                continue
            subnet.pop('subnetpool')

        subnet = sanitize(subnet, (
            'name', 'enable_dhcp', 'dns_nameservers',
            'allocation_pools', 'host_routes', 'ip_version',
            'gateway_ip', 'cidr', 'subnetpool_id', 'description'))

        if 'name' not in subnet or not subnet['name']:
            logging.warn(
                "skipping subnet '%s/%s', since it is misconfigured" % (
                    network['name'], subnet))
            continue

        body = {'subnet': subnet.copy()}
        body['subnet']['network_id'] = network['id']
        body['subnet']['tenant_id'] = network['tenant_id']

        query = {'network_id': network['id'], 'name': subnet['name']}
        result = neutron.list_subnets(retrieve_all=True, **query)
        if not result or not result['subnets']:
            logging.info(
                "create subnet '%s/%s'" % (network['name'], subnet['name']))
            neutron.create_subnet(body)
        else:
            resource = result['subnets'][0]
            for attr in subnet.keys():
                if subnet[attr] != resource.get(attr, ''):
                    logging.info(
                        "update subnet'%s/%s'" % (
                            network['name'], subnet['name']))
                    # drop read-only attributes
                    body['subnet'].pop('tenant_id')
                    body['subnet'].pop('network_id')
                    body['subnet'].pop('subnetpool_id')
                    body['subnet'].pop('ip_version')
                    neutron.update_subnet(resource['id'], body)
                    break


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
    logging.debug("seeding domain config %s %s" % (domain.name, driver))

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
        logging.error('could not configure domain %s: %s' % (domain.name, e))


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
                logging.info("update domain '%s'" % domain['name'])
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


def seed_flavor(flavor, args, sess):
    logging.debug("seeding flavor %s" % flavor)

    nova = novaclient.Client("2.1", session=sess,
                             interface=args.interface)

    flavor = sanitize(flavor, (
        'id', 'name', 'ram', 'disk', 'vcpus', 'swap', 'rxtx_factor',
        'is_public', 'disabled', 'ephemeral'))
    if 'name' not in flavor or not flavor['name']:
        logging.warn(
            "skipping flavor '%s', since it is misconfigured" % flavor)
        return

    # 'rename' some flavor attributes
    if 'is_public' in flavor:
        flavor['os-flavor-access:is_public'] = flavor.pop('is_public')
    if 'disabled' in flavor:
        flavor['OS-FLV-DISABLED:disabled'] = flavor.pop('disabled')
    if 'ephemeral' in flavor:
        flavor['OS-FLV-EXT-DATA:ephemeral'] = flavor.pop('ephemeral')

    result = nova.flavors.list(name=flavor['name'])
    if not result:
        logging.info(
            "create flavor '%s'" % flavor['name'])
        nova.flavors.create(**flavor)
    else:
        resource = result[0]
        for attr in flavor.keys():
            if flavor[attr] != resource._info.get(attr, ''):
                logging.info("update flavor '%s'" %
                             flavor['name'])
                nova.flavors.update(resource.id, **flavor)
                break


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
                    logging.info("add user '%s' to group '%s'" % (uid, group))
                    keystone.users.add_to_group(user, group)
            else:
                logging.warn(
                    "could not add user '%s' to group '%s'" % (uid, group))


def resolve_role_assignments(keystone):
    for assignment in role_assignments:
        logging.debug("resolving role assignment %s" % assignment)

        role_assignment = dict()
        role = assignment.pop('role')
        role_id = get_role_id(role, keystone)
        if 'user' in assignment:
            user, domain = assignment['user'].split('@')
            id = get_user_id(domain, user, keystone)
            if not id:
                logging.warn("user %s not found, skipping role assignment.." % \
                             assignment['user'])
                continue
            role_assignment['user'] = id
        elif 'group' in assignment:
            group, domain = assignment['group'].split('@')
            id = get_group_id(domain, group, keystone)
            if not id:
                logging.warn("group %s not found, skipping role assignment.." % \
                             assignment['group'])
                continue
            role_assignment['group'] = id
        if 'domain' in assignment:
            id = get_domain_id(assignment['domain'], keystone)
            if not id:
                logging.warn(
                    "domain %s not found, skipping role assignment.." % \
                    assignment['domain'])
                continue
            role_assignment['domain'] = id
        if 'project' in assignment:
            project, domain = assignment['project'].split('@')
            id = get_project_id(domain, project, keystone)
            if not id:
                logging.warn(
                    "project %s not found, skipping role assignment.." % \
                    assignment['project'])
                continue
            role_assignment['project'] = id
        if 'inherited' in assignment:
            role_assignment['os_inherit_extension_inherited'] = assignment[
                'inherited']

        try:
            keystone.roles.check(role_id, **role_assignment)
        except exceptions.NotFound:
            logging.info("grant '%s' to '%s'" % (role, assignment))
            keystone.roles.grant(role_id, **role_assignment)


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

    if "flavors" in config:
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
        logging.info("seeding openstack with '%s'" % config)

        if not args.dry_run:
            plugin = cli.load_from_argparse_arguments(args)
            sess = session.Session(auth=plugin, user_agent='openstack-seeder')
            seed_config(config, args, sess)
        return 0
    except Exception as e:
        logging.error("could not seed openstack: %s" % e)
        logging.error(traceback.format_exc())
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
    parser.add_argument("-l", "--log", dest="logLevel",
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                 'CRITICAL'], help="Set the logging level",
                        default='INFO')
    parser.add_argument('--dry-run', default=False, action='store_true',
                        help=('Only parse the seed, do no actual seeding.'))
    cli.register_argparse_arguments(parser, sys.argv[1:])
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
        datefmt='%d.%m.%Y %H:%M:%S',
        level=getattr(logging, args.logLevel))

    return seed(args)


if __name__ == "__main__":
    sys.exit(main())
