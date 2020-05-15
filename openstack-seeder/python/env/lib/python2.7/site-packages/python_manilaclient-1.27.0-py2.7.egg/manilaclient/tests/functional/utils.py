# Copyright 2015 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ast
import six
from tempest.lib.cli import output_parser
import testtools

from manilaclient import api_versions
from manilaclient import config

CONF = config.CONF


def multi_line_row_table(output_lines, group_by_column_index=0):
    parsed_table = output_parser.table(output_lines)

    rows = parsed_table['values']
    row_index = 0

    def get_column_index(column_name, headers, default):
        return next(
            (i for i, h in enumerate(headers) if h.lower() == column_name),
            default
        )

    if group_by_column_index is None:
        group_by_column_index = get_column_index(
            'id', parsed_table['headers'], 0)

    def is_embedded_table(parsed_rows):
        def is_table_border(t):
            return six.text_type(t).startswith('+')

        return (isinstance(parsed_rows, list)
                and len(parsed_rows) > 3
                and is_table_border(parsed_rows[0])
                and is_table_border(parsed_rows[-1]))

    def merge_cells(master_cell, value_cell):
        if value_cell:
            if not isinstance(master_cell, list):
                master_cell = [master_cell]
            master_cell.append(value_cell)

        if is_embedded_table(master_cell):
            return multi_line_row_table('\n'.join(master_cell), None)

        return master_cell

    def is_empty_row(row):
        empty_cells = 0
        for cell in row:
            if cell == '':
                empty_cells += 1
        return len(row) == empty_cells

    while row_index < len(rows):
        row = rows[row_index]
        line_with_value = row_index > 0 and row[group_by_column_index] == ''

        if line_with_value and not is_empty_row(row):
            rows[row_index - 1] = list(map(merge_cells,
                                           rows[row_index - 1],
                                           rows.pop(row_index)))
        else:
            row_index += 1

    return parsed_table


def listing(output_lines):
    """Return list of dicts with basic item info parsed from cli output."""

    items = []
    table_ = multi_line_row_table(output_lines)
    for row in table_['values']:
        item = {}
        for col_idx, col_key in enumerate(table_['headers']):
            item[col_key] = row[col_idx]
        items.append(item)
    return items


def details(output_lines):
    """Returns dict parsed from CLI output."""
    result = listing(output_lines)
    d = {}
    for item in result:
        d.update({item['Property']: item['Value']})
    return d


def is_microversion_supported(microversion):
    return (
        api_versions.APIVersion(CONF.min_api_microversion) <=
        api_versions.APIVersion(microversion) <=
        api_versions.APIVersion(CONF.max_api_microversion)
    )


def skip_if_microversion_not_supported(microversion):
    """Decorator for tests that are microversion-specific."""
    if not is_microversion_supported(microversion):
        reason = ("Skipped. Test requires microversion %s that is not "
                  "allowed to be used by configuration." % microversion)
        return testtools.skip(reason)
    return lambda f: f


def choose_matching_backend(share, pools, share_type):
    extra_specs = {}

    # convert extra-specs in provided type to dict format
    pair = [x.strip() for x in share_type['required_extra_specs'].split(':')]
    if len(pair) == 2:
        value = (True if six.text_type(pair[1]).lower() == 'true'
                 else False if six.text_type(pair[1]).lower() == 'false'
                 else pair[1])
        extra_specs[pair[0]] = value

    selected_pool = next(
        (x for x in pools if (x['Name'] != share['host'] and all(
            y in ast.literal_eval(x['Capabilities']).items() for y in
            extra_specs.items()))),
        None)

    return selected_pool['Name']
