#   Copyright 2012-2013 OpenStack Foundation
#
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

"""Common client utilities"""

import copy
import getpass
import logging
import os
import six
import time
import warnings

from cliff import columns as cliff_columns
from oslo_utils import importutils

from osc_lib import exceptions
from osc_lib.i18n import _


LOG = logging.getLogger(__name__)


def backward_compat_col_lister(column_headers, columns, column_map):
    """Convert the column headers to keep column backward compatibility.

    Replace the new column name of column headers by old name, so that
    the column headers can continue to support to show the old column name by
    --column/-c option with old name, like: volume list -c 'Display Name'

    :param column_headers: The column headers to be output in list command.
    :param columns: The columns to be output.
    :param column_map: The key of map is old column name, the value is new
            column name, like: {'old_col': 'new_col'}
    """
    if not columns:
        return column_headers
    # NOTE(RuiChen): column_headers may be a tuple in some code, like:
    #                volume v1, convert it to a list in order to change
    #                the column name.
    column_headers = list(column_headers)
    for old_col, new_col in six.iteritems(column_map):
        if old_col in columns:
            LOG.warning(_('The column "%(old_column)s" was deprecated, '
                          'please use "%(new_column)s" replace.') % {
                              'old_column': old_col,
                              'new_column': new_col}
                        )
            if new_col in column_headers:
                column_headers[column_headers.index(new_col)] = old_col
    return column_headers


def backward_compat_col_showone(show_object, columns, column_map):
    """Convert the output object to keep column backward compatibility.

    Replace the new column name of output object by old name, so that
    the object can continue to support to show the old column name by
    --column/-c option with old name, like: volume show -c 'display_name'

    :param show_object: The object to be output in create/show commands.
    :param columns: The columns to be output.
    :param column_map: The key of map is old column name, the value is new
        column name, like: {'old_col': 'new_col'}
    """
    if not columns:
        return show_object

    show_object = copy.deepcopy(show_object)
    for old_col, new_col in six.iteritems(column_map):
        if old_col in columns:
            LOG.warning(_('The column "%(old_column)s" was deprecated, '
                          'please use "%(new_column)s" replace.') % {
                              'old_column': old_col,
                              'new_column': new_col}
                        )
            if new_col in show_object:
                show_object.update({old_col: show_object.pop(new_col)})
    return show_object


def build_kwargs_dict(arg_name, value):
    """Return a dictionary containing `arg_name` if `value` is set."""
    kwargs = {}
    if value:
        kwargs[arg_name] = value
    return kwargs


def calculate_header_and_attrs(column_headers, attrs, parsed_args):
    """Calculate headers and attribute names based on parsed_args.column.

    When --column (-c) option is specified, this function calculates
    column headers and expected API attribute names according to
    the OSC header/column definitions.

    This function also adjusts the content of parsed_args.columns
    if API attribute names are used in parsed_args.columns.
    This allows users to specify API attribute names in -c option.

    :param column_headers: A tuple/list of column headers to display
    :param attrs: a tuple/list of API attribute names. The order of
        corresponding column header and API attribute name must match.
    :param parsed_args: Parsed argument object returned by argparse parse_args
    :returns: A tuple of calculated headers and API attribute names.
    """
    if parsed_args.columns:
        header_attr_map = dict(zip(column_headers, attrs))
        expected_attrs = [header_attr_map.get(c, c)
                          for c in parsed_args.columns]
        attr_header_map = dict(zip(attrs, column_headers))
        expected_headers = [attr_header_map.get(c, c)
                            for c in parsed_args.columns]
        # If attribute name is used in parsed_args.columns
        # convert it into display names because cliff expects
        # name in parsed_args.columns and name in column_headers matches.
        parsed_args.columns = expected_headers
        return expected_headers, expected_attrs
    else:
        return column_headers, attrs


def env(*vars, **kwargs):
    """Search for the first defined of possibly many env vars

    Returns the first environment variable defined in vars, or
    returns the default defined in kwargs.
    """
    for v in vars:
        value = os.environ.get(v, None)
        if value:
            return value
    return kwargs.get('default', '')


