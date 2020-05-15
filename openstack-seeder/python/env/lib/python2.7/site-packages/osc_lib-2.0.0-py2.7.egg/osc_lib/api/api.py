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

"""Base API Library"""

import simplejson as json
import six

from keystoneauth1 import exceptions as ksa_exceptions
from keystoneauth1 import session as ksa_session

from osc_lib import exceptions
from osc_lib.i18n import _


class BaseAPI(object):
    """Base API wrapper for keystoneauth1.session.Session

    Encapsulate the translation between keystoneauth1.session.Session
    and requests.Session in a single layer:

    * Restore some requests.session.Session compatibility;
      keystoneauth1.session.Session.request() has the method and url
      arguments swapped from the rest of the requests-using world.
    * Provide basic endpoint handling when a Service Catalog is not
      available.

    """

    # Which service are we? Set in API-specific subclasses
    SERVICE_TYPE = ""

    # The common OpenStack microversion header
    HEADER_NAME = "OpenStack-API-Version"

    def __init__(
        self,
        session=None,
        service_type=None,
        endpoint=None,
        **kwargs
    ):
        """Base object that contains some common API objects and methods

        :param keystoneauth1.session.Session session:
            The session to be used for making the HTTP API calls.  If None,
            a default keystoneauth1.session.Session will be created.
        :param string service_type:
            API name, i.e. ``identity`` or ``compute``
        :param string endpoint:
            An optional URL to be used as the base for API requests on
            this API.
        :param kwargs:
            Keyword arguments passed to keystoneauth1.session.Session().
        """

        super(BaseAPI, self).__init__()

        # Create a keystoneauth1.session.Session if one is not supplied
        if not session:
            self.session = ksa_session.Session(**kwargs)
        else:
            self.session = session

        self.service_type = service_type
        self.endpoint = self._munge_endpoint(endpoint)

    def _munge_endpoint(self, endpoint):
        """Hook to allow subclasses to massage the passed-in endpoint

        Hook to massage passed-in endpoints from arbitrary sources,
        including direct user input.  By default just remove trailing
        '/' as all of our path info strings start with '/' and not all
        services can handle '//' in their URLs.

        Some subclasses will override this to do additional work, most
        likely with regard to API versions.

        :param string endpoint: The service endpoint, generally direct
                                from the service catalog.
        :return: The modified endpoint
        """

        if isinstance(endpoint, six.string_types):
            return endpoint.rstrip('/')
        else:
            return endpoint

    def _request(self, method, url, session=None, **kwargs):
        """Perform call into session

        All API calls are funneled through this method to provide a common
        place to finalize the passed URL and other things.

        :param string method:
            The HTTP method name, i.e. ``GET``, ``PUT``, etc
        :param string url:
            The API-specific portion of the URL path, or a full URL if
            ``endpoint`` was not supplied at initialization.
        :param keystoneauth1.session.Session session:
            An initialized session to override the one created at
            initialization.
        :param kwargs:
            Keyword arguments passed to requests.request().
        :return: the requests.Response object
        """

        # If session arg is supplied, use it this time, but don't save it
        if not session:
            session = self.session

        # Do the auto-endpoint magic
        if self.endpoint:
            if url:
                url = '/'.join([self.endpoint.rstrip('/'), url.lstrip('/')])
            else:
                # NOTE(dtroyer): This is left here after _munge_endpoint() is
                #                added because endpoint is public and there is
                #                no accounting for what may happen.
                url = self.endpoint.rstrip('/')
        else:
            # Pass on the lack of URL unmolested to maintain the same error
            # handling from keystoneauth: raise EndpointNotFound
            pass

        # Hack out empty headers 'cause KSA can't stomach it
        if 'headers' in kwargs and kwargs['headers'] is None:
            kwargs.pop('headers')

        # Why is ksc session backwards???
        return session.request(url, method, **kwargs)

    # The basic action methods all take a Session and return dict/lists

    def create(
        self,
        url,
        session=None,
        method=None,
        **params
    ):
        """Create a new resource

        :param string url:
            The API-specific portion of the URL path
        :param Session session:
            HTTP client session
        :param string method:
            HTTP method (default POST)
        """

        if not method:
            method = 'POST'
        ret = self._request(method, url, session=session, **params)
        # Should this move into _requests()?
        try:
            return ret.json()
        except json.JSONDecodeError:
            return ret

    def delete(
        self,
        url,
        session=None,
        **params
    ):
        """Delete a resource

        :param string url:
            The API-specific portion of the URL path
        :param Session session:
            HTTP client session
        """

        return self._request('DELETE', url, **params)

    def list(
        self,
        path,
        session=None,
        body=None,
        detailed=False,
        headers=None,
        **params
    ):
        """Return a list of resources

        GET ${ENDPOINT}/${PATH}?${PARAMS}

        path is often the object's plural resource type

        :param string path:
            The API-specific portion of the URL path
        :param Session session:
            HTTP client session
        :param body: data that will be encoded as JSON and passed in POST
            request (GET will be sent by default)
        :param bool detailed:
            Adds '/details' to path for some APIs to return extended attributes
        :param dict headers:
            Headers dictionary to pass to requests
        :returns:
            JSON-decoded response, could be a list or a dict-wrapped-list
        """

        if detailed:
            path = '/'.join([path.rstrip('/'), 'details'])

        if body:
            ret = self._request(
                'POST',
                path,
                # service=self.service_type,
                json=body,
                params=params,
                headers=headers,
            )
        else:
            ret = self._request(
                'GET',
                path,
                # service=self.service_type,
                params=params,
                headers=headers,
            )
        try:
            return ret.json()
        except json.JSONDecodeError:
            return ret

    # Layered actions built on top of the basic action methods do not
    # explicitly take a Session but one may still be passed in kwargs

    def find_attr(
        self,
        path,
        value=None,
        attr=None,
        resource=None,
    ):
        """Find a resource via attribute or ID

        Most APIs return a list wrapped by a dict with the resource
        name as key.  Some APIs (Identity) return a dict when a query
        string is present and there is one return value.  Take steps to
        unwrap these bodies and return a single dict without any resource
        wrappers.

        :param string path:
            The API-specific portion of the URL path
        :param string value:
            value to search for
        :param string attr:
            attribute to use for resource search
        :param string resource:
            plural of the object resource name; defaults to path

        For example:
            n = find(netclient, 'network', 'networks', 'matrix')
        """

        # Default attr is 'name'
        if attr is None:
            attr = 'name'

        # Default resource is path - in many APIs they are the same
        if resource is None:
            resource = path

        def getlist(kw):
            """Do list call, unwrap resource dict if present"""
            ret = self.list(path, **kw)
            if isinstance(ret, dict) and resource in ret:
                ret = ret[resource]
            return ret

        # Search by attribute
        kwargs = {attr: value}
        data = getlist(kwargs)
        if isinstance(data, dict):
            return data
        if len(data) == 1:
            return data[0]
        if len(data) > 1:
            msg = _("Multiple %(resource)s exist with %(attr)s='%(value)s'")
            raise exceptions.CommandError(
                msg % {'resource': resource,
                       'attr': attr,
                       'value': value}
            )

        # Search by id
        kwargs = {'id': value}
        data = getlist(kwargs)
        if len(data) == 1:
            return data[0]
        msg = _("No %(resource)s with a %(attr)s or ID of '%(value)s' found")
        raise exceptions.CommandError(
            msg % {'resource': resource,
                   'attr': attr,
                   'value': value}
        )

    def find_bulk(
        self,
        path,
        headers=None,
        **kwargs
    ):
        """Bulk load and filter locally

        :param string path:
            The API-specific portion of the URL path
        :param kwargs:
            A dict of AVPs to match - logical AND
        :param dict headers:
            Headers dictionary to pass to requests
        :returns: list of resource dicts
        """

        items = self.list(path)
        if isinstance(items, dict):
            # strip off the enclosing dict
            key = list(items.keys())[0]
            items = items[key]

        ret = []
        for o in items:
            try:
                if all(o[attr] == kwargs[attr] for attr in kwargs.keys()):
                    ret.append(o)
            except KeyError:
                continue

        return ret

    def find_one(
        self,
        path,
        **kwargs
    ):
        """Find a resource by name or ID

        :param string path:
            The API-specific portion of the URL path
        :returns:
            resource dict
        """

        bulk_list = self.find_bulk(path, **kwargs)
        num_bulk = len(bulk_list)
        if num_bulk == 0:
            msg = _("none found")
            raise exceptions.NotFound(404, msg)
        elif num_bulk > 1:
            msg = _("many found")
            raise RuntimeError(msg)
        return bulk_list[0]

    def find(
        self,
        path,
        value=None,
        attr=None,
        headers=None,
    ):
        """Find a single resource by name or ID

        :param string path:
            The API-specific portion of the URL path
        :param string value:
            search expression (required, really)
        :param string attr:
            name of attribute for secondary search
        :param dict headers:
            Headers dictionary to pass to requests
        """

        def raise_not_found():
            msg = _("%s not found") % value
            raise exceptions.NotFound(404, msg)

        try:
            ret = self._request(
                'GET', "/%s/%s" % (path, value),
                headers=headers,
            ).json()
            if isinstance(ret, dict):
                # strip off the enclosing dict
                key = list(ret.keys())[0]
                ret = ret[key]
        except (
            ksa_exceptions.NotFound,
            ksa_exceptions.BadRequest,
        ):
            if attr:
                kwargs = {attr: value}
                try:
                    ret = self.find_one(
                        path,
                        headers=headers,
                        **kwargs
                    )
                except (
                    exceptions.NotFound,
                    ksa_exceptions.NotFound,
                ):
                    raise_not_found()
            else:
                raise_not_found()

        return ret
