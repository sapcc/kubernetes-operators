# Copyright (c) 2013 The Johns Hopkins University/Applied Physics Laboratory
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

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes
from cinderclient.v2.volume_encryption_types import VolumeEncryptionType

cs = fakes.FakeClient()

FAKE_ENCRY_TYPE = {'provider': 'Test',
                   'key_size': None,
                   'cipher': None,
                   'control_location': None,
                   'volume_type_id': '65922555-7bc0-47e9-8d88-c7fdbcac4781',
                   'encryption_id': '62daf814-cf9b-401c-8fc8-f84d7850fb7c'}


class VolumeEncryptionTypesTest(utils.TestCase):
    """
    Test suite for the Volume Encryption Types Resource and Manager.
    """

    def test_list(self):
        """
        Unit test for VolumeEncryptionTypesManager.list

        Verify that a series of GET requests are made:
        - one GET request for the list of volume types
        - one GET request per volume type for encryption type information

        Verify that all returned information is :class: VolumeEncryptionType
        """
        encryption_types = cs.volume_encryption_types.list()
        cs.assert_called_anytime('GET', '/types?is_public=None')
        cs.assert_called_anytime('GET', '/types/2/encryption')
        cs.assert_called_anytime('GET', '/types/1/encryption')
        for encryption_type in encryption_types:
            self.assertIsInstance(encryption_type, VolumeEncryptionType)
            self._assert_request_id(encryption_type)

    def test_get(self):
        """
        Unit test for VolumeEncryptionTypesManager.get

        Verify that one GET request is made for the volume type encryption
        type information. Verify that returned information is :class:
        VolumeEncryptionType
        """
        encryption_type = cs.volume_encryption_types.get(1)
        cs.assert_called('GET', '/types/1/encryption')
        self.assertIsInstance(encryption_type, VolumeEncryptionType)
        self._assert_request_id(encryption_type)

    def test_get_no_encryption(self):
        """
        Unit test for VolumeEncryptionTypesManager.get

        Verify that a request on a volume type with no associated encryption
        type information returns a VolumeEncryptionType with no attributes.
        """
        encryption_type = cs.volume_encryption_types.get(2)
        self.assertIsInstance(encryption_type, VolumeEncryptionType)
        self.assertFalse(hasattr(encryption_type, 'id'),
                         'encryption type has an id')
        self._assert_request_id(encryption_type)

    def test_create(self):
        """
        Unit test for VolumeEncryptionTypesManager.create

        Verify that one POST request is made for the encryption type creation.
        Verify that encryption type creation returns a VolumeEncryptionType.
        """
        result = cs.volume_encryption_types.create(2, {'provider': 'Test',
                                                       'key_size': None,
                                                       'cipher': None,
                                                       'control_location':
                                                       None})
        cs.assert_called('POST', '/types/2/encryption')
        self.assertIsInstance(result, VolumeEncryptionType)
        self._assert_request_id(result)

    def test_update(self):
        """
        Unit test for VolumeEncryptionTypesManager.update

        Verify that one PUT request is made for encryption type update
        Verify that an empty encryption-type update returns the original
        encryption-type information.
        """
        expected = {'id': 1, 'volume_type_id': 1, 'provider': 'test',
                    'cipher': 'test', 'key_size': 1,
                    'control_location': 'front-end'}
        result = cs.volume_encryption_types.update(1, {})
        cs.assert_called('PUT', '/types/1/encryption/provider')
        self.assertEqual(expected, result,
                         "empty update must yield original data")
        self._assert_request_id(result)

    def test_delete(self):
        """
        Unit test for VolumeEncryptionTypesManager.delete

        Verify that one DELETE request is made for encryption type deletion
        Verify that encryption type deletion returns None
        """
        result = cs.volume_encryption_types.delete(1)
        cs.assert_called('DELETE', '/types/1/encryption/provider')
        self.assertIsInstance(result, tuple)
        self.assertEqual(202, result[0].status_code)
        self._assert_request_id(result)

    def test___repr__(self):
        """
        Unit test for VolumeEncryptionTypes.__repr__

        Verify that one encryption type can be printed
        """
        encry_type = VolumeEncryptionType(None, FAKE_ENCRY_TYPE)
        self.assertEqual(
            "<VolumeEncryptionType: %s>" % FAKE_ENCRY_TYPE['encryption_id'],
            repr(encry_type))
