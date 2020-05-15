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
import random
import subprocess

from oslotest import base


RP_PREFIX = 'osc-placement-functional-tests-'


class BaseTestCase(base.BaseTestCase):
    VERSION = None

    @classmethod
    def openstack(cls, cmd, may_fail=False, use_json=False):
        result = None
        try:
            to_exec = ['openstack'] + cmd.split()
            if use_json:
                to_exec += ['-f', 'json']
            if cls.VERSION is not None:
                to_exec += ['--os-placement-api-version', cls.VERSION]

            output = subprocess.check_output(to_exec, stderr=subprocess.STDOUT)
            result = (output or b'').decode('utf-8')
        except subprocess.CalledProcessError as e:
            msg = 'Command: "%s"\noutput: %s' % (' '.join(e.cmd), e.output)
            e.cmd = msg
            if not may_fail:
                raise

        if use_json and result:
            return json.loads(result)
        else:
            return result

    def rand_name(self, name='', prefix=None):
        """Generate a random name that includes a random number

        :param str name: The name that you want to include
        :param str prefix: The prefix that you want to include
        :return: a random name. The format is
                 '<prefix>-<name>-<random number>'.
                 (e.g. 'prefixfoo-namebar-154876201')
        :rtype: string
        """
        # NOTE(lajos katona): This method originally is in tempest-lib.
        randbits = str(random.randint(1, 0x7fffffff))
        rand_name = randbits
        if name:
            rand_name = name + '-' + rand_name
        if prefix:
            rand_name = prefix + '-' + rand_name
        return rand_name

    def assertCommandFailed(self, message, func, *args, **kwargs):
        signature = [func]
        signature.extend(args)
        try:
            func(*args, **kwargs)
            self.fail('Command does not fail as required (%s)' % signature)

        except subprocess.CalledProcessError as e:
            self.assertIn(
                message, e.output,
                'Command "%s" fails with different message' % e.cmd)

    def resource_provider_create(self,
                                 name='',
                                 parent_provider_uuid=None):
        if not name:
            name = self.rand_name(name='', prefix=RP_PREFIX)

        to_exec = 'resource provider create ' + name
        if parent_provider_uuid is not None:
            to_exec += ' --parent-provider ' + parent_provider_uuid
        res = self.openstack(to_exec, use_json=True)

        def cleanup():
            try:
                self.resource_provider_delete(res['uuid'])
            except subprocess.CalledProcessError as exc:
                # may have already been deleted by a test case
                err_message = exc.output.decode('utf-8').lower()
                if 'no resource provider' not in err_message:
                    raise
        self.addCleanup(cleanup)

        return res

    def resource_provider_set(self, uuid, name, parent_provider_uuid=None):
        to_exec = 'resource provider set ' + uuid + ' --name ' + name
        if parent_provider_uuid is not None:
            to_exec += ' --parent-provider ' + parent_provider_uuid
        return self.openstack(to_exec, use_json=True)

    def resource_provider_show(self, uuid, allocations=False):
        cmd = 'resource provider show ' + uuid
        if allocations:
            cmd = cmd + ' --allocations'

        return self.openstack(cmd, use_json=True)

    def resource_provider_list(self, uuid=None, name=None,
                               aggregate_uuids=None, resources=None,
                               in_tree=None):
        to_exec = 'resource provider list'
        if uuid:
            to_exec += ' --uuid ' + uuid
        if name:
            to_exec += ' --name ' + name
        if aggregate_uuids:
            to_exec += ' ' + ' '.join(
                '--aggregate-uuid %s' % a for a in aggregate_uuids)
        if resources:
            to_exec += ' ' + ' '.join('--resource %s' % r for r in resources)
        if in_tree:
            to_exec += ' --in-tree ' + in_tree

        return self.openstack(to_exec, use_json=True)

    def resource_provider_delete(self, uuid):
        return self.openstack('resource provider delete ' + uuid)

    def resource_allocation_show(self, consumer_uuid):
        return self.openstack(
            'resource provider allocation show ' + consumer_uuid,
            use_json=True
        )

    def resource_allocation_set(self, consumer_uuid, allocations,
                                project_id=None, user_id=None,
                                use_json=True):
        cmd = 'resource provider allocation set {allocs} {uuid}'.format(
            uuid=consumer_uuid,
            allocs=' '.join('--allocation {}'.format(a) for a in allocations)
        )
        if project_id:
            cmd += ' --project-id %s' % project_id
        if user_id:
            cmd += ' --user-id %s' % user_id
        result = self.openstack(cmd, use_json=use_json)

        def cleanup(uuid):
            try:
                self.openstack('resource provider allocation delete ' + uuid)
            except subprocess.CalledProcessError as exc:
                # may have already been deleted by a test case
                if 'not found' in exc.output.decode('utf-8').lower():
                    pass
        self.addCleanup(cleanup, consumer_uuid)

        return result

    def resource_allocation_delete(self, consumer_uuid):
        cmd = 'resource provider allocation delete ' + consumer_uuid
        return self.openstack(cmd)

    def resource_inventory_show(self, uuid, resource_class):
        cmd = 'resource provider inventory show {uuid} {rc}'.format(
            uuid=uuid, rc=resource_class
        )
        return self.openstack(cmd, use_json=True)

    def resource_inventory_list(self, uuid):
        return self.openstack('resource provider inventory list ' + uuid,
                              use_json=True)

    def resource_inventory_delete(self, uuid, resource_class=None):
        cmd = 'resource provider inventory delete {uuid}'.format(uuid=uuid)
        if resource_class:
            cmd += ' --resource-class ' + resource_class
        self.openstack(cmd)

    def resource_inventory_set(self, uuid, *resources):
        cmd = 'resource provider inventory set {uuid} {resources}'.format(
            uuid=uuid, resources=' '.join(
                ['--resource %s' % r for r in resources]))
        return self.openstack(cmd, use_json=True)

    def resource_inventory_class_set(self, uuid, resource_class, **kwargs):
        opts = ['--%s=%s' % (k, v) for k, v in kwargs.items()]
        cmd = 'resource provider inventory class set {uuid} {rc} {opts}'.\
            format(uuid=uuid, rc=resource_class, opts=' '.join(opts))
        return self.openstack(cmd, use_json=True)

    def resource_provider_show_usage(self, uuid):
        return self.openstack('resource provider usage show ' + uuid,
                              use_json=True)

    def resource_show_usage(self, project_id, user_id=None):
        cmd = 'resource usage show %s' % project_id
        if user_id:
            cmd += ' --user-id %s' % user_id
        return self.openstack(cmd, use_json=True)

    def resource_provider_aggregate_list(self, uuid):
        return self.openstack('resource provider aggregate list ' + uuid,
                              use_json=True)

    def resource_provider_aggregate_set(self, uuid, *aggregates):
        cmd = 'resource provider aggregate set %s ' % uuid
        cmd += ' '.join('--aggregate %s' % aggregate
                        for aggregate in aggregates)
        return self.openstack(cmd, use_json=True)

    def resource_class_list(self):
        return self.openstack('resource class list', use_json=True)

    def resource_class_show(self, name):
        return self.openstack('resource class show ' + name, use_json=True)

    def resource_class_create(self, name):
        return self.openstack('resource class create ' + name)

    def resource_class_set(self, name):
        return self.openstack('resource class set ' + name)

    def resource_class_delete(self, name):
        return self.openstack('resource class delete ' + name)

    def trait_list(self, name=None, associated=False):
        cmd = 'trait list'
        if name:
            cmd += ' --name ' + name
        if associated:
            cmd += ' --associated'
        return self.openstack(cmd, use_json=True)

    def trait_show(self, name):
        cmd = 'trait show %s' % name
        return self.openstack(cmd, use_json=True)

    def trait_create(self, name):
        cmd = 'trait create %s' % name
        self.openstack(cmd)

        def cleanup():
            try:
                self.trait_delete(name)
            except subprocess.CalledProcessError as exc:
                # may have already been deleted by a test case
                err_message = exc.output.decode('utf-8').lower()
                if 'http 404' not in err_message:
                    raise
        self.addCleanup(cleanup)

    def trait_delete(self, name):
        cmd = 'trait delete %s' % name
        self.openstack(cmd)

    def resource_provider_trait_list(self, uuid):
        cmd = 'resource provider trait list %s ' % uuid
        return self.openstack(cmd, use_json=True)

    def resource_provider_trait_set(self, uuid, *traits):
        cmd = 'resource provider trait set %s ' % uuid
        cmd += ' '.join('--trait %s' % trait for trait in traits)
        return self.openstack(cmd, use_json=True)

    def resource_provider_trait_delete(self, uuid):
        cmd = 'resource provider trait delete %s ' % uuid
        self.openstack(cmd)

    def allocation_candidate_list(self, resources, required=None, limit=None):
        cmd = 'allocation candidate list ' + ' '.join(
            '--resource %s' % resource for resource in resources)
        if required is not None:
            cmd += ''.join([' --required %s' % t for t in required])
        if limit is not None:
            cmd += ' --limit %d' % limit
        return self.openstack(cmd, use_json=True)
