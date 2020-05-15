# Copyright 2015 Mirantis Inc.
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

import ddt

from manilaclient.tests.functional import base


@ddt.ddt
class SharesMetadataReadWriteTest(base.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(SharesMetadataReadWriteTest, cls).setUpClass()
        cls.share = cls.create_share(
            client=cls.get_user_client(),
            cleanup_in_class=True)

    def test_set_metadata_in_share_creation(self):
        md = {"key1": "value1", "key2": "value2"}

        # Create share with metadata
        share = self.create_share(
            metadata=md, cleanup_in_class=False, client=self.get_user_client())

        # Read share metadata
        metadata = self.user_client.get_share_metadata(share["id"])

        # Verify share metadata
        self.assertEqual(2, len(metadata))
        self.assertIn('key1', metadata)
        self.assertIn('key2', metadata)
        self.assertEqual(md['key1'], metadata['key1'])
        self.assertEqual(md['key2'], metadata['key2'])

    def test_set_and_get_metadata(self):
        # Create share
        share = self.create_share(
            cleanup_in_class=False, client=self.get_user_client())

        # Set share metadata
        md = {"key3": "value3", "key4": "value4"}
        self.user_client.set_share_metadata(share["id"], md)

        # Read share metadata
        metadata = self.user_client.get_share_metadata(share["id"])

        # Verify share metadata
        self.assertEqual(2, len(metadata))
        self.assertIn('key3', metadata)
        self.assertIn('key4', metadata)
        self.assertEqual(md['key3'], metadata['key3'])
        self.assertEqual(md['key4'], metadata['key4'])

    def test_set_and_delete_metadata(self):
        # Create share
        share = self.create_share(
            cleanup_in_class=False, client=self.get_user_client())

        # Set share metadata
        md = {"key3": "value3", "key4": "value4"}
        self.user_client.set_share_metadata(share["id"], md)

        # Unset share metadata
        self.user_client.unset_share_metadata(share["id"], list(md.keys()))

        # Verify deletion of share metadata
        metadata = self.user_client.get_share_metadata(share["id"])
        self.assertEqual({}, metadata)

    def test_set_and_add_metadata(self):
        md = {'key5': 'value5'}

        # Create share with metadata
        share = self.create_share(
            metadata=md, cleanup_in_class=False, client=self.get_user_client())

        # Set share metadata
        self.user_client.set_share_metadata(share["id"], {'key6': 'value6'})
        self.user_client.set_share_metadata(share["id"], {'key7': 'value7'})

        # Read share metadata
        metadata = self.user_client.get_share_metadata(share["id"])

        # Verify share metadata
        self.assertEqual(3, len(metadata))
        for i in (5, 6, 7):
            key = 'key%s' % i
            self.assertIn(key, metadata)
            self.assertEqual('value%s' % i, metadata[key])

    def test_set_and_replace_metadata(self):
        md = {'key8': 'value8'}

        # Create share with metadata
        share = self.create_share(
            metadata=md, cleanup_in_class=False, client=self.get_user_client())

        # Set share metadata
        self.user_client.set_share_metadata(share["id"], {'key9': 'value9'})

        # Replace all existing share metadata
        self.user_client.update_all_share_metadata(
            share["id"], {'key10': 'value10'})

        # Read share metadata
        metadata = self.user_client.get_share_metadata(share["id"])

        # Verify share metadata
        self.assertEqual(1, len(metadata))
        self.assertIn('key10', metadata)
        self.assertEqual('value10', metadata['key10'])

    @ddt.data(
        {"k": "value"},
        {"k" * 255: "value"},
        {"key": "v"},
        {"key": "v" * 1023})
    def test_set_metadata_min_max_sizes_of_keys_and_values(self, metadata):
        # Set share metadata
        self.user_client.set_share_metadata(self.share["id"], metadata)

        # Read share metadata
        get = self.user_client.get_share_metadata(self.share["id"])

        # Verify share metadata
        key = list(metadata.keys())[0]
        self.assertIn(key, get)
        self.assertEqual(metadata[key], get[key])

    @ddt.data(
        {"k": "value"},
        {"k" * 255: "value"},
        {"key": "v"},
        {"key": "v" * 1023})
    def test_update_metadata_min_max_sizes_of_keys_and_values(self, metadata):
        # Update share metadata
        self.user_client.update_all_share_metadata(self.share["id"], metadata)

        # Read share metadata
        get = self.user_client.get_share_metadata(self.share["id"])

        # Verify share metadata
        self.assertEqual(len(metadata), len(get))
        for key in metadata:
            self.assertIn(key, get)
            self.assertEqual(metadata[key], get[key])
