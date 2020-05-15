# Copyright (c) 2016 Red Hat Inc.
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

from cinderclient import api_versions
from cinderclient import exceptions as exc
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes
import ddt


cs = fakes.FakeClient(api_version=api_versions.APIVersion('3.7'))


@ddt.ddt
class ClusterTest(utils.TestCase):
    def _check_fields_present(self, clusters, detailed=False):
        expected_keys = {'name', 'binary', 'state', 'status'}

        if detailed:
            expected_keys.update(('num_hosts', 'num_down_hosts',
                                  'last_heartbeat', 'disabled_reason',
                                  'created_at', 'updated_at'))

        for cluster in clusters:
            self.assertEqual(expected_keys, set(cluster.to_dict()))

    def _assert_call(self, base_url, detailed, params=None, method='GET',
                     body=None):
        url = base_url
        if detailed:
            url += '/detail'
        if params:
            url += '?' + params
        if body:
            cs.assert_called(method, url, body)
        else:
            cs.assert_called(method, url)

    @ddt.data(True, False)
    def test_clusters_list(self, detailed):
        lst = cs.clusters.list(detailed=detailed)
        self._assert_call('/clusters', detailed)
        self.assertEqual(3, len(lst))
        self._assert_request_id(lst)
        self._check_fields_present(lst, detailed)

    @ddt.data(True, False)
    def test_clusters_list_pre_version(self, detailed):
        pre_cs = fakes.FakeClient(api_version=
                                  api_versions.APIVersion('3.6'))
        self.assertRaises(exc.VersionNotFoundForAPIMethod,
                          pre_cs.clusters.list, detailed=detailed)

    @ddt.data(True, False)
    def test_cluster_list_name(self, detailed):
        lst = cs.clusters.list(name='cluster1@lvmdriver-1',
                               detailed=detailed)
        self._assert_call('/clusters', detailed,
                          'name=cluster1@lvmdriver-1')
        self.assertEqual(1, len(lst))
        self._assert_request_id(lst)
        self._check_fields_present(lst, detailed)

    @ddt.data(True, False)
    def test_clusters_list_binary(self, detailed):
        lst = cs.clusters.list(binary='cinder-volume', detailed=detailed)
        self._assert_call('/clusters', detailed, 'binary=cinder-volume')
        self.assertEqual(2, len(lst))
        self._assert_request_id(lst)
        self._check_fields_present(lst, detailed)

    @ddt.data(True, False)
    def test_clusters_list_is_up(self, detailed):
        lst = cs.clusters.list(is_up=True, detailed=detailed)
        self._assert_call('/clusters', detailed, 'is_up=True')
        self.assertEqual(2, len(lst))
        self._assert_request_id(lst)
        self._check_fields_present(lst, detailed)

    @ddt.data(True, False)
    def test_clusters_list_disabled(self, detailed):
        lst = cs.clusters.list(disabled=True, detailed=detailed)
        self._assert_call('/clusters', detailed, 'disabled=True')
        self.assertEqual(1, len(lst))
        self._assert_request_id(lst)
        self._check_fields_present(lst, detailed)

    @ddt.data(True, False)
    def test_clusters_list_num_hosts(self, detailed):
        lst = cs.clusters.list(num_hosts=1, detailed=detailed)
        self._assert_call('/clusters', detailed, 'num_hosts=1')
        self.assertEqual(1, len(lst))
        self._assert_request_id(lst)
        self._check_fields_present(lst, detailed)

    @ddt.data(True, False)
    def test_clusters_list_num_down_hosts(self, detailed):
        lst = cs.clusters.list(num_down_hosts=2, detailed=detailed)
        self._assert_call('/clusters', detailed, 'num_down_hosts=2')
        self.assertEqual(2, len(lst))
        self._assert_request_id(lst)
        self._check_fields_present(lst, detailed)

    def test_cluster_show(self):
        result = cs.clusters.show('1')
        self._assert_call('/clusters/1', False)
        self._assert_request_id(result)
        self._check_fields_present([result], True)

    def test_cluster_enable(self):
        body = {'binary': 'cinder-volume', 'name': 'cluster@lvmdriver-1'}
        result = cs.clusters.update(body['name'], body['binary'], False,
                                    disabled_reason='is ignored')
        self._assert_call('/clusters/enable', False, method='PUT', body=body)
        self._assert_request_id(result)
        self._check_fields_present([result], False)

    def test_cluster_disable(self):
        body = {'binary': 'cinder-volume', 'name': 'cluster@lvmdriver-1',
                'disabled_reason': 'is passed'}
        result = cs.clusters.update(body['name'], body['binary'], True,
                                    body['disabled_reason'])
        self._assert_call('/clusters/disable', False, method='PUT', body=body)
        self._assert_request_id(result)
        self._check_fields_present([result], False)
