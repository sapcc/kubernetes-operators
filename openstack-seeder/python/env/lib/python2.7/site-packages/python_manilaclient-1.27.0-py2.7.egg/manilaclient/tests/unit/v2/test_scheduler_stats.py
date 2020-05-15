# Copyright (c) 2015 Clinton Knight.  All rights reserved.
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

import mock

from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes
from manilaclient.v2 import scheduler_stats


class PoolTest(utils.TestCase):

    def setUp(self):
        super(PoolTest, self).setUp()

        self.name = 'fake_host@fake_backend#fake_pool'
        info = {
            'name': self.name,
            'host': 'fake_host',
            'backend': 'fake_backend',
            'pool': 'fake_pool',
        }
        self.resource_class = scheduler_stats.Pool(manager=self, info=info)

    def test_get_repr_of_share_server(self):
        self.assertEqual('<Pool: %s>' % self.name, repr(self.resource_class))


class PoolManagerTest(utils.TestCase):

    def setUp(self):
        super(PoolManagerTest, self).setUp()
        self.manager = scheduler_stats.PoolManager(fakes.FakeClient())

    @mock.patch.object(scheduler_stats.PoolManager, '_list', mock.Mock())
    def test_list(self):
        self.manager.list(detailed=False)
        self.manager._list.assert_called_once_with(
            scheduler_stats.RESOURCES_PATH,
            scheduler_stats.RESOURCES_NAME)

    @mock.patch.object(scheduler_stats.PoolManager, '_list', mock.Mock())
    def test_list_detail(self):
        self.manager.list()
        self.manager._list.assert_called_once_with(
            scheduler_stats.RESOURCES_PATH + '/detail',
            scheduler_stats.RESOURCES_NAME)

    @mock.patch.object(scheduler_stats.PoolManager, '_list', mock.Mock())
    def test_list_with_one_search_opt(self):
        host = 'fake_host'
        query_string = "?host=%s" % host

        self.manager.list(detailed=False, search_opts={'host': host})

        self.manager._list.assert_called_once_with(
            scheduler_stats.RESOURCES_PATH + query_string,
            scheduler_stats.RESOURCES_NAME)

    @mock.patch.object(scheduler_stats.PoolManager, '_list', mock.Mock())
    def test_list_detail_with_two_search_opts(self):
        host = 'fake_host'
        backend = 'fake_backend'
        query_string = "?backend=%s&host=%s" % (backend, host)

        self.manager.list(search_opts={'host': host, 'backend': backend})

        self.manager._list.assert_called_once_with(
            scheduler_stats.RESOURCES_PATH + '/detail' + query_string,
            scheduler_stats.RESOURCES_NAME)
