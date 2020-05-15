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

import fixtures

from oslo_context import context


class ClearRequestContext(fixtures.Fixture):
    """Clears any cached RequestContext

    This resets RequestContext at the beginning and end of tests that
    use this fixture to ensure that we have a clean slate for running
    tests, and that we leave a clean slate for other tests that might
    run later in the same process.
    """

    def setUp(self):
        super(ClearRequestContext, self).setUp()
        # we need to clear both when we start, and when we finish,
        # because there might be other tests running that don't handle
        # this correctly.
        self._remove_cached_context()
        self.addCleanup(self._remove_cached_context)

    def _remove_cached_context(self):
        """Remove the thread-local context stored in the module."""
        try:
            del context._request_store.context
        except AttributeError:
            pass
