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

from oslotest import base as test_base

from oslo_context import context
from oslo_context import fixture


class ClearRequestContextTest(test_base.BaseTestCase):

    # def setUp(self):
    #     super(ContextTest, self).setUp()
    #     self.useFixture(fixture.ClearRequestContext())

    def test_store_current(self):
        # By default a new context is stored.
        ctx = context.RequestContext()
        self.assertIs(context.get_current(), ctx)
        fixture.ClearRequestContext()._remove_cached_context()
        self.assertIsNone(context.get_current())

    def test_store_current_resets_correctly(self):
        # By default a new context is stored.
        ctx = context.RequestContext()

        # the use of the fixture should put us in a reset state, not
        # doing so is a bug because when this fixture is consumed by
        # other test suites there is no guaruntee that all tests use
        # this fixture.
        self.useFixture(fixture.ClearRequestContext())
        self.assertIsNone(context.get_current())

        ctx = context.RequestContext()
        self.assertIs(context.get_current(), ctx)
        fixture.ClearRequestContext()._remove_cached_context()
        self.assertIsNone(context.get_current())
