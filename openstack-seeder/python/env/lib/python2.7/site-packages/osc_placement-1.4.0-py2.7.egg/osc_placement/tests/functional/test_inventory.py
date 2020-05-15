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

import subprocess

from osc_placement.tests.functional import base


class TestInventory(base.BaseTestCase):
    def setUp(self):
        super(TestInventory, self).setUp()

        self.rp = self.resource_provider_create()

    def test_inventory_show(self):
        rp_uuid = self.rp['uuid']
        expected = {'min_unit': 1,
                    'max_unit': 12,
                    'reserved': 0,
                    'step_size': 1,
                    'total': 12,
                    'allocation_ratio': 16.0}

        args = ['VCPU:%s=%s' % (k, v) for k, v in expected.items()]
        self.resource_inventory_set(rp_uuid, *args)
        self.assertEqual(expected,
                         self.resource_inventory_show(rp_uuid, 'VCPU'))

    def test_inventory_show_not_found(self):
        rp_uuid = self.rp['uuid']

        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_show,
                                rp_uuid, 'VCPU')
        self.assertIn('No inventory of class VCPU for {}'.format(rp_uuid),
                      exc.output.decode('utf-8'))

    def test_inventory_delete(self):
        rp_uuid = self.rp['uuid']

        self.resource_inventory_set(rp_uuid, 'VCPU=8')

        self.resource_inventory_delete(rp_uuid, 'VCPU')
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_show,
                                rp_uuid, 'VCPU')
        self.assertIn('No inventory of class VCPU for {}'.format(rp_uuid),
                      exc.output.decode('utf-8'))

    def test_inventory_delete_not_found(self):
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_delete,
                                self.rp['uuid'], 'VCPU')
        self.assertIn('No inventory of class VCPU found for delete',
                      exc.output.decode('utf-8'))

    def test_delete_all_inventories(self):
        # Negative test to assert command failure because
        # microversion < 1.5 and --resource-class is not specified.
        self.assertCommandFailed(
            'argument --resource-class is required',
            self.resource_inventory_delete,
            'fake_uuid')


