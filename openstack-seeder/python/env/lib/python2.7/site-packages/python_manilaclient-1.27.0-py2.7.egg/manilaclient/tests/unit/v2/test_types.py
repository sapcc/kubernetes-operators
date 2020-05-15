# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import ddt
import itertools
import mock

from manilaclient import api_versions
from manilaclient import exceptions
from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import share_types

cs = fakes.FakeClient()


def get_valid_type_create_data_2_0():

    public = [True, False]
    dhss = [True, False]
    snapshot = [None, True, False]
    extra_specs = [None, {'foo': 'bar'}]

    combos = list(itertools.product(public, dhss, snapshot, extra_specs))

    return combos


def get_valid_type_create_data_2_24():

    public = [True, False]
    dhss = [True, False]
    snapshot = [None]
    create_from_snapshot = [None]
    extra_specs = [None, {'replication_type': 'writable', 'foo': 'bar'}]

    snapshot_none_combos = list(itertools.product(public, dhss, snapshot,
                                                  create_from_snapshot,
                                                  extra_specs))

    public = [True, False]
    dhss = [True, False]
    snapshot = [True]
    create_from_snapshot = [True, False, None]
    extra_specs = [None, {'replication_type': 'readable', 'foo': 'bar'}]

    snapshot_true_combos = list(itertools.product(public, dhss, snapshot,
                                                  create_from_snapshot,
                                                  extra_specs))

    public = [True, False]
    dhss = [True, False]
    snapshot = [False]
    create_from_snapshot = [False, None]
    extra_specs = [None, {'replication_type': 'dr', 'foo': 'bar'}]

    snapshot_false_combos = list(itertools.product(public, dhss, snapshot,
                                                   create_from_snapshot,
                                                   extra_specs))

    return snapshot_none_combos + snapshot_true_combos + snapshot_false_combos


def get_valid_type_create_data_2_27():

    public = [True, False]
    dhss = [True, False]
    snapshot = [None]
    create_from_snapshot = [None]
    revert_to_snapshot = [None]
    extra_specs = [None, {'replication_type': 'writable', 'foo': 'bar'}]

    snapshot_none_combos = list(itertools.product(public, dhss, snapshot,
                                                  create_from_snapshot,
                                                  revert_to_snapshot,
                                                  extra_specs))

    public = [True, False]
    dhss = [True, False]
    snapshot = [True]
    create_from_snapshot = [True, False, None]
    revert_to_snapshot = [True, False, None]
    extra_specs = [None, {'replication_type': 'readable', 'foo': 'bar'}]

    snapshot_true_combos = list(itertools.product(public, dhss, snapshot,
                                                  create_from_snapshot,
                                                  revert_to_snapshot,
                                                  extra_specs))

    public = [True, False]
    dhss = [True, False]
    snapshot = [False]
    create_from_snapshot = [False, None]
    revert_to_snapshot = [False, None]
    extra_specs = [None, {'replication_type': 'dr', 'foo': 'bar'}]

    snapshot_false_combos = list(itertools.product(public, dhss, snapshot,
                                                   create_from_snapshot,
                                                   revert_to_snapshot,
                                                   extra_specs))

    return snapshot_none_combos + snapshot_true_combos + snapshot_false_combos


