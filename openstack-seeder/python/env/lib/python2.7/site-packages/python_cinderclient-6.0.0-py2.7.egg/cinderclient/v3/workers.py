# Copyright (c) 2016 Red Hat, Inc.
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

"""
Interface to workers API
"""
from cinderclient import api_versions
from cinderclient.apiclient import base as common_base
from cinderclient import base


class Service(base.Resource):
    def __repr__(self):
        return "<Service (%s): %s in cluster %s>" % (self.id, self.host,
                                                     self.cluster_name or '-')

    @classmethod
    def list_factory(cls, mngr, elements):
        return [cls(mngr, element, loaded=True) for element in elements]


class WorkerManager(base.Manager):
    base_url = '/workers'

    @api_versions.wraps('3.24')
    def clean(self, **filters):
        url = self.base_url + '/cleanup'
        resp, body = self.api.client.post(url, body=filters)

        cleaning = Service.list_factory(self, body['cleaning'])
        unavailable = Service.list_factory(self, body['unavailable'])

        result = common_base.TupleWithMeta((cleaning, unavailable), resp)
        return result
