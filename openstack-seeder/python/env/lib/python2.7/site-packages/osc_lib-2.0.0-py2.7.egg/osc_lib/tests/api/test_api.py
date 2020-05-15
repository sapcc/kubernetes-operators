#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

"""Base API Library Tests"""

from keystoneauth1 import exceptions as ksa_exceptions
from keystoneauth1 import session

from osc_lib.api import api
from osc_lib import exceptions
from osc_lib.tests.api import fakes as api_fakes


class TestBaseAPIDefault(api_fakes.TestSession):

    def setUp(self):
        super(TestBaseAPIDefault, self).setUp()
        self.api = api.BaseAPI()

    def test_baseapi_request_no_url(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )
        self.assertRaises(
            ksa_exceptions.EndpointNotFound,
            self.api._request,
            'GET',
            '',
        )
        self.assertIsNotNone(self.api.session)
        self.assertNotEqual(self.sess, self.api.session)

    def test_baseapi_request_url(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )
        ret = self.api._request('GET', self.BASE_URL + '/qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())
        self.assertIsNotNone(self.api.session)
        self.assertNotEqual(self.sess, self.api.session)

    def test_baseapi_request_url_path(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )
        self.assertRaises(
            ksa_exceptions.EndpointNotFound,
            self.api._request,
            'GET',
            '/qaz',
        )
        self.assertIsNotNone(self.api.session)
        self.assertNotEqual(self.sess, self.api.session)

    def test_baseapi_request_session(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )
        ret = self.api._request(
            'GET',
            self.BASE_URL + '/qaz',
            session=self.sess,
        )
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())
        self.assertIsNotNone(self.api.session)
        self.assertNotEqual(self.sess, self.api.session)