@ddt.ddt
class TypesTest(utils.TestCase):

    def _get_share_types_manager(self, microversion):
        version = api_versions.APIVersion(microversion)
        mock_microversion = mock.Mock(api_version=version)
        return share_types.ShareTypeManager(api=mock_microversion)

    @ddt.data(
        {'snapshot_support': 'False'},
        {'snapshot_support': 'False', 'foo': 'bar'},
    )
    def test_init(self, extra_specs):
        info = {'extra_specs': extra_specs}

        share_type = share_types.ShareType(share_types.ShareTypeManager, info)

        self.assertTrue(hasattr(share_type, '_required_extra_specs'))
        self.assertTrue(hasattr(share_type, '_optional_extra_specs'))
        self.assertIsInstance(share_type._required_extra_specs, dict)
        self.assertIsInstance(share_type._optional_extra_specs, dict)
        self.assertEqual(extra_specs, share_type.get_optional_keys())

    def test_list_types(self):
        tl = cs.share_types.list()
        cs.assert_called('GET', '/types?is_public=all')
        for t in tl:
            self.assertIsInstance(t, share_types.ShareType)
            self.assertTrue(callable(getattr(t, 'get_required_keys', '')))
            self.assertTrue(callable(getattr(t, 'get_optional_keys', '')))
            self.assertEqual({'test': 'test'}, t.get_required_keys())
            self.assertEqual({'test1': 'test1'}, t.get_optional_keys())

    def test_list_types_only_public(self):
        cs.share_types.list(show_all=False)
        cs.assert_called('GET', '/types')

    def test_list_types_search_by_extra_specs(self):
        search_opts = {'extra_specs': {'aa': 'bb'}}
        cs.share_types.list(search_opts=search_opts)
        expect = '/types?extra_specs=%7B%27aa%27%3A+%27bb%27%7D&is_public=all'
        cs.assert_called('GET', expect)

    @ddt.data(*get_valid_type_create_data_2_0())
    @ddt.unpack
    def test_create_2_7(self, is_public, dhss, snapshot, extra_specs):

        extra_specs = copy.copy(extra_specs)

        manager = self._get_share_types_manager("2.7")
        self.mock_object(manager, '_create', mock.Mock(return_value="fake"))

        result = manager.create(
            'test-type-3', spec_driver_handles_share_servers=dhss,
            spec_snapshot_support=snapshot, extra_specs=extra_specs,
            is_public=is_public)

        if extra_specs is None:
            extra_specs = {}

        expected_extra_specs = dict(extra_specs)

        expected_body = {
            "share_type": {
                "name": 'test-type-3',
                'share_type_access:is_public': is_public,
                "extra_specs": expected_extra_specs,
            }
        }

        expected_body["share_type"]["extra_specs"][
            "driver_handles_share_servers"] = dhss
        expected_body["share_type"]["extra_specs"]['snapshot_support'] = (
            True if snapshot is None else snapshot)

        manager._create.assert_called_once_with(
            "/types", expected_body, "share_type")
        self.assertEqual("fake", result)

    def _add_standard_extra_specs_to_dict(self, extra_specs,
                                          create_from_snapshot=None,
                                          revert_to_snapshot=None,
                                          mount_snapshot=None):

        # Short-circuit checks to allow for extra specs to be (and remain) None
        if all(spec is None for spec in [
                create_from_snapshot, revert_to_snapshot, mount_snapshot]):
            return extra_specs

        extra_specs = extra_specs or {}

        if create_from_snapshot is not None:
            extra_specs['create_share_from_snapshot_support'] = (
                create_from_snapshot)
        if revert_to_snapshot is not None:
            extra_specs['revert_to_snapshot_support'] = (
                revert_to_snapshot)
        if mount_snapshot is not None:
            extra_specs['mount_snapshot_support'] = (
                mount_snapshot)

        return extra_specs

    @ddt.data(*get_valid_type_create_data_2_24())
    @ddt.unpack
    def test_create_2_24(self, is_public, dhss, snapshot, create_from_snapshot,
                         extra_specs):

        extra_specs = copy.copy(extra_specs)
        extra_specs = self._add_standard_extra_specs_to_dict(
            extra_specs, create_from_snapshot=create_from_snapshot)

        manager = self._get_share_types_manager("2.24")
        self.mock_object(manager, '_create', mock.Mock(return_value="fake"))

        result = manager.create(
            'test-type-3', spec_driver_handles_share_servers=dhss,
            spec_snapshot_support=snapshot,
            extra_specs=extra_specs, is_public=is_public)

        expected_extra_specs = dict(extra_specs or {})
        expected_extra_specs["driver_handles_share_servers"] = dhss

        if snapshot is None:
            expected_extra_specs.pop("snapshot_support", None)
        else:
            expected_extra_specs["snapshot_support"] = snapshot

        if create_from_snapshot is None:
            expected_extra_specs.pop("create_share_from_snapshot_support",
                                     None)
        else:
            expected_extra_specs["create_share_from_snapshot_support"] = (
                create_from_snapshot)

        expected_body = {
            "share_type": {
                "name": 'test-type-3',
                'share_type_access:is_public': is_public,
                "extra_specs": expected_extra_specs,
            }
        }

        manager._create.assert_called_once_with(
            "/types", expected_body, "share_type")
        self.assertEqual("fake", result)

    @ddt.data(*get_valid_type_create_data_2_27())
    @ddt.unpack
    def test_create_2_27(self, is_public, dhss, snapshot, create_from_snapshot,
                         revert_to_snapshot, extra_specs):

        extra_specs = copy.copy(extra_specs)
        extra_specs = self._add_standard_extra_specs_to_dict(
            extra_specs, create_from_snapshot=create_from_snapshot,
            revert_to_snapshot=revert_to_snapshot)

        manager = self._get_share_types_manager("2.27")
        self.mock_object(manager, '_create', mock.Mock(return_value="fake"))

        result = manager.create(
            'test-type-3', spec_driver_handles_share_servers=dhss,
            spec_snapshot_support=snapshot,
            extra_specs=extra_specs, is_public=is_public)

        expected_extra_specs = dict(extra_specs or {})
        expected_extra_specs["driver_handles_share_servers"] = dhss

        if snapshot is None:
            expected_extra_specs.pop("snapshot_support", None)
        else:
            expected_extra_specs["snapshot_support"] = snapshot

        if create_from_snapshot is None:
            expected_extra_specs.pop("create_share_from_snapshot_support",
                                     None)
        else:
            expected_extra_specs["create_share_from_snapshot_support"] = (
                create_from_snapshot)

        if revert_to_snapshot is None:
            expected_extra_specs.pop("revert_to_snapshot_support", None)
        else:
            expected_extra_specs["revert_to_snapshot_support"] = (
                revert_to_snapshot)

        expected_body = {
            "share_type": {
                "name": 'test-type-3',
                'share_type_access:is_public': is_public,
                "extra_specs": expected_extra_specs,
            }
        }

        manager._create.assert_called_once_with(
            "/types", expected_body, "share_type")
        self.assertEqual("fake", result)

    @ddt.data(
        (False, False, True, {'snapshot_support': True,
                              'replication_type': 'fake_repl_type'}),
        (False, False, False, {'snapshot_support': False,
                               'replication_type': 'fake_repl_type'}),
        (False, False, True, {'snapshot_support': False,
                              'replication_type': 'fake_repl_type'}),
        (False, False, False, {'snapshot_support': True,
                               'replication_type': 'fake_repl_type'}),

        (False, True, None, {'driver_handles_share_servers': True}),
        (False, False, None, {'driver_handles_share_servers': True}),
        (False, None, None, {'driver_handles_share_servers': True}),
        (False, None, None, {'driver_handles_share_servers': None}),
    )
    @ddt.unpack
    def test_create_error_2_7(self, is_public, dhss, snapshot,
                              extra_specs):
        manager = self._get_share_types_manager("2.7")
        self.mock_object(manager, '_create', mock.Mock(return_value="fake"))

        self.assertRaises(
            exceptions.CommandError,
            manager.create,
            'test-type-3',
            spec_driver_handles_share_servers=dhss,
            spec_snapshot_support=snapshot,
            extra_specs=extra_specs,
            is_public=is_public)

    @ddt.data(
        (False, True, None, None, {'driver_handles_share_servers': True}),
        (False, False, False, False, {'snapshot_support': True,
                                      'replication_type': 'fake_repl_type'}),
    )
    @ddt.unpack
    def test_create_error_2_24(self, is_public, dhss, snapshot,
                               create_from_snapshot, extra_specs):

        extra_specs = copy.copy(extra_specs)
        extra_specs = self._add_standard_extra_specs_to_dict(
            extra_specs, create_from_snapshot=create_from_snapshot)

        manager = self._get_share_types_manager("2.24")
        self.mock_object(manager, '_create', mock.Mock(return_value="fake"))

        self.assertRaises(
            exceptions.CommandError,
            manager.create,
            'test-type-3',
            spec_driver_handles_share_servers=dhss,
            spec_snapshot_support=snapshot,
            extra_specs=extra_specs,
            is_public=is_public)

    @ddt.data(
        ("2.6", True),
        ("2.7", True),
        ("2.24", True),
        ("2.41", True),
        ("2.6", False),
        ("2.7", False),
        ("2.24", False),
        ("2.41", False),
    )
    @ddt.unpack
    def test_create_with_default_values(self, microversion, dhss):

        manager = self._get_share_types_manager(microversion)
        self.mock_object(manager, '_create', mock.Mock(return_value="fake"))

        description = 'test description'
        if (api_versions.APIVersion(microversion) >=
                api_versions.APIVersion("2.41")):
            result = manager.create(
                'test-type-3', dhss, description=description)
        else:
            result = manager.create('test-type-3', dhss)

        if (api_versions.APIVersion(microversion) >
                api_versions.APIVersion("2.6")):
            is_public_keyname = "share_type_access:is_public"
        else:
            is_public_keyname = "os-share-type-access:is_public"

        expected_body = {
            "share_type": {
                "name": 'test-type-3',
                is_public_keyname: True,
                "extra_specs": {
                    "driver_handles_share_servers": dhss,
                    "snapshot_support": True,
                }
            }
        }

        if (api_versions.APIVersion(microversion) >=
                api_versions.APIVersion("2.24")):
            del expected_body['share_type']['extra_specs']['snapshot_support']

        if (api_versions.APIVersion(microversion) >=
                api_versions.APIVersion("2.41")):
            expected_body['share_type']['description'] = description
        manager._create.assert_called_once_with(
            "/types", expected_body, "share_type")
        self.assertEqual("fake", result)

    def test_set_key(self):
        t = cs.share_types.get(1)
        t.set_keys({'k': 'v'})
        cs.assert_called('POST',
                         '/types/1/extra_specs',
                         {'extra_specs': {'k': 'v'}})

    def test_unset_keys(self):
        t = cs.share_types.get(1)
        t.unset_keys(['k'])
        cs.assert_called('DELETE', '/types/1/extra_specs/k')

    def test_delete(self):
        cs.share_types.delete(1)
        cs.assert_called('DELETE', '/types/1')

    def test_get_keys_from_resource_data(self):
        manager = mock.Mock()
        manager.api.client.get = mock.Mock(return_value=(200, {}))
        valid_extra_specs = {'test': 'test'}
        share_type = share_types.ShareType(mock.Mock(),
                                           {'extra_specs': valid_extra_specs,
                                            'name': 'test'},
                                           loaded=True)

        actual_result = share_type.get_keys()

        self.assertEqual(actual_result, valid_extra_specs)
        self.assertEqual(manager.api.client.get.call_count, 0)

    @ddt.data({'prefer_resource_data': True,
               'resource_extra_specs': {}},
              {'prefer_resource_data': False,
               'resource_extra_specs': {'fake': 'fake'}},
              {'prefer_resource_data': False,
              'resource_extra_specs': {}})
    @ddt.unpack
    def test_get_keys_from_api(self, prefer_resource_data,
                               resource_extra_specs):
        manager = mock.Mock()
        valid_extra_specs = {'test': 'test'}
        manager.api.client.get = mock.Mock(
            return_value=(200, {'extra_specs': valid_extra_specs}))
        info = {
            'name': 'test',
            'uuid': 'fake',
            'extra_specs': resource_extra_specs
        }
        share_type = share_types.ShareType(manager, info, loaded=True)

        actual_result = share_type.get_keys(prefer_resource_data)

        self.assertEqual(actual_result, valid_extra_specs)
        self.assertEqual(manager.api.client.get.call_count, 1)
