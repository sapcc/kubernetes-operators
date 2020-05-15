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

import logging

from oslo_log import fixture
from oslotest import base as test_base


class TestSetLevelFixture(test_base.BaseTestCase):

    def test_unset_before(self):
        logger = logging.getLogger('no-such-logger-unset')
        self.assertEqual(logging.NOTSET, logger.level)
        fix = fixture.SetLogLevel(['no-such-logger-unset'], logging.DEBUG)
        with fix:
            self.assertEqual(logging.DEBUG, logger.level)
        self.assertEqual(logging.NOTSET, logger.level)

    def test_set_before(self):
        logger = logging.getLogger('no-such-logger-set')
        logger.setLevel(logging.ERROR)
        self.assertEqual(logging.ERROR, logger.level)
        fix = fixture.SetLogLevel(['no-such-logger-set'], logging.DEBUG)
        with fix:
            self.assertEqual(logging.DEBUG, logger.level)
        self.assertEqual(logging.ERROR, logger.level)
