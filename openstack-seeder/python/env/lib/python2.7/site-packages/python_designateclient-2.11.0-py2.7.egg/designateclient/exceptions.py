# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
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


class Base(Exception):
    def __init__(self, message=None):
        if not message:
            message = self.__class__.__name__
        super(Base, self).__init__(message)


class UnsupportedVersion(Base):
    pass


class ResourceNotFound(Base):
    pass


class NoUniqueMatch(Base):
    pass


class RemoteError(Base):
    def __init__(self, message=None, code=None, type=None, errors=None,
                 request_id=None, **ignore):
        err_message = self._get_error_message(message, type, errors)
        self.message = err_message
        self.code = code
        self.type = type
        self.errors = errors
        self.request_id = request_id

        super(RemoteError, self).__init__(err_message)

    def _get_error_message(self, _message, _type, _errors):
        # Try to get a useful error msg if 'message' has nothing
        if not _message:
            if _errors and 'errors' in _errors:
                err_msg = list()
                for err in _errors['errors']:
                    if 'message' in err:
                        err_msg.append(err['message'])
                _message = '. '.join(err_msg)
            elif _type:
                _message = str(_type)
        return _message


class Unknown(RemoteError):
    pass


class BadRequest(RemoteError):
    pass


class Forbidden(RemoteError):
    pass


class Conflict(RemoteError):
    pass


class NotFound(RemoteError):
    pass


class OverQuota(RemoteError):
    pass
