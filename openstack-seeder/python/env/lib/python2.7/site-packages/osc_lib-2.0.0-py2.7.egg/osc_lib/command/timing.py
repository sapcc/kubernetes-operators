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

"""Timing Implementation"""

from osc_lib.command import command


class Timing(command.Lister):
    """Show timing data"""

    def take_action(self, parsed_args):
        column_headers = (
            'URL',
            'Seconds',
        )

        results = []
        total = 0.0
        for td in self.app.timing_data:
            sec = td.elapsed.total_seconds()
            total += sec
            results.append((td.method + ' ' + td.url, sec))
        results.append(('Total', total))
        return (
            column_headers,
            results,
        )
