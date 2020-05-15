# Copyright (c) 2013 OpenStack Foundation
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

from cinderclient.v2 import quotas


class QuotaSetManager(quotas.QuotaSetManager):

    def update(self, tenant_id, **updates):
        skip_validation = updates.pop('skip_validation', True)

        body = {'quota_set': {'tenant_id': tenant_id}}
        for update in updates:
            body['quota_set'][update] = updates[update]

        request_url = '/os-quota-sets/%s' % tenant_id
        if not skip_validation:
            request_url += '?skip_validation=False'

        result = self._update(request_url, body)
        return self.resource_class(self, result['quota_set'], loaded=True,
                                   resp=result.request_ids)
