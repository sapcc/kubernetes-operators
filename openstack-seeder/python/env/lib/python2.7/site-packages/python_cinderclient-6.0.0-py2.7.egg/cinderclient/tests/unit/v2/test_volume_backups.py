# Copyright (C) 2013 Hewlett-Packard Development Company, L.P.
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

from cinderclient.tests.unit import utils
from cinderclient.tests.unit.v2 import fakes
from cinderclient.v2 import volume_backups_restore


cs = fakes.FakeClient()


class VolumeBackupsTest(utils.TestCase):

    def test_create(self):
        vol = cs.backups.create('2b695faf-b963-40c8-8464-274008fbcef4')
        cs.assert_called('POST', '/backups')
        self._assert_request_id(vol)

    def test_create_full(self):
        vol = cs.backups.create('2b695faf-b963-40c8-8464-274008fbcef4',
                                None, None, False)
        cs.assert_called('POST', '/backups')
        self._assert_request_id(vol)

    def test_create_incremental(self):
        vol = cs.backups.create('2b695faf-b963-40c8-8464-274008fbcef4',
                                None, None, True)
        cs.assert_called('POST', '/backups')
        self._assert_request_id(vol)

    def test_create_force(self):
        vol = cs.backups.create('2b695faf-b963-40c8-8464-274008fbcef4',
                                None, None, False, True)
        cs.assert_called('POST', '/backups')
        self._assert_request_id(vol)

    def test_create_snapshot(self):
        cs.backups.create('2b695faf-b963-40c8-8464-274008fbcef4',
                          None, None, False, False,
                          '3c706gbg-c074-51d9-9575-385119gcdfg5')
        cs.assert_called('POST', '/backups')

    def test_get(self):
        backup_id = '76a17945-3c6f-435c-975b-b5685db10b62'
        back = cs.backups.get(backup_id)
        cs.assert_called('GET', '/backups/%s' % backup_id)
        self._assert_request_id(back)

    def test_list(self):
        lst = cs.backups.list()
        cs.assert_called('GET', '/backups/detail')
        self._assert_request_id(lst)

    def test_list_with_pagination(self):
        lst = cs.backups.list(limit=2, marker=100)
        cs.assert_called('GET', '/backups/detail?limit=2&marker=100')
        self._assert_request_id(lst)

    def test_sorted_list(self):
        lst = cs.backups.list(sort="id")
        cs.assert_called('GET', '/backups/detail?sort=id')
        self._assert_request_id(lst)

    def test_sorted_list_by_data_timestamp(self):
        cs.backups.list(sort="data_timestamp")
        cs.assert_called('GET', '/backups/detail?sort=data_timestamp')

    def test_delete(self):
        b = cs.backups.list()[0]
        del_back = b.delete()
        cs.assert_called('DELETE',
                         '/backups/76a17945-3c6f-435c-975b-b5685db10b62')
        self._assert_request_id(del_back)
        del_back = cs.backups.delete('76a17945-3c6f-435c-975b-b5685db10b62')
        cs.assert_called('DELETE',
                         '/backups/76a17945-3c6f-435c-975b-b5685db10b62')
        self._assert_request_id(del_back)
        del_back = cs.backups.delete(b)
        cs.assert_called('DELETE',
                         '/backups/76a17945-3c6f-435c-975b-b5685db10b62')
        self._assert_request_id(del_back)

    def test_force_delete_with_True_force_param_value(self):
        """Tests delete backup with force parameter set to True"""
        b = cs.backups.list()[0]
        del_back = b.delete(force=True)
        expected_body = {'os-force_delete': None}
        cs.assert_called('POST',
            '/backups/76a17945-3c6f-435c-975b-b5685db10b62/action',
            expected_body)
        self._assert_request_id(del_back)

    def test_force_delete_with_false_force_param_vaule(self):
        """To delete backup with force parameter set to False"""
        b = cs.backups.list()[0]
        del_back = b.delete(force=False)
        cs.assert_called('DELETE',
                         '/backups/76a17945-3c6f-435c-975b-b5685db10b62')
        self._assert_request_id(del_back)
        del_back = cs.backups.delete('76a17945-3c6f-435c-975b-b5685db10b62')
        cs.assert_called('DELETE',
                         '/backups/76a17945-3c6f-435c-975b-b5685db10b62')
        self._assert_request_id(del_back)
        del_back = cs.backups.delete(b)
        cs.assert_called('DELETE',
                         '/backups/76a17945-3c6f-435c-975b-b5685db10b62')
        self._assert_request_id(del_back)

    def test_restore(self):
        backup_id = '76a17945-3c6f-435c-975b-b5685db10b62'
        info = cs.restores.restore(backup_id)
        cs.assert_called('POST', '/backups/%s/restore' % backup_id)
        self.assertIsInstance(info,
                              volume_backups_restore.VolumeBackupsRestore)
        self._assert_request_id(info)

    def test_restore_with_name(self):
        backup_id = '76a17945-3c6f-435c-975b-b5685db10b62'
        name = 'restore_vol'
        info = cs.restores.restore(backup_id, name=name)
        expected_body = {'restore': {'volume_id': None, 'name': name}}
        cs.assert_called('POST', '/backups/%s/restore' % backup_id,
                         body=expected_body)
        self.assertIsInstance(info,
                              volume_backups_restore.VolumeBackupsRestore)

    def test_reset_state(self):
        b = cs.backups.list()[0]
        api = '/backups/76a17945-3c6f-435c-975b-b5685db10b62/action'
        st = b.reset_state(state='error')
        cs.assert_called('POST', api)
        self._assert_request_id(st)
        st = cs.backups.reset_state('76a17945-3c6f-435c-975b-b5685db10b62',
                                    state='error')
        cs.assert_called('POST', api)
        self._assert_request_id(st)
        st = cs.backups.reset_state(b, state='error')
        cs.assert_called('POST', api)
        self._assert_request_id(st)

    def test_record_export(self):
        backup_id = '76a17945-3c6f-435c-975b-b5685db10b62'
        export = cs.backups.export_record(backup_id)
        cs.assert_called('GET',
                         '/backups/%s/export_record' % backup_id)
        self._assert_request_id(export)

    def test_record_import(self):
        backup_service = 'fake-backup-service'
        backup_url = 'fake-backup-url'
        expected_body = {'backup-record': {'backup_service': backup_service,
                                           'backup_url': backup_url}}
        impt = cs.backups.import_record(backup_service, backup_url)
        cs.assert_called('POST', '/backups/import_record', expected_body)
        self._assert_request_id(impt)
