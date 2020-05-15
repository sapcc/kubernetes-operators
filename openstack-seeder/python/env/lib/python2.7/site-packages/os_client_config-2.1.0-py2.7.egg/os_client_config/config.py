# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
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

import copy
import sys

from openstack.config import loader
from openstack.config.loader import *  # noqa

from os_client_config import cloud_config
from os_client_config import defaults


class OpenStackConfig(loader.OpenStackConfig):

    _cloud_region_class = cloud_config.CloudConfig
    _defaults_module = defaults

    get_one_cloud = loader.OpenStackConfig.get_one
    get_all_clouds = loader.OpenStackConfig.get_all

    def get_cache_expiration_time(self):
        return int(self._cache_expiration_time)

    def get_cache_interval(self):
        return self.get_cache_expiration_time()

    def get_cache_max_age(self):
        return self.get_cache_expiration_time()

    def get_cache_path(self):
        return self._cache_path

    def get_cache_class(self):
        return self._cache_class

    def get_cache_arguments(self):
        return copy.deepcopy(self._cache_arguments)

    def get_cache_expiration(self):
        return copy.deepcopy(self._cache_expiration)


if __name__ == '__main__':
    config = OpenStackConfig().get_all_clouds()
    for cloud in config:
        print_cloud = False
        if len(sys.argv) == 1:
            print_cloud = True
        elif len(sys.argv) == 3 and (
                sys.argv[1] == cloud.name and sys.argv[2] == cloud.region):
            print_cloud = True
        elif len(sys.argv) == 2 and (
                sys.argv[1] == cloud.name):
            print_cloud = True

        if print_cloud:
            print(cloud.name, cloud.region, cloud.config)
