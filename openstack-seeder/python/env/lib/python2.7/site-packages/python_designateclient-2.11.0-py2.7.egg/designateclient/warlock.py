# Copyright 2012 Brian Waldon
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
#
# Code copied from Warlock, as warlock depends on jsonschema==0.2
# Hopefully we can upstream the changes ASAP.
#

import copy
import logging

import jsonschema
import six

LOG = logging.getLogger(__name__)


class InvalidOperation(RuntimeError):
    pass


class ValidationError(ValueError):
    pass


def model_factory(schema):
    """Generate a model class based on the provided JSON Schema

    :param schema: dict representing valid JSON schema
    """
    schema = copy.deepcopy(schema)

    def validator(obj):
        """Apply a JSON schema to an object"""
        try:
            jsonschema.validate(obj, schema, cls=jsonschema.Draft3Validator)
        except jsonschema.ValidationError as e:
            raise ValidationError(str(e))

    class Model(dict):
        """Self-validating model for arbitrary objects"""

        def __init__(self, *args, **kwargs):
            d = dict(*args, **kwargs)

            # we overload setattr so set this manually
            self.__dict__['validator'] = validator
            try:
                self.validator(d)
            except ValidationError as e:
                raise ValueError('Validation Error: %s' % str(e))
            else:
                dict.__init__(self, d)

            self.__dict__['changes'] = {}

        def __getattr__(self, key):
            try:
                return self.__getitem__(key)
            except KeyError:
                raise AttributeError(key)

        def __setitem__(self, key, value):
            mutation = dict(self.items())
            mutation[key] = value
            try:
                self.validator(mutation)
            except ValidationError as e:
                raise InvalidOperation(str(e))

            dict.__setitem__(self, key, value)

            self.__dict__['changes'][key] = value

        def __setattr__(self, key, value):
            self.__setitem__(key, value)

        def clear(self):
            raise InvalidOperation()

        def pop(self, key, default=None):
            raise InvalidOperation()

        def popitem(self):
            raise InvalidOperation()

        def __delitem__(self, key):
            raise InvalidOperation()

        # NOTE(termie): This is kind of the opposite of what copy usually does
        def copy(self):
            return copy.deepcopy(dict(self))

        def update(self, other):
            # NOTE(kiall): It seems update() doesn't update the
            #              self.__dict__['changes'] dict correctly.
            mutation = dict(self.items())
            mutation.update(other)
            try:
                self.validator(mutation)
            except ValidationError as e:
                raise InvalidOperation(str(e))
            dict.update(self, other)

        def iteritems(self):
            return six.iteritems(copy.deepcopy(dict(self)))

        def items(self):
            return list(six.iteritems(copy.deepcopy(dict(self))))

        def itervalues(self):
            return six.itervalues(copy.deepcopy(dict(self)))

        def keys(self):
            return list(six.iterkeys(copy.deepcopy(dict(self))))

        def values(self):
            return list(six.itervalues(copy.deepcopy(dict(self))))

        @property
        def changes(self):
            return copy.deepcopy(self.__dict__['changes'])

    Model.__name__ = str(schema['title'])
    return Model
