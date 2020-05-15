# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
from requests import Response
import six

from cinderclient import api_versions
from cinderclient.apiclient import base as common_base
from cinderclient import base
from cinderclient import exceptions
from cinderclient.v3 import client
from cinderclient.v3 import volumes

from cinderclient.tests.unit import test_utils
from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes


cs = fakes.FakeClient()


REQUEST_ID = 'req-test-request-id'


def create_response_obj_with_header():
    resp = Response()
    resp.headers['x-openstack-request-id'] = REQUEST_ID
    resp.headers['Etag'] = 'd5103bf7b26ff0310200d110da3ed186'
    resp.status_code = 200
    return resp


class BaseTest(utils.TestCase):

    def test_resource_repr(self):
        r = base.Resource(None, dict(foo="bar", baz="spam"))
        self.assertEqual("<Resource baz=spam, foo=bar>", repr(r))
        self.assertNotIn("x_openstack_request_ids", repr(r))

    def test_add_non_ascii_attr_to_resource(self):
        info = {'gigabytes_тест': -1,
                'volumes_тест': -1,
                'id': 'admin'}

        res = base.Resource(None, info)

        for key, value in info.items():
            self.assertEqual(value, getattr(res, key, None))

    def test_getid(self):
        self.assertEqual(4, base.getid(4))

        class TmpObject(object):
            id = 4
        self.assertEqual(4, base.getid(TmpObject))

    def test_eq(self):
        # Two resources with same ID: never equal if their info is not equal
        r1 = base.Resource(None, {'id': 1, 'name': 'hi'})
        r2 = base.Resource(None, {'id': 1, 'name': 'hello'})
        self.assertNotEqual(r1, r2)

        # Two resources with same ID: equal if their info is equal
        r1 = base.Resource(None, {'id': 1, 'name': 'hello'})
        r2 = base.Resource(None, {'id': 1, 'name': 'hello'})
        self.assertEqual(r1, r2)

        # Two resources of different types: never equal
        r1 = base.Resource(None, {'id': 1})
        r2 = volumes.Volume(None, {'id': 1})
        self.assertNotEqual(r1, r2)

        # Two resources with no ID: equal if their info is equal
        r1 = base.Resource(None, {'name': 'joe', 'age': 12})
        r2 = base.Resource(None, {'name': 'joe', 'age': 12})
        self.assertEqual(r1, r2)

    def test_findall_invalid_attribute(self):
        # Make sure findall with an invalid attribute doesn't cause errors.
        # The following should not raise an exception.
        cs.volumes.findall(vegetable='carrot')

        # However, find() should raise an error
        self.assertRaises(exceptions.NotFound,
                          cs.volumes.find,
                          vegetable='carrot')

    def test_to_dict(self):
        r1 = base.Resource(None, {'id': 1, 'name': 'hi'})
        self.assertEqual({'id': 1, 'name': 'hi'}, r1.to_dict())

    def test_resource_object_with_request_ids(self):
        resp_obj = create_response_obj_with_header()
        r = base.Resource(None, {"name": "1"}, resp=resp_obj)
        self.assertEqual([REQUEST_ID], r.request_ids)

    def test_api_version(self):
        version = api_versions.APIVersion('3.1')
        api = client.Client(api_version=version)
        manager = test_utils.FakeManagerWithApi(api)
        r1 = base.Resource(manager, {'id': 1})
        self.assertEqual(version, r1.api_version)

    @mock.patch('cinderclient.utils.unicode_key_value_to_string',
                side_effect=lambda x: x)
    def test_build_list_url_failed(self, fake_encode):
        # NOTE(mdovgal): This test is reasonable only for py27 version,
        #                due to issue with parse.urlencode method only in py27
        if six.PY2:
            arguments = dict(resource_type = 'volumes',
                             search_opts = {'all_tenants': 1,
                                            'name': u'ффф'})
            manager = base.Manager(None)
            self.assertRaises(UnicodeEncodeError,
                              manager._build_list_url,
                              **arguments)

    def test__list_no_link(self):
        api = mock.Mock()
        api.client.get.return_value = (mock.sentinel.resp,
                                       {'resp_keys': [{'name': '1'}]})
        manager = test_utils.FakeManager(api)
        res = manager._list(mock.sentinel.url, 'resp_keys')
        api.client.get.assert_called_once_with(mock.sentinel.url)
        result = [r.name for r in res]
        self.assertListEqual(['1'], result)

    def test__list_with_link(self):
        api = mock.Mock()
        api.client.get.side_effect = [
            (mock.sentinel.resp,
             {'resp_keys': [{'name': '1'}],
              'resp_keys_links': [{'rel': 'next', 'href': mock.sentinel.u2}]}),
            (mock.sentinel.resp,
             {'resp_keys': [{'name': '2'}],
              'resp_keys_links': [{'rel': 'next', 'href': mock.sentinel.u3}]}),
            (mock.sentinel.resp,
             {'resp_keys': [{'name': '3'}],
              'resp_keys_links': [{'rel': 'next', 'href': None}]}),
        ]
        manager = test_utils.FakeManager(api)
        res = manager._list(mock.sentinel.url, 'resp_keys')
        api.client.get.assert_has_calls([mock.call(mock.sentinel.url),
                                         mock.call(mock.sentinel.u2),
                                         mock.call(mock.sentinel.u3)])
        result = [r.name for r in res]
        self.assertListEqual(['1', '2', '3'], result)


class ListWithMetaTest(utils.TestCase):
    def test_list_with_meta(self):
        resp = create_response_obj_with_header()
        obj = common_base.ListWithMeta([], resp)
        self.assertEqual([], obj)
        # Check request_ids attribute is added to obj
        self.assertTrue(hasattr(obj, 'request_ids'))
        self.assertEqual([REQUEST_ID], obj.request_ids)


class DictWithMetaTest(utils.TestCase):
    def test_dict_with_meta(self):
        resp = create_response_obj_with_header()
        obj = common_base.DictWithMeta([], resp)
        self.assertEqual({}, obj)
        # Check request_ids attribute is added to obj
        self.assertTrue(hasattr(obj, 'request_ids'))
        self.assertEqual([REQUEST_ID], obj.request_ids)


class TupleWithMetaTest(utils.TestCase):
    def test_tuple_with_meta(self):
        resp = create_response_obj_with_header()
        obj = common_base.TupleWithMeta((), resp)
        self.assertEqual((), obj)
        # Check request_ids attribute is added to obj
        self.assertTrue(hasattr(obj, 'request_ids'))
        self.assertEqual([REQUEST_ID], obj.request_ids)
