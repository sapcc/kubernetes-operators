# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Author: Kiall Mac Innes <kiall@hp.com>
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
import uuid

from designateclient.tests import base


class CrudMixin(object):
    path_prefix = None

    def new_ref(self, **kwargs):
        kwargs.setdefault('id', uuid.uuid4().hex)
        return kwargs

    def stub_entity(self, method, parts=None, entity=None, id=None, **kwargs):
        if entity:
            kwargs['json'] = entity

        if not parts:
            parts = [self.RESOURCE]

            if self.path_prefix:
                parts.insert(0, self.path_prefix)

        if id:
            if not parts:
                parts = []

            parts.append(id)

        self.stub_url(method, parts=parts, **kwargs)

    def assertList(self, expected, actual):
        self.assertEqual(len(expected), len(actual))
        for i in expected:
            self.assertIn(i, actual)


class APIV1TestCase(base.APITestCase):
    VERSION = "1"
