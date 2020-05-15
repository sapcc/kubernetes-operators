# Copyright (C) 2015 Hewlett-Packard Development Company, L.P.
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

from cinderclient.v2.pools import Pool

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes

cs = fakes.FakeClient()


class PoolsTest(utils.TestCase):

    def test_get_pool_stats(self):
        sl = cs.pools.list()
        cs.assert_called('GET', '/scheduler-stats/get_pools')
        self._assert_request_id(sl)
        for s in sl:
            self.assertIsInstance(s, Pool)
            self.assertTrue(hasattr(s, "name"))
            self.assertFalse(hasattr(s, "capabilities"))
            # basic list should not have volume_backend_name (or any other
            # entries from capabilities)
            self.assertFalse(hasattr(s, "volume_backend_name"))

    def test_get_detail_pool_stats(self):
        sl = cs.pools.list(detailed=True)
        self._assert_request_id(sl)
        cs.assert_called('GET', '/scheduler-stats/get_pools?detail=True')
        for s in sl:
            self.assertIsInstance(s, Pool)
            self.assertTrue(hasattr(s, "name"))
            self.assertFalse(hasattr(s, "capabilities"))
            # detail list should have a volume_backend_name (from capabilities)
            self.assertTrue(hasattr(s, "volume_backend_name"))