def find_min_match(items, sort_attr, **kwargs):
    """Find all resources meeting the given minimum constraints

    :param items: A List of objects to consider
    :param sort_attr: Attribute to sort the resulting list
    :param kwargs: A dict of attributes and their minimum values
    :rtype: A list of resources osrted by sort_attr that meet the minimums
    """

    def minimum_pieces_of_flair(item):
        """Find lowest value greater than the minumum"""

        result = True
        for k in kwargs:
            # AND together all of the given attribute results
            result = result and kwargs[k] <= get_field(item, k)
        return result

    return sort_items(filter(minimum_pieces_of_flair, items), sort_attr)


def find_resource(manager, name_or_id, **kwargs):
    """Helper for the _find_* methods.

    :param manager: A client manager class
    :param name_or_id: The resource we are trying to find
    :param kwargs: To be used in calling .find()
    :rtype: The found resource

    This method will attempt to find a resource in a variety of ways.
    Primarily .get() methods will be called with `name_or_id` as an integer
    value, and tried again as a string value.

    If both fail, then a .find() is attempted, which is essentially calling
    a .list() function with a 'name' query parameter that is set to
    `name_or_id`.

    Lastly, if any kwargs are passed in, they will be treated as additional
    query parameters. This is particularly handy in the case of finding
    resources in a domain.

    """

    # Case 1: name_or_id is an ID, we need to call get() directly
    # for example: /projects/454ad1c743e24edcad846d1118837cac
    # For some projects, the name only will work. For keystone, this is not
    # enough information, and domain information is necessary.
    try:
        return manager.get(name_or_id)
    except Exception:
        pass

    if kwargs:
        # Case 2: name_or_id is a name, but we have query args in kwargs
        # for example: /projects/demo&domain_id=30524568d64447fbb3fa8b7891c10dd
        try:
            return manager.get(name_or_id, **kwargs)
        except Exception:
            pass

    # Case 3: Try to get entity as integer id. Keystone does not have integer
    # IDs, they are UUIDs, but some things in nova do, like flavors.
    try:
        if isinstance(name_or_id, int) or name_or_id.isdigit():
            return manager.get(int(name_or_id), **kwargs)
    # FIXME(dtroyer): The exception to catch here is dependent on which
    #                 client library the manager passed in belongs to.
    #                 Eventually this should be pulled from a common set
    #                 of client exceptions.
    except Exception as ex:
        if (type(ex).__name__ == 'NotFound' or
                type(ex).__name__ == 'HTTPNotFound' or
                type(ex).__name__ == 'TypeError'):
            pass
        else:
            raise

    # Case 4: Try to use find.
    # Reset the kwargs here for find
    if len(kwargs) == 0:
        kwargs = {}

    try:
        # Prepare the kwargs for calling find
        if 'NAME_ATTR' in manager.resource_class.__dict__:
            # novaclient does this for oddball resources
            kwargs[manager.resource_class.NAME_ATTR] = name_or_id
        else:
            kwargs['name'] = name_or_id
    except Exception:
        pass

    # finally try to find entity by name
    try:
        return manager.find(**kwargs)
    # FIXME(dtroyer): The exception to catch here is dependent on which
    #                 client library the manager passed in belongs to.
    #                 Eventually this should be pulled from a common set
    #                 of client exceptions.
    except Exception as ex:
        if type(ex).__name__ == 'NotFound':
            msg = _(
                "No %(resource)s with a name or ID of '%(id)s' exists."
            )
            raise exceptions.CommandError(msg % {
                'resource': manager.resource_class.__name__.lower(),
                'id': name_or_id,
            })
        if type(ex).__name__ == 'NoUniqueMatch':
            msg = _(
                "More than one %(resource)s exists with the name '%(id)s'."
            )
            raise exceptions.CommandError(msg % {
                'resource': manager.resource_class.__name__.lower(),
                'id': name_or_id,
            })

        if type(ex).__name__ == 'Forbidden':
            msg = _(
                "You are not authorized to find %(resource)s with the "
                "name '%(id)s'."
            )
            raise exceptions.CommandError(msg % {
                'resource': manager.resource_class.__name__.lower(),
                'id': name_or_id,
            })
        else:
            pass

    # Case 5: For client with no find function, list all resources and hope
    # to find a matching name or ID.
    count = 0
    for resource in manager.list():
        if (resource.get('id') == name_or_id or
                resource.get('name') == name_or_id):
            count += 1
            _resource = resource
    if count == 0:
        # we found no match, report back this error:
        msg = _("Could not find resource %s")
        raise exceptions.CommandError(msg % name_or_id)
    elif count == 1:
        return _resource
    else:
        # we found multiple matches, report back this error
        msg = _("More than one resource exists with the name or ID '%s'.")
        raise exceptions.CommandError(msg % name_or_id)


