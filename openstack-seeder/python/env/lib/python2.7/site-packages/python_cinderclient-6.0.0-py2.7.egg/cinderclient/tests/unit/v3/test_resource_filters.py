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

import ddt

from cinderclient import api_versions
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes

cs = fakes.FakeClient(api_versions.APIVersion('3.33'))


@ddt.ddt
class ResourceFilterTests(utils.TestCase):
    @ddt.data({'resource': None, 'query_url': None},
              {'resource': 'volume', 'query_url': '?resource=volume'},
              {'resource': 'group', 'query_url': '?resource=group'})
    @ddt.unpack
    def test_list_resource_filters(self, resource, query_url):
        cs.resource_filters.list(resource)
        url = '/resource_filters'
        if resource is not None:
            url += query_url
        cs.assert_called('GET', url)
