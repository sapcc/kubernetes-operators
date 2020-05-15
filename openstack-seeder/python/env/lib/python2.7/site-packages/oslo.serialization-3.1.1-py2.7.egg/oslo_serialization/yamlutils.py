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

"""YAML related utilities.

The main goal of this module is to standardize yaml management inside
openstack. This module reduce technical debt by avoiding re-implementations
of yaml manager in all the openstack projects.
Use this module inside openstack projects to handle yaml securely and properly.
"""

from debtcollector import removals
import yaml


removals.removed_module(
    'oslo_serialization.yamlutils', version='3.0.0',
    removal_version='4.0.0',
    message='The oslo_serialization.yamlutils will be removed')


def load(stream, is_safe=True):
    """Converts a YAML document to a Python object.

    :param stream: the YAML document to convert into a Python object. Accepts
                   a byte string, a Unicode string, an open binary file object,
                   or an open text file object.
    :param is_safe: Turn off safe loading. True by default and only load
                    standard YAML. This option can be turned off by
                    passing ``is_safe=False`` if you need to load not only
                    standard YAML tags or if you need to construct an
                    arbitrary python object.

    Stream specifications:

    * An empty stream contains no documents.
    * Documents are separated with ``---``.
    * Documents may optionally end with ``...``.
    * A single document may or may not be marked with ``---``.

    Parses the given stream and returns a Python object constructed
    from the first document in the stream. If there are no documents
    in the stream, it returns None.
    """
    yaml_loader = yaml.Loader
    if is_safe:
        if hasattr(yaml, 'CSafeLoader'):
            yaml_loader = yaml.CSafeLoader
        else:
            yaml_loader = yaml.SafeLoader
    return yaml.load(stream, yaml_loader)  # nosec B506


def dumps(obj, is_safe=True):
    """Converts a Python object to a YAML document.

    :param obj: python object to convert into YAML representation.
    :param is_safe: Turn off safe dumping.

    Serializes the given Python object to a string and returns that string.
    """
    yaml_dumper = yaml.Dumper
    if is_safe:
        if hasattr(yaml, 'CSafeDumper'):
            yaml_dumper = yaml.CSafeDumper
        else:
            yaml_dumper = yaml.SafeDumper
    return yaml.dump(obj, default_flow_style=False, Dumper=yaml_dumper)


def dump(obj, fp, is_safe=True):
    """Converts a Python object as a YAML document to ``fp``.

    :param obj: python object to convert into YAML representation.
    :param fp: a ``.write()``-supporting file-like object
    :param is_safe: Turn off safe dumping.
    """
    yaml_dumper = yaml.Dumper
    if is_safe:
        if hasattr(yaml, 'CSafeDumper'):
            yaml_dumper = yaml.CSafeDumper
        else:
            yaml_dumper = yaml.SafeDumper
    return yaml.dump(obj, fp, default_flow_style=False, Dumper=yaml_dumper)
