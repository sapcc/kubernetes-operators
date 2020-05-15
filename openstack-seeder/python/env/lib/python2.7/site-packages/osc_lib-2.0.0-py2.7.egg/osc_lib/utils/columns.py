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

import operator

LIST_BOTH = 'both'
LIST_SHORT_ONLY = 'short_only'
LIST_LONG_ONLY = 'long_only'


def get_column_definitions(attr_map, long_listing):
    """Return table headers and column names for a listing table.

    An attribute map (attr_map) is a list of table entry definitions
    and the format of the map is as follows:

    :param attr_map: a list of table entry definitions.
        Each entry should be a tuple consisting of
        (API attribute name, header name, listing mode). For example:

        .. code-block:: python

           (('id', 'ID', LIST_BOTH),
            ('name', 'Name', LIST_BOTH),
            ('tenant_id', 'Project', LIST_LONG_ONLY))

        The third field of each tuple must be one of LIST_BOTH,
        LIST_LONG_ONLY (a corresponding column is shown only in a long mode),
        or LIST_SHORT_ONLY (a corresponding column is shown only
        in a short mode).
    :param long_listing: A boolean value which indicates a long listing
        or not. In most cases, parsed_args.long is passed to this argument.
    :return: A tuple of a list of table headers and a list of column names.

    """

    if long_listing:
        headers = [hdr for col, hdr, listing_mode in attr_map
                   if listing_mode in (LIST_BOTH, LIST_LONG_ONLY)]
        columns = [col for col, hdr, listing_mode in attr_map
                   if listing_mode in (LIST_BOTH, LIST_LONG_ONLY)]
    else:
        headers = [hdr for col, hdr, listing_mode in attr_map if listing_mode
                   if listing_mode in (LIST_BOTH, LIST_SHORT_ONLY)]
        columns = [col for col, hdr, listing_mode in attr_map if listing_mode
                   if listing_mode in (LIST_BOTH, LIST_SHORT_ONLY)]

    return headers, columns


def get_columns(item, attr_map=None):
    """Return pair of resource attributes and corresponding display names.

    :param item: a dictionary which represents a resource.
        Keys of the dictionary are expected to be attributes of the resource.
        Values are not referred to by this method.

        .. code-block:: python

           {'id': 'myid', 'name': 'myname',
            'foo': 'bar', 'tenant_id': 'mytenan'}

    :param attr_map: a list of mapping from attribute to display name.
        The same format is used as for get_column_definitions attr_map.

        .. code-block:: python

           (('id', 'ID', LIST_BOTH),
            ('name', 'Name', LIST_BOTH),
            ('tenant_id', 'Project', LIST_LONG_ONLY))

    :return: A pair of tuple of attributes and tuple of display names.

        .. code-block:: python

           (('id', 'name', 'tenant_id', 'foo'),  # attributes
            ('ID', 'Name', 'Project', 'foo')     # display names

        Both tuples of attributes and display names are sorted by display names
        in the alphabetical order.
        Attributes not found in a given attr_map are kept as-is.
    """
    attr_map = attr_map or tuple([])
    _attr_map_dict = dict((col, hdr) for col, hdr, listing_mode in attr_map)

    columns = [(column, _attr_map_dict.get(column, column))
               for column in item.keys()]
    columns = sorted(columns, key=operator.itemgetter(1))
    return (tuple(col[0] for col in columns),
            tuple(col[1] for col in columns))