class TestSetInventory(base.BaseTestCase):
    def test_fail_if_no_rp(self):
        exc = self.assertRaises(
            subprocess.CalledProcessError,
            self.openstack, 'resource provider inventory set')
        self.assertIn('too few arguments', exc.output.decode('utf-8'))

    def test_set_empty_inventories(self):
        rp = self.resource_provider_create()
        self.assertEqual([], self.resource_inventory_set(rp['uuid']))

    def test_fail_if_incorrect_resource(self):
        rp = self.resource_provider_create()
        # wrong format
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_set,
                                rp['uuid'], 'VCPU')
        self.assertIn('must have "name=value"', exc.output.decode('utf-8'))
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_set,
                                rp['uuid'], 'VCPU==')
        self.assertIn('must have "name=value"', exc.output.decode('utf-8'))
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_set,
                                rp['uuid'], '=10')
        self.assertIn('must be not empty', exc.output.decode('utf-8'))
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_set,
                                rp['uuid'], 'v=')
        self.assertIn('must be not empty', exc.output.decode('utf-8'))

        # unknown class
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_set,
                                rp['uuid'], 'UNKNOWN_CPU=16')
        self.assertIn('Unknown resource class', exc.output.decode('utf-8'))
        # unknown property
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_set,
                                rp['uuid'], 'VCPU:fake=16')
        self.assertIn('Unknown inventory field', exc.output.decode('utf-8'))

    def test_set_multiple_classes(self):
        rp = self.resource_provider_create()
        resp = self.resource_inventory_set(
            rp['uuid'],
            'VCPU=8',
            'VCPU:max_unit=4',
            'MEMORY_MB=1024',
            'MEMORY_MB:reserved=256',
            'DISK_GB=16',
            'DISK_GB:allocation_ratio=1.5',
            'DISK_GB:min_unit=2',
            'DISK_GB:step_size=2')

        def check(inventories):
            self.assertEqual(8, inventories['VCPU']['total'])
            self.assertEqual(4, inventories['VCPU']['max_unit'])
            self.assertEqual(1024, inventories['MEMORY_MB']['total'])
            self.assertEqual(256, inventories['MEMORY_MB']['reserved'])
            self.assertEqual(16, inventories['DISK_GB']['total'])
            self.assertEqual(2, inventories['DISK_GB']['min_unit'])
            self.assertEqual(2, inventories['DISK_GB']['step_size'])
            self.assertEqual(1.5, inventories['DISK_GB']['allocation_ratio'])

        check({r['resource_class']: r for r in resp})
        resp = self.resource_inventory_list(rp['uuid'])
        check({r['resource_class']: r for r in resp})

    def test_set_known_and_unknown_class(self):
        rp = self.resource_provider_create()
        exc = self.assertRaises(subprocess.CalledProcessError,
                                self.resource_inventory_set,
                                rp['uuid'], 'VCPU=8', 'UNKNOWN=4')
        self.assertIn('Unknown resource class', exc.output.decode('utf-8'))
        self.assertEqual([], self.resource_inventory_list(rp['uuid']))

    def test_replace_previous_values(self):
        """Test each new set call replaces previous inventories totally."""
        rp = self.resource_provider_create()
        # set disk inventory first
        self.resource_inventory_set(rp['uuid'], 'DISK_GB=16')
        # set memory and vcpu inventories
        self.resource_inventory_set(rp['uuid'], 'MEMORY_MB=16', 'VCPU=32')
        resp = self.resource_inventory_list(rp['uuid'])
        inv = {r['resource_class']: r for r in resp}
        # no disk inventory as it was overwritten
        self.assertNotIn('DISK_GB', inv)
        self.assertIn('VCPU', inv)
        self.assertIn('MEMORY_MB', inv)

    def test_delete_via_set(self):
        rp = self.resource_provider_create()
        self.resource_inventory_set(rp['uuid'], 'DISK_GB=16')
        self.resource_inventory_set(rp['uuid'])
        self.assertEqual([], self.resource_inventory_list(rp['uuid']))

    def test_fail_if_incorrect_parameters_set_class_inventory(self):
        exc = self.assertRaises(
            subprocess.CalledProcessError,
            self.openstack, 'resource provider inventory class set')
        self.assertIn('too few arguments', exc.output.decode('utf-8'))
        exc = self.assertRaises(
            subprocess.CalledProcessError,
            self.openstack, 'resource provider inventory class set fake_uuid')
        self.assertIn('too few arguments', exc.output.decode('utf-8'))
        exc = self.assertRaises(
            subprocess.CalledProcessError,
            self.openstack,
            ('resource provider inventory class set '
             'fake_uuid fake_class --total 5 --unknown 1'))
        self.assertIn('unrecognized arguments', exc.output.decode('utf-8'))
        # Valid RP UUID and resource class, but no inventory field.
        rp = self.resource_provider_create()
        exc = self.assertRaises(
            subprocess.CalledProcessError, self.openstack,
            'resource provider inventory class set %s VCPU' % rp['uuid'])
        self.assertIn('argument --total is required',
                      exc.output.decode('utf-8'))

    def test_set_inventory_for_resource_class(self):
        rp = self.resource_provider_create()
        self.resource_inventory_set(rp['uuid'], 'MEMORY_MB=16', 'VCPU=32')
        self.resource_inventory_class_set(
            rp['uuid'], 'MEMORY_MB', total=128, step_size=16)
        resp = self.resource_inventory_list(rp['uuid'])
        inv = {r['resource_class']: r for r in resp}
        self.assertEqual(128, inv['MEMORY_MB']['total'])
        self.assertEqual(16, inv['MEMORY_MB']['step_size'])
        self.assertEqual(32, inv['VCPU']['total'])


class TestInventory15(TestInventory):
    VERSION = '1.5'

    def test_delete_all_inventories(self):
        rp = self.resource_provider_create()
        self.resource_inventory_set(rp['uuid'], 'MEMORY_MB=16', 'VCPU=32')
        self.resource_inventory_delete(rp['uuid'])
        self.assertEqual([], self.resource_inventory_list(rp['uuid']))
