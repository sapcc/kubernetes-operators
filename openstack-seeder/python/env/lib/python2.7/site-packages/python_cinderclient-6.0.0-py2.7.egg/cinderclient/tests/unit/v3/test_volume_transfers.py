# Copyright 2018 FiberHome Telecommunication Technologies CO.,LTD
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

from cinderclient import api_versions
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v3 import fakes

TRANSFER_URL = 'os-volume-transfer'
TRANSFER_355_URL = 'volume-transfers'

# Create calls need the right version of faked client
v355cs = fakes.FakeClient(api_versions.APIVersion('3.55'))
# Other calls fall back to API extension behavior
v3cs = fakes.FakeClient(api_versions.APIVersion('3.0'))


class VolumeTransfersTest(utils.TestCase):

    def test_create(self):
        vol = v3cs.transfers.create('1234')
        v3cs.assert_called('POST', '/%s' % TRANSFER_URL,
                         body={'transfer': {'volume_id': '1234',
                                            'name': None}})
        self._assert_request_id(vol)

    def test_create_355(self):
        vol = v355cs.transfers.create('1234')
        v355cs.assert_called('POST', '/%s' % TRANSFER_355_URL,
                             body={'transfer': {'volume_id': '1234',
                                                'name': None,
                                                'no_snapshots': False}})
        self._assert_request_id(vol)

    def test_create_without_snapshots(self):
        vol = v355cs.transfers.create('1234', no_snapshots=True)
        v355cs.assert_called('POST', '/%s' % TRANSFER_355_URL,
                             body={'transfer': {'volume_id': '1234',
                                                'name': None,
                                                'no_snapshots': True}})
        self._assert_request_id(vol)

    def _test_get(self, client, expected_url):
        transfer_id = '5678'
        vol = client.transfers.get(transfer_id)
        client.assert_called('GET', '/%s/%s' % (expected_url, transfer_id))
        self._assert_request_id(vol)

    def test_get(self):
        self._test_get(v3cs, TRANSFER_URL)

    def test_get_355(self):
        self._test_get(v355cs, TRANSFER_355_URL)

    def _test_list(self, client, expected_url):
        lst = client.transfers.list()
        client.assert_called('GET', '/%s/detail' % expected_url)
        self._assert_request_id(lst)

    def test_list(self):
        self._test_list(v3cs, TRANSFER_URL)

    def test_list_355(self):
        self._test_list(v355cs, TRANSFER_355_URL)

    def _test_delete(self, client, expected_url):
        url = '/%s/5678' % expected_url
        b = client.transfers.list()[0]
        vol = b.delete()
        client.assert_called('DELETE', url)
        self._assert_request_id(vol)
        vol = client.transfers.delete('5678')
        self._assert_request_id(vol)
        client.assert_called('DELETE', url)
        vol = client.transfers.delete(b)
        client.assert_called('DELETE', url)
        self._assert_request_id(vol)

    def test_delete(self):
        self._test_delete(v3cs, TRANSFER_URL)

    def test_delete_355(self):
        self._test_delete(v355cs, TRANSFER_355_URL)

    def _test_accept(self, client, expected_url):
        transfer_id = '5678'
        auth_key = '12345'
        vol = client.transfers.accept(transfer_id, auth_key)
        client.assert_called(
            'POST',
            '/%s/%s/accept' % (expected_url, transfer_id))
        self._assert_request_id(vol)

    def test_accept(self):
        self._test_accept(v3cs, TRANSFER_URL)

    def test_accept_355(self):
        self._test_accept(v355cs, TRANSFER_355_URL)
