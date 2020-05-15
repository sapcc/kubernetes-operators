# Copyright 2017 Red Hat
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

import mock

import ddt
import six

from manilaclient.tests.unit import utils
from manilaclient.tests.unit.v2 import fakes as fake
from manilaclient.v2 import messages


class MessageTest(utils.TestCase):

    def setUp(self):
        super(MessageTest, self).setUp()
        self.manager = messages.MessageManager(fake.FakeClient())
        self.message = messages.Message(
            self.manager, {'id': 'fake_id'})
        self.fake_kwargs = {'key': 'value'}

    def test_repr(self):
        result = six.text_type(self.message)

        self.assertEqual('<Message: fake_id>', result)

    def test_delete(self):
        mock_manager_delete = self.mock_object(self.manager, 'delete')

        self.message.delete()

        mock_manager_delete.assert_called_once_with(self.message)


@ddt.ddt
class MessageManagerTest(utils.TestCase):

    def setUp(self):
        super(MessageManagerTest, self).setUp()
        self.manager = messages.MessageManager(fake.FakeClient())

    def test_get(self):
        fake_message = fake.Message()
        mock_get = self.mock_object(
            self.manager, '_get', mock.Mock(return_value=fake_message))

        result = self.manager.get(fake.Message.id)

        self.assertIs(fake_message, result)
        mock_get.assert_called_once_with(
            messages.RESOURCE_PATH % fake.Message.id,
            messages.RESOURCE_NAME)

    def test_list(self):
        fake_message = fake.Message()
        mock_list = self.mock_object(
            self.manager, '_list', mock.Mock(return_value=[fake_message]))

        result = self.manager.list()

        self.assertEqual([fake_message], result)
        mock_list.assert_called_once_with(
            messages.RESOURCES_PATH,
            messages.RESOURCES_NAME)

    @ddt.data(
        ({'action_id': 1, 'resource_type': 'share'},
         '?action_id=1&resource_type=share'),
        ({'action_id': 1}, '?action_id=1'),
    )
    @ddt.unpack
    def test_list_with_filters(self, filters, filters_path):
        fake_message = fake.Message()
        mock_list = self.mock_object(
            self.manager, '_list', mock.Mock(return_value=[fake_message]))

        result = self.manager.list(search_opts=filters)

        self.assertEqual([fake_message], result)
        expected_path = (messages.RESOURCES_PATH + filters_path)
        mock_list.assert_called_once_with(
            expected_path, messages.RESOURCES_NAME)

    @ddt.data('id', 'project_id', 'request_id', 'resource_type', 'action_id',
              'detail_id', 'resource_id', 'message_level', 'expires_at',
              'request_id', 'created_at')
    def test_list_with_sorting(self, key):
        fake_message = fake.Message()
        mock_list = self.mock_object(
            self.manager, '_list', mock.Mock(return_value=[fake_message]))

        result = self.manager.list(sort_dir='asc', sort_key=key)

        self.assertEqual([fake_message], result)
        expected_path = (
            messages.RESOURCES_PATH + '?sort_dir=asc&sort_key=' +
            key)
        mock_list.assert_called_once_with(
            expected_path, messages.RESOURCES_NAME)

    @ddt.data(
        ('name', 'invalid'),
        ('invalid', 'asc'),
    )
    @ddt.unpack
    def test_list_with_invalid_sorting(self, sort_key, sort_dir):
        self.assertRaises(
            ValueError,
            self.manager.list, sort_dir=sort_dir, sort_key=sort_key)

    def test_delete(self):
        mock_delete = self.mock_object(self.manager, '_delete')
        mock_post = self.mock_object(self.manager.api.client, 'post')

        self.manager.delete(fake.Message())

        mock_delete.assert_called_once_with(
            messages.RESOURCE_PATH % fake.Message.id)
        self.assertFalse(mock_post.called)
