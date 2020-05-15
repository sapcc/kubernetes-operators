# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse

import mock
from oslotest import base

import osc_placement.plugin as plugin


class TestPlugin(base.BaseTestCase):
    def test_build_option_parser(self):
        parser = plugin.build_option_parser(argparse.ArgumentParser())

        args = parser.parse_args(['--os-placement-api-version=1.0'])
        self.assertEqual('1.0', args.os_placement_api_version)
        args = parser.parse_args(['--os-placement-api-version', '1.0'])
        self.assertEqual('1.0', args.os_placement_api_version)

    @mock.patch('osc_placement.http.SessionClient')
    def test_make_client(self, mock_session_client):
        instance = mock.Mock(_api_version={'placement': '1.0'})

        plugin.make_client(instance)
        mock_session_client.assert_called_with(
            session=instance.session,
            ks_filter={
                'service_type': 'placement',
                'region_name': instance._region_name,
                'interface': instance.interface
            },
            api_version='1.0'
        )