def format_dict(data, prefix=None):
    """Return a formatted string of key value pairs

    :param data: a dict
    :param prefix: the current parent keys in a recursive call
    :rtype: a string formatted to key='value'
    """

    if data is None:
        return None

    output = ""
    for s in sorted(data):
        if prefix:
            key_str = ".".join([prefix, s])
        else:
            key_str = s
        if isinstance(data[s], dict):
            # NOTE(dtroyer): Only append the separator chars here, quoting
            #                is completely handled in the terminal case.
            output = output + format_dict(data[s], prefix=key_str) + ", "
        elif data[s] is not None:
            output = output + key_str + "='" + six.text_type(data[s]) + "', "
        else:
            output = output + key_str + "=, "
    return output[:-2]


def format_dict_of_list(data, separator='; '):
    """Return a formatted string of key value pair

    :param data: a dict, key is string, value is a list of string, for example:
                 {u'public': [u'2001:db8::8', u'172.24.4.6']}
    :param separator: the separator to use between key/value pair
                      (default: '; ')
    :return: a string formatted to {'key1'=['value1', 'value2']} with separated
             by separator
    """
    if data is None:
        return None

    output = []
    for key in sorted(data):
        value = data[key]
        if value is None:
            continue
        value_str = format_list(value)
        group = "%s=%s" % (key, value_str)
        output.append(group)

    return separator.join(output)


def format_list(data, separator=', '):
    """Return a formatted strings

    :param data: a list of strings
    :param separator: the separator to use between strings (default: ', ')
    :rtype: a string formatted based on separator
    """
    if data is None:
        return None

    return separator.join(sorted(data))


def format_list_of_dicts(data):
    """Return a formatted string of key value pairs for each dict

    :param data: a list of dicts
    :rtype: a string formatted to key='value' with dicts separated by new line
    """
    if data is None:
        return None

    return '\n'.join(format_dict(i) for i in data)


def format_size(size):
    """Display size of a resource in a human readable format

    :param string size:
        The size of the resource in bytes.

    :returns:
        Returns the size in human-friendly format
    :rtype string:

    This function converts the size (provided in bytes) of a resource
    into a human-friendly format such as K, M, G, T, P, E, Z
    """

    suffix = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']
    base = 1000.0
    index = 0

    if size is None:
        size = 0
    while size >= base:
        index = index + 1
        size = size / base

    padded = '%.1f' % size
    stripped = padded.rstrip('0').rstrip('.')

    return '%s%s' % (stripped, suffix[index])


def get_client_class(api_name, version, version_map):
    """Returns the client class for the requested API version

    :param api_name: the name of the API, e.g. 'compute', 'image', etc
    :param version: the requested API version
    :param version_map: a dict of client classes keyed by version
    :rtype: a client class for the requested API version
    """
    try:
        client_path = version_map[str(version)]
    except (KeyError, ValueError):
        sorted_versions = sorted(version_map.keys(),
                                 key=lambda s: list(map(int, s.split('.'))))
        msg = _(
            "Invalid %(api_name)s client version '%(version)s'. "
            "must be one of: %(version_map)s"
        )
        raise exceptions.UnsupportedVersion(msg % {
            'api_name': api_name,
            'version': version,
            'version_map': ', '.join(sorted_versions),
        })

    return importutils.import_class(client_path)


