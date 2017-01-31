#!/usr/bin/env python
import argparse
import sys
import yaml
import logging
import traceback
from urlparse import urlparse

from keystoneauth1 import session
from keystoneauth1.loading import cli
from keystoneclient import exceptions
from keystoneclient.v3 import client as keystoneclient
from novaclient import client as novaclient

#todo: raven instrumentation, adress scopes, subnet pools

# caches
role_cache = {}
domain_cache = {}
project_cache = {}
user_cache = {}
group_cache = {}

# assignments to be resolved after everything else has been processed
group_members = {}
role_assignments = []


def get_role_id(name, keystone):
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
    logging.debug("seeding role %s" % role)

    result = keystone.roles.list(name=role)
    if not result:
        logging.info("create role '%s'" % role)
        resource = keystone.roles.create(name=role)
    else:
        resource = result[0]

    role_cache[resource.name] = resource.id


def seed_region(region, keystone):
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


def seed_projects(domain, projects, keystone):
    logging.debug("seeding projects %s %s" % (domain.name, projects))

    # todo: test parent support
    for project in projects:
        roles = None
        if 'roles' in project:
            roles = project.pop('roles')
        endpoints = None
        if 'project_endpoints' in project:
            endpoints = project.pop('project_endpoints', None)
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

        if endpoints:
            seed_project_endpoints(resource, endpoints, keystone)

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


# compares domain configurations (and ignores passwords in the comparison)
def domain_config_equal(new, current):
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


def seed_domain(domain, keystone):
    logging.debug("seeding domain %s" % domain)

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
        seed_projects(resource, projects, keystone)
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


def seed_flavor(flavor, nova):
    logging.debug("seeding flavor %s" % flavor)

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
        resource = nova.flavors.create(**flavor)
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


def seed_config(config, keystone, session):
    global group_members, role_assignments

    # reset
    group_members = {}
    role_assignments = []

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
        nova = novaclient.Client("2.1", session=session)
        for flavor in config['flavors']:
            seed_flavor(flavor, nova)

    if 'domains' in config:
        for domain in config['domains']:
            seed_domain(domain, keystone)

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

        plugin = cli.load_from_argparse_arguments(args)
        sess = session.Session(auth=plugin, user_agent='openstack-seeder')
        keystone = keystoneclient.Client(session=sess,
                                         interface=args.interface)
        seed_config(config, keystone, sess)
        return 0
    except Exception as e:
        logging.error("could not seed openstack: %s" % e)
        logging.error(traceback.format_exc())
        return 1


def main():
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
    cli.register_argparse_arguments(parser, sys.argv[1:])
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
        datefmt='%d.%m.%Y %H:%M:%S',
        level=getattr(logging, args.logLevel))

    return seed(args)


if __name__ == "__main__":
    sys.exit(main())
