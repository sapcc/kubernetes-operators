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

import six
from six.moves.urllib import parse as urlparse


def encode(value, encoding='utf-8'):
    """Return a byte repr of a string for a given encoding.

    Byte strings and values of other types are returned as is.

    """

    if isinstance(value, six.text_type):
        return value.encode(encoding)
    else:
        return value


def url_with_filters(url, filters=None):
    """Add a percent-encoded string of filters (a dict) to a base url."""

    if filters:
        filters = [(encode(k), encode(v)) for k, v in filters.items()]

        urlencoded_filters = urlparse.urlencode(filters)
        url = urlparse.urljoin(url, '?' + urlencoded_filters)

    return url
