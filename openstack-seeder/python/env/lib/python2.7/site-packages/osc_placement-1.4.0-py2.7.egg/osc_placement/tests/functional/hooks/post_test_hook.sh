#!/bin/bash -xe

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed inside post_test_hook function in devstack gate.

function generate_testr_results {
    if [ -f .testrepository/0 ]; then
        .tox/functional/bin/testr last --subunit > $WORKSPACE/testrepository.subunit
        mv $WORKSPACE/testrepository.subunit $BASE/logs/testrepository.subunit
        /usr/os-testr-env/bin/subunit2html $BASE/logs/testrepository.subunit $BASE/logs/testr_results.html
        gzip -9 $BASE/logs/testrepository.subunit
        gzip -9 $BASE/logs/testr_results.html
        chmod a+r $BASE/logs/testrepository.subunit.gz $BASE/logs/testr_results.html.gz
    fi
}

export OSCPLACEMENT_DIR="$BASE/new/osc-placement"

sudo chown -R $USER:stack $OSCPLACEMENT_DIR

# Go to the osc-placement dir
cd $OSCPLACEMENT_DIR

# Run tests
echo "Running osc-placement functional test suite"
set +e
# Preserve env for OS_ credentials
source $BASE/new/devstack/openrc admin admin
tox -e ${TOX_ENV:-functional}
EXIT_CODE=$?
set -e

# Collect and parse result
generate_testr_results
exit $EXIT_CODE
