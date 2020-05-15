# Copyright 2016 Hewlett Packard Enterprise Development Company LP
#
# Author: Graham Hayes <endre.karlson@hp.com>
#
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

from designateclient import client
from designateclient.v2.utils import parse_query_from_url


class DesignateList(list):

    next_link_criterion = {}
    next_page = False


class V2Controller(client.Controller):

    def _get(self, url, response_key=None, **kwargs):
        resp, body = self.client.session.get(url, **kwargs)

        if response_key is not None:
            data = DesignateList()
            data.extend(body[response_key])

            if 'next' in body.get('links', {}):
                data.next_page = True
                data.next_link_criterion = parse_query_from_url(
                    body['links']['next'])

            return data

        return body
