# Copyright 2016 FUJITSU LIMITED
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

from cinderclient import api_versions
from cinderclient import utils


@api_versions.wraps("3.0", "3.1")
def do_fake_action():
    """help message

    This will not show up in help message
    """
    return "fake_action 3.0 to 3.1"


@api_versions.wraps("3.2", "3.3")  # noqa: F811
def do_fake_action():
    return "fake_action 3.2 to 3.3"


@api_versions.wraps("3.6")
@utils.arg(
    '--foo',
    start_version='3.7')
def do_another_fake_action():
    return "another_fake_action"


@utils.arg(
    '--foo',
    start_version='3.1',
    end_version='3.2')
@utils.arg(
    '--bar',
    help='bar help',
    start_version='3.3',
    end_version='3.4')
def do_fake_action2():
    return "fake_action2"


@utils.arg(
    '--foo',
    help='first foo',
    start_version='3.6',
    end_version='3.7')
@utils.arg(
    '--foo',
    help='second foo',
    start_version='3.8')
def do_fake_action3():
    return "fake_action3"