class TestBaseAPIEndpointArg(api_fakes.TestSession):

    def test_baseapi_endpoint_no_endpoint(self):
        x_api = api.BaseAPI(
            session=self.sess,
        )
        self.assertIsNotNone(x_api.session)
        self.assertEqual(self.sess, x_api.session)
        self.assertIsNone(x_api.endpoint)

        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )

        # Normal url
        self.assertRaises(
            ksa_exceptions.EndpointNotFound,
            x_api._request,
            'GET',
            '/qaz',
        )

        # No leading '/' url
        self.assertRaises(
            ksa_exceptions.EndpointNotFound,
            x_api._request,
            'GET',
            'qaz',
        )

        # Extra leading '/' url
        self.assertRaises(
            ksa_exceptions.connection.UnknownConnectionError,
            x_api._request,
            'GET',
            '//qaz',
        )

    def test_baseapi_endpoint_no_extra(self):
        x_api = api.BaseAPI(
            session=self.sess,
            endpoint=self.BASE_URL,
        )
        self.assertIsNotNone(x_api.session)
        self.assertEqual(self.sess, x_api.session)
        self.assertEqual(self.BASE_URL, x_api.endpoint)

        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )

        # Normal url
        ret = x_api._request('GET', '/qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())

        # No leading '/' url
        ret = x_api._request('GET', 'qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())

        # Extra leading '/' url
        ret = x_api._request('GET', '//qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())

    def test_baseapi_endpoint_extra(self):
        x_api = api.BaseAPI(
            session=self.sess,
            endpoint=self.BASE_URL + '/',
        )
        self.assertIsNotNone(x_api.session)
        self.assertEqual(self.sess, x_api.session)
        self.assertEqual(self.BASE_URL, x_api.endpoint)

        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )

        # Normal url
        ret = x_api._request('GET', '/qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())

        # No leading '/' url
        ret = x_api._request('GET', 'qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())

        # Extra leading '/' url
        ret = x_api._request('GET', '//qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())


class TestBaseAPIArgs(api_fakes.TestSession):

    def setUp(self):
        super(TestBaseAPIArgs, self).setUp()
        self.api = api.BaseAPI(
            session=self.sess,
            endpoint=self.BASE_URL,
        )

    def test_baseapi_request_url_path(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )
        ret = self.api._request('GET', '/qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())
        self.assertIsNotNone(self.api.session)
        self.assertEqual(self.sess, self.api.session)

    def test_baseapi_request_session(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=200,
        )
        new_session = session.Session()
        ret = self.api._request('GET', '/qaz', session=new_session)
        self.assertEqual(api_fakes.RESP_ITEM_1, ret.json())
        self.assertIsNotNone(self.api.session)
        self.assertNotEqual(new_session, self.api.session)


class TestBaseAPICreate(api_fakes.TestSession):

    def setUp(self):
        super(TestBaseAPICreate, self).setUp()
        self.api = api.BaseAPI(
            session=self.sess,
            endpoint=self.BASE_URL,
        )

    def test_baseapi_create_post(self):
        self.requests_mock.register_uri(
            'POST',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=202,
        )
        ret = self.api.create('qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)

    def test_baseapi_create_put(self):
        self.requests_mock.register_uri(
            'PUT',
            self.BASE_URL + '/qaz',
            json=api_fakes.RESP_ITEM_1,
            status_code=202,
        )
        ret = self.api.create('qaz', method='PUT')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)

    def test_baseapi_delete(self):
        self.requests_mock.register_uri(
            'DELETE',
            self.BASE_URL + '/qaz',
            status_code=204,
        )
        ret = self.api.delete('qaz')
        self.assertEqual(204, ret.status_code)


class TestBaseAPIFind(api_fakes.TestSession):

    def setUp(self):
        super(TestBaseAPIFind, self).setUp()
        self.api = api.BaseAPI(
            session=self.sess,
            endpoint=self.BASE_URL,
        )

    def test_baseapi_find(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz/1',
            json={'qaz': api_fakes.RESP_ITEM_1},
            status_code=200,
        )
        ret = self.api.find('qaz', '1')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz/1',
            status_code=404,
        )
        self.assertRaises(
            exceptions.NotFound,
            self.api.find,
            'qaz',
            '1')

    def test_baseapi_find_attr_by_id(self):

        # All first requests (by name) will fail in this test
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?name=1',
            json={'qaz': []},
            status_code=200,
        )
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?id=1',
            json={'qaz': [api_fakes.RESP_ITEM_1]},
            status_code=200,
        )
        ret = self.api.find_attr('qaz', '1')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)

        # value not found
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?name=0',
            json={'qaz': []},
            status_code=200,
        )
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?id=0',
            json={'qaz': []},
            status_code=200,
        )
        self.assertRaises(
            exceptions.CommandError,
            self.api.find_attr,
            'qaz',
            '0',
        )

        # Attribute other than 'name'
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?status=UP',
            json={'qaz': [api_fakes.RESP_ITEM_1]},
            status_code=200,
        )
        ret = self.api.find_attr('qaz', 'UP', attr='status')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)
        ret = self.api.find_attr('qaz', value='UP', attr='status')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)

    def test_baseapi_find_attr_by_name(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?name=alpha',
            json={'qaz': [api_fakes.RESP_ITEM_1]},
            status_code=200,
        )
        ret = self.api.find_attr('qaz', 'alpha')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)

        # value not found
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?name=0',
            json={'qaz': []},
            status_code=200,
        )
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?id=0',
            json={'qaz': []},
            status_code=200,
        )
        self.assertRaises(
            exceptions.CommandError,
            self.api.find_attr,
            'qaz',
            '0',
        )

        # Attribute other than 'name'
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?status=UP',
            json={'qaz': [api_fakes.RESP_ITEM_1]},
            status_code=200,
        )
        ret = self.api.find_attr('qaz', 'UP', attr='status')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)
        ret = self.api.find_attr('qaz', value='UP', attr='status')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)

    def test_baseapi_find_attr_path_resource(self):

        # Test resource different than path
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/wsx?name=1',
            json={'qaz': []},
            status_code=200,
        )
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/wsx?id=1',
            json={'qaz': [api_fakes.RESP_ITEM_1]},
            status_code=200,
        )
        ret = self.api.find_attr('wsx', '1', resource='qaz')
        self.assertEqual(api_fakes.RESP_ITEM_1, ret)

    def test_baseapi_find_bulk_none(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.find_bulk('qaz')
        self.assertEqual(api_fakes.LIST_RESP, ret)
        # Verify headers arg does not interfere
        ret = self.api.find_bulk('qaz', headers={})
        self.assertEqual(api_fakes.LIST_RESP, ret)

    def test_baseapi_find_bulk_one(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.find_bulk('qaz', id='1')
        self.assertEqual([api_fakes.LIST_RESP[0]], ret)
        # Verify headers arg does not interfere with search
        ret = self.api.find_bulk('qaz', id='1', headers={})
        self.assertEqual([api_fakes.LIST_RESP[0]], ret)

        ret = self.api.find_bulk('qaz', id='0')
        self.assertEqual([], ret)

        ret = self.api.find_bulk('qaz', name='beta')
        self.assertEqual([api_fakes.LIST_RESP[1]], ret)

        ret = self.api.find_bulk('qaz', error='bogus')
        self.assertEqual([], ret)

    def test_baseapi_find_bulk_two(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.find_bulk('qaz', id='1', name='alpha')
        self.assertEqual([api_fakes.LIST_RESP[0]], ret)

        ret = self.api.find_bulk('qaz', id='1', name='beta')
        self.assertEqual([], ret)

        ret = self.api.find_bulk('qaz', id='1', error='beta')
        self.assertEqual([], ret)

    def test_baseapi_find_bulk_dict(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json={'qaz': api_fakes.LIST_RESP},
            status_code=200,
        )
        ret = self.api.find_bulk('qaz', id='1')
        self.assertEqual([api_fakes.LIST_RESP[0]], ret)


class TestBaseAPIList(api_fakes.TestSession):

    def setUp(self):
        super(TestBaseAPIList, self).setUp()
        self.api = api.BaseAPI(
            session=self.sess,
            endpoint=self.BASE_URL,
        )

    def test_baseapi_list_no_args(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz',
            json=api_fakes.LIST_RESP,
            status_code=204,
        )
        ret = self.api.list('/qaz')
        self.assertEqual(api_fakes.LIST_RESP, ret)

    def test_baseapi_list_params(self):
        params = {'format': 'json'}
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '?format=json',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.list('', **params)
        self.assertEqual(api_fakes.LIST_RESP, ret)

        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?format=json',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.list('qaz', **params)
        self.assertEqual(api_fakes.LIST_RESP, ret)

    def test_baseapi_list_body(self):
        self.requests_mock.register_uri(
            'POST',
            self.BASE_URL + '/qaz',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.list('qaz', body=api_fakes.LIST_BODY)
        self.assertEqual(api_fakes.LIST_RESP, ret)

    def test_baseapi_list_detailed(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz/details',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.list('qaz', detailed=True)
        self.assertEqual(api_fakes.LIST_RESP, ret)

    def test_baseapi_list_filtered(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?attr=value',
            json=api_fakes.LIST_RESP,
            status_code=200,
        )
        ret = self.api.list('qaz', attr='value')
        self.assertEqual(api_fakes.LIST_RESP, ret)

    def test_baseapi_list_wrapped(self):
        self.requests_mock.register_uri(
            'GET',
            self.BASE_URL + '/qaz?attr=value',
            json={'responses': api_fakes.LIST_RESP},
            status_code=200,
        )
        ret = self.api.list('qaz', attr='value')
        self.assertEqual({'responses': api_fakes.LIST_RESP}, ret)
