"""
Copyright 2015 Rackspace

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from __future__ import absolute_import
from __future__ import print_function
import sys
import tempfile
import traceback

import fixtures
from tempest.lib.exceptions import CommandFailed
from testtools.runtest import MultipleExceptions

from designateclient.functionaltests.client import DesignateCLI


class BaseFixture(fixtures.Fixture):

    def __init__(self, user='default', *args, **kwargs):
        """args/kwargs are forwarded to a create method on DesignateCLI"""
        super(BaseFixture, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.client = DesignateCLI.as_user(user)

    def setUp(self):
        # Sometimes, exceptions are raised in _setUp methods on fixtures.
        # testtools pushes the exception into a MultipleExceptions object along
        # with an artificial SetupError, which produces bad error messages.
        # This just logs those stack traces to stderr for easier debugging.
        try:
            super(BaseFixture, self).setUp()
        except MultipleExceptions as e:
            for i, exc_info in enumerate(e.args):
                print('--- printing MultipleExceptions traceback {} of {} ---'
                      .format(i + 1, len(e.args)), file=sys.stderr)
                traceback.print_exception(*exc_info)
            raise


class ZoneFixture(BaseFixture):
    """See DesignateCLI.zone_create for __init__ args"""

    def _setUp(self):
        super(ZoneFixture, self)._setUp()
        self.zone = self.client.zone_create(*self.args, **self.kwargs)
        self.addCleanup(self.cleanup_zone, self.client, self.zone.id)

    @classmethod
    def cleanup_zone(cls, client, zone_id):
        try:
            client.zone_delete(zone_id)
        except CommandFailed:
            pass


class TransferRequestFixture(BaseFixture):
    """See DesignateCLI.zone_transfer_request_create for __init__ args"""

    def __init__(self, zone, user='default', target_user='alt', *args,
                 **kwargs):
        super(TransferRequestFixture, self).__init__(user, *args, **kwargs)
        self.zone = zone
        self.target_client = DesignateCLI.as_user(target_user)

        # the client has a bug such that it requires --target-project-id.
        # when this bug is fixed, please remove this
        self.kwargs['target_project_id'] = self.target_client.project_id

    def _setUp(self):
        super(TransferRequestFixture, self)._setUp()
        self.transfer_request = self.client.zone_transfer_request_create(
            zone_id=self.zone.id,
            *self.args, **self.kwargs
        )
        self.addCleanup(self.cleanup_transfer_request, self.client,
                        self.transfer_request.id)
        self.addCleanup(ZoneFixture.cleanup_zone, self.client, self.zone.id)
        self.addCleanup(ZoneFixture.cleanup_zone, self.target_client,
                        self.zone.id)

    @classmethod
    def cleanup_transfer_request(cls, client, transfer_request_id):
        try:
            client.zone_transfer_request_delete(transfer_request_id)
        except CommandFailed:
            pass


class ExportFixture(BaseFixture):
    """See DesignateCLI.zone_export_create for __init__ args"""

    def __init__(self, zone, user='default', *args, **kwargs):
        super(ExportFixture, self).__init__(user, *args, **kwargs)
        self.zone = zone

    def _setUp(self):
        super(ExportFixture, self)._setUp()
        self.zone_export = self.client.zone_export_create(
            zone_id=self.zone.id,
            *self.args, **self.kwargs
        )
        self.addCleanup(self.cleanup_zone_export, self.client,
                        self.zone_export.id)
        self.addCleanup(ZoneFixture.cleanup_zone, self.client, self.zone.id)

    @classmethod
    def cleanup_zone_export(cls, client, zone_export_id):
        try:
            client.zone_export_delete(zone_export_id)
        except CommandFailed:
            pass


class ImportFixture(BaseFixture):
    """See DesignateCLI.zone_import_create for __init__ args"""

    def __init__(self, zone_file_contents, user='default', *args, **kwargs):
        super(ImportFixture, self).__init__(user, *args, **kwargs)
        self.zone_file_contents = zone_file_contents

    def _setUp(self):
        super(ImportFixture, self)._setUp()

        with tempfile.NamedTemporaryFile() as f:
            f.write(self.zone_file_contents)
            f.flush()

            self.zone_import = self.client.zone_import_create(
                zone_file_path=f.name,
                *self.args, **self.kwargs
            )

        self.addCleanup(self.cleanup_zone_import, self.client,
                        self.zone_import.id)
        self.addCleanup(ZoneFixture.cleanup_zone, self.client,
                        self.zone_import.zone_id)

    @classmethod
    def cleanup_zone_import(cls, client, zone_import_id):
        try:
            client.zone_import_delete(zone_import_id)
        except CommandFailed:
            pass


class RecordsetFixture(BaseFixture):
    """See DesignateCLI.recordset_create for __init__ args"""

    def _setUp(self):
        super(RecordsetFixture, self)._setUp()
        self.recordset = self.client.recordset_create(
            *self.args, **self.kwargs)
        self.addCleanup(self.cleanup_recordset, self.client,
                        self.recordset.zone_id, self.recordset.id)

    @classmethod
    def cleanup_recordset(cls, client, zone_id, recordset_id):
        try:
            client.recordset_delete(zone_id, recordset_id)
        except CommandFailed:
            pass


class TLDFixture(BaseFixture):
    """See DesignateCLI.tld_create for __init__ args"""

    def __init__(self, user='admin', *args, **kwargs):
        super(TLDFixture, self).__init__(user=user, *args, **kwargs)

    def _setUp(self):
        super(TLDFixture, self)._setUp()
        self.tld = self.client.tld_create(*self.args, **self.kwargs)
        self.addCleanup(self.cleanup_tld, self.client, self.tld.id)

    @classmethod
    def cleanup_tld(cls, client, tld_id):
        try:
            client.tld_delete(tld_id)
        except CommandFailed:
            pass


class TSIGKeyFixture(BaseFixture):
    """See DesignateCLI.tsigkey_create for __init__ args"""

    def __init__(self, user='admin', *args, **kwargs):
        super(TSIGKeyFixture, self).__init__(user=user, *args, **kwargs)

    def _setUp(self):
        super(TSIGKeyFixture, self)._setUp()
        self.tsigkey = self.client.tsigkey_create(*self.args, **self.kwargs)
        self.addCleanup(self.cleanup_tsigkey(self.client, self.tsigkey.id))

    @classmethod
    def cleanup_tsigkey(cls, client, tsigkey_id):
        try:
            client.tsigkey_delete(tsigkey_id)
        except CommandFailed:
            pass


class BlacklistFixture(BaseFixture):
    """See DesignateCLI.zone_blacklist_create for __init__ args"""

    def __init__(self, user='admin', *args, **kwargs):
        super(BlacklistFixture, self).__init__(user=user, *args, **kwargs)

    def _setUp(self):
        super(BlacklistFixture, self)._setUp()
        self.blacklist = self.client.zone_blacklist_create(*self.args,
                                                           **self.kwargs)
        self.addCleanup(self.cleanup_blacklist, self.client, self.blacklist.id)

    @classmethod
    def cleanup_blacklist(cls, client, blacklist_id):
        try:
            client.zone_blacklist_delete(blacklist_id)
        except CommandFailed:
            pass
