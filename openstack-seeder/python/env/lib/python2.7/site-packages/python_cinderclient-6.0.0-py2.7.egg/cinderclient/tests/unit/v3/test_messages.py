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
from six.moves.urllib import parse

from cinderclient import api_versions
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes


@ddt.ddt
class MessagesTest(utils.TestCase):

    def test_list_messages(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.3'))
        cs.messages.list()
        cs.assert_called('GET', '/messages')

    @ddt.data('id', 'id:asc', 'id:desc', 'resource_type', 'event_id',
              'resource_uuid', 'message_level', 'guaranteed_until',
              'request_id')
    def test_list_messages_with_sort(self, sort_string):
        cs = fakes.FakeClient(api_versions.APIVersion('3.5'))
        cs.messages.list(sort=sort_string)
        cs.assert_called('GET', '/messages?sort=%s' % parse.quote(sort_string))

    @ddt.data('id', 'resource_type', 'event_id', 'resource_uuid',
              'message_level', 'guaranteed_until', 'request_id')
    def test_list_messages_with_filters(self, filter_string):
        cs = fakes.FakeClient(api_versions.APIVersion('3.5'))
        cs.messages.list(search_opts={filter_string: 'value'})
        cs.assert_called('GET', '/messages?%s=value' % parse.quote(
            filter_string))

    @ddt.data('fake', 'fake:asc', 'fake:desc')
    def test_list_messages_with_invalid_sort(self, sort_string):
        cs = fakes.FakeClient(api_versions.APIVersion('3.5'))
        self.assertRaises(ValueError, cs.messages.list, sort=sort_string)

    def test_get_messages(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.3'))
        fake_id = '1234'
        cs.messages.get(fake_id)
        cs.assert_called('GET', '/messages/%s' % fake_id)

    def test_delete_messages(self):
        cs = fakes.FakeClient(api_versions.APIVersion('3.3'))
        fake_id = '1234'
        cs.messages.delete(fake_id)
        cs.assert_called('DELETE', '/messages/%s' % fake_id)