def get_dict_properties(item, fields, mixed_case_fields=None, formatters=None):
    """Return a tuple containing the item properties.

    :param item: a single dict resource
    :param fields: tuple of strings with the desired field names
    :param mixed_case_fields: tuple of field names to preserve case
    :param formatters: dictionary mapping field names to callables
       to format the values
    """
    if mixed_case_fields is None:
        mixed_case_fields = []
    if formatters is None:
        formatters = {}

    row = []

    for field in fields:
        if field in mixed_case_fields:
            field_name = field.replace(' ', '_')
        else:
            field_name = field.lower().replace(' ', '_')
        data = item[field_name] if field_name in item else ''
        if field in formatters:
            formatter = formatters[field]
            if (isinstance(formatter, type) and issubclass(
                    formatter, cliff_columns.FormattableColumn)):
                data = formatter(data)
            elif callable(formatter):
                warnings.warn(
                    'The usage of formatter functions is now discouraged. '
                    'Consider using cliff.columns.FormattableColumn instead. '
                    'See reviews linked with bug 1687955 for more detail.',
                    category=DeprecationWarning)
                if data is not None:
                    data = formatter(data)
            else:
                msg = "Invalid formatter provided."
                raise exceptions.CommandError(msg)

        row.append(data)
    return tuple(row)


def get_effective_log_level():
    """Returns the lowest logging level considered by logging handlers

    Retrieve and return the smallest log level set among the root
    logger's handlers (in case of multiple handlers).
    """
    root_log = logging.getLogger()
    min_log_lvl = logging.CRITICAL
    for handler in root_log.handlers:
        min_log_lvl = min(min_log_lvl, handler.level)
    return min_log_lvl


def get_field(item, field):
    try:
        if isinstance(item, dict):
            return item[field]
        else:
            return getattr(item, field)
    except Exception:
        msg = _("Resource doesn't have field %s")
        raise exceptions.CommandError(msg % field)


def get_item_properties(item, fields, mixed_case_fields=None, formatters=None):
    """Return a tuple containing the item properties.

    :param item: a single item resource (e.g. Server, Project, etc)
    :param fields: tuple of strings with the desired field names
    :param mixed_case_fields: tuple of field names to preserve case
    :param formatters: dictionary mapping field names to callables
       to format the values
    """
    if mixed_case_fields is None:
        mixed_case_fields = []
    if formatters is None:
        formatters = {}

    row = []

    for field in fields:
        if field in mixed_case_fields:
            field_name = field.replace(' ', '_')
        else:
            field_name = field.lower().replace(' ', '_')
        data = getattr(item, field_name, '')
        if field in formatters:
            formatter = formatters[field]
            if (isinstance(formatter, type) and issubclass(
                    formatter, cliff_columns.FormattableColumn)):
                data = formatter(data)
            elif callable(formatter):
                warnings.warn(
                    'The usage of formatter functions is now discouraged. '
                    'Consider using cliff.columns.FormattableColumn instead. '
                    'See reviews linked with bug 1687955 for more detail.',
                    category=DeprecationWarning)
                if data is not None:
                    data = formatter(data)
            else:
                msg = "Invalid formatter provided."
                raise exceptions.CommandError(msg)

        row.append(data)
    return tuple(row)


def get_password(stdin, prompt=None, confirm=True):
    message = prompt or "User Password:"
    if hasattr(stdin, 'isatty') and stdin.isatty():
        try:
            while True:
                first_pass = getpass.getpass(message)
                if not confirm:
                    return first_pass
                second_pass = getpass.getpass("Repeat " + message)
                if first_pass == second_pass:
                    return first_pass
                msg = _("The passwords entered were not the same")
                print(msg)
        except EOFError:  # Ctl-D
            msg = _("Error reading password")
            raise exceptions.CommandError(msg)
    msg = _("No terminal detected attempting to read password")
    raise exceptions.CommandError(msg)


def is_ascii(string):
    try:
        (string.decode('ascii') if isinstance(string, bytes)
            else string.encode('ascii'))
        return True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False


def read_blob_file_contents(blob_file):
    try:
        with open(blob_file) as file:
            blob = file.read().strip()
        return blob
    except IOError:
        msg = _("Error occurred trying to read from file %s")
        raise exceptions.CommandError(msg % blob_file)


