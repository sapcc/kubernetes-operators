# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ddt
import mock

from manilaclient import api_versions
from manilaclient import client
from manilaclient import exceptions
from manilaclient.tests.unit import utils
import manilaclient.v1.client
import manilaclient.v2.client


@ddt.ddt
class ClientTest(utils.TestCase):

    def test_get_client_class_v2(self):
        output = manilaclient.client.get_client_class('2')
        self.assertEqual(output, manilaclient.v2.client.Client)

    def test_get_client_class_unknown(self):
        self.assertRaises(manilaclient.exceptions.UnsupportedVersion,
                          manilaclient.client.get_client_class, '0')

    @ddt.data('1', '1.0')
    def test_init_client_with_string_v1_version(self, version):
        with mock.patch.object(manilaclient.v1.client, 'Client'):
            with mock.patch.object(api_versions, 'APIVersion'):
                api_instance = api_versions.APIVersion.return_value
                api_instance.get_major_version.return_value = '1'

                manilaclient.client.Client(version, 'foo', bar='quuz')

                manilaclient.v1.client.Client.assert_called_once_with(
                    'foo', api_version=api_instance, bar='quuz')
                api_versions.APIVersion.assert_called_once_with('1.0')

    @ddt.data(
        ('2', '2.0'),
        ('2.0', '2.0'),
        ('2.6', '2.6'),
    )
    @ddt.unpack
    def test_init_client_with_string_v2_version(self, provided, expected):
        with mock.patch.object(manilaclient.v2.client, 'Client'):
            with mock.patch.object(api_versions, 'APIVersion'):
                api_instance = api_versions.APIVersion.return_value
                api_instance.get_major_version.return_value = '2'

                manilaclient.client.Client(provided, 'foo', bar='quuz')

                manilaclient.v2.client.Client.assert_called_once_with(
                    'foo', api_version=api_instance, bar='quuz')
                api_versions.APIVersion.assert_called_once_with(expected)

    def test_init_client_with_api_version_instance(self):
        version = manilaclient.API_MAX_VERSION
        with mock.patch.object(manilaclient.v2.client, 'Client'):

            manilaclient.client.Client(version, 'foo', bar='quuz')

            manilaclient.v2.client.Client.assert_called_once_with(
                'foo', api_version=version, bar='quuz')

    @ddt.data(None, '', '3', 'v1', 'v2', 'v1.0', 'v2.0')
    def test_init_client_with_unsupported_version(self, v):
        self.assertRaises(exceptions.UnsupportedVersion, client.Client, v)

    @ddt.data(
        ('1', '1.0'),
        ('1', '2.0'),
        ('1', '2.7'),
        ('1', None),
        ('1.0', '1.0'),
        ('1.0', '2.0'),
        ('1.0', '2.7'),
        ('1.0', None),
        ('2', '1.0'),
        ('2', '2.0'),
        ('2', '2.7'),
        ('2', None),
    )
    @ddt.unpack
    def test_init_client_with_version_parms(self, pos, kw):

        major = int(float(pos))
        pos_av = mock.Mock()
        kw_av = mock.Mock()

        with mock.patch.object(manilaclient.v1.client, 'Client'):
            with mock.patch.object(manilaclient.v2.client, 'Client'):
                with mock.patch.object(api_versions, 'APIVersion'):
                    api_versions.APIVersion.side_effect = [pos_av, kw_av]
                    pos_av.get_major_version.return_value = str(major)

                    if kw is None:
                        manilaclient.client.Client(pos, 'foo')
                        expected_av = pos_av
                    else:
                        manilaclient.client.Client(pos, 'foo', api_version=kw)
                        expected_av = kw_av

                    if int(float(pos)) == 1:
                        expected_client_ver = api_versions.DEPRECATED_VERSION
                        self.assertFalse(manilaclient.v2.client.Client.called)
                        manilaclient.v1.client.Client.assert_has_calls([
                            mock.call('foo', api_version=expected_av)
                        ])
                    else:
                        expected_client_ver = api_versions.MIN_VERSION
                        self.assertFalse(manilaclient.v1.client.Client.called)
                        manilaclient.v2.client.Client.assert_has_calls([
                            mock.call('foo', api_version=expected_av)
                        ])

                    if kw is None:
                        api_versions.APIVersion.assert_called_once_with(
                            expected_client_ver)
                    else:
                        api_versions.APIVersion.assert_has_calls([
                            mock.call(expected_client_ver),
                            mock.call(kw),
                        ])