def sort_items(items, sort_str, sort_type=None):
    """Sort items based on sort keys and sort directions given by sort_str.

    :param items: a list or generator object of items
    :param sort_str: a string defining the sort rules, the format is
        '<key1>:[direction1],<key2>:[direction2]...', direction can be 'asc'
        for ascending or 'desc' for descending, if direction is not given,
        it's ascending by default
    :return: sorted items
    """
    if not sort_str:
        return items
    # items may be a generator object, transform it to a list
    items = list(items)
    sort_keys = sort_str.strip().split(',')
    for sort_key in reversed(sort_keys):
        reverse = False
        if ':' in sort_key:
            sort_key, direction = sort_key.split(':', 1)
            if not sort_key:
                msg = _("'<empty string>'' is not a valid sort key")
                raise exceptions.CommandError(msg)
            if direction not in ['asc', 'desc']:
                if not direction:
                    direction = "<empty string>"
                msg = _(
                    "'%(direction)s' is not a valid sort direction for "
                    "sort key %(sort_key)s, use 'asc' or 'desc' instead"
                )
                raise exceptions.CommandError(msg % {
                    'direction': direction,
                    'sort_key': sort_key,
                })
            if direction == 'desc':
                reverse = True

        def f(x):
            # Attempts to convert items to same 'sort_type' if provided.
            # This is due to Python 3 throwing TypeError if you attempt to
            # compare different types
            item = get_field(x, sort_key)
            if sort_type and not isinstance(item, sort_type):
                try:
                    item = sort_type(item)
                except Exception:
                    # Can't convert, so no sensible way to compare
                    item = sort_type()
            return item

        items.sort(key=f, reverse=reverse)

    return items


def wait_for_delete(manager,
                    res_id,
                    status_field='status',
                    error_status=['error'],
                    exception_name=['NotFound'],
                    sleep_time=5,
                    timeout=300,
                    callback=None):
    """Wait for resource deletion

    :param manager: the manager from which we can get the resource
    :param res_id: the resource id to watch
    :param status_field: the status attribute in the returned resource object,
        this is used to check for error states while the resource is being
        deleted
    :param error_status: a list of status strings for error
    :param exception_name: a list of exception strings for deleted case
    :param sleep_time: wait this long between checks (seconds)
    :param timeout: check until this long (seconds)
    :param callback: called per sleep cycle, useful to display progress; this
        function is passed a progress value during each iteration of the wait
        loop
    :rtype: True on success, False if the resource has gone to error state or
        the timeout has been reached
    """
    total_time = 0
    while total_time < timeout:
        try:
            # might not be a bad idea to re-use find_resource here if it was
            # a bit more friendly in the exceptions it raised so we could just
            # handle a NotFound exception here without parsing the message
            res = manager.get(res_id)
        except Exception as ex:
            if type(ex).__name__ in exception_name:
                return True
            raise

        status = getattr(res, status_field, '').lower()
        if status in error_status:
            return False

        if callback:
            progress = getattr(res, 'progress', None) or 0
            callback(progress)
        time.sleep(sleep_time)
        total_time += sleep_time

    # if we got this far we've timed out
    return False


def wait_for_status(status_f,
                    res_id,
                    status_field='status',
                    success_status=['active'],
                    error_status=['error'],
                    sleep_time=5,
                    callback=None):
    """Wait for status change on a resource during a long-running operation

    :param status_f: a status function that takes a single id argument
    :param res_id: the resource id to watch
    :param status_field: the status attribute in the returned resource object
    :param success_status: a list of status strings for successful completion
    :param error_status: a list of status strings for error
    :param sleep_time: wait this long (seconds)
    :param callback: called per sleep cycle, useful to display progress
    :rtype: True on success
    """
    while True:
        res = status_f(res_id)
        status = getattr(res, status_field, '').lower()
        if status in success_status:
            retval = True
            break
        elif status in error_status:
            retval = False
            break
        if callback:
            progress = getattr(res, 'progress', None) or 0
            callback(progress)
        time.sleep(sleep_time)
    return retval
