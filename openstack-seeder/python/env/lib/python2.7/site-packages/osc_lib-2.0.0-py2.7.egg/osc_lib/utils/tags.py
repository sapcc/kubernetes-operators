#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#

import argparse

from osc_lib.i18n import _


class _CommaListAction(argparse.Action):

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.split(','))


def add_tag_filtering_option_to_parser(
        parser, resource_name, enhance_help=lambda _h: _h):
    """Add tag filtering options to a parser.

    :param parser: argparse.Argument parser object.
    :param resource_name: Description of the object being filtered.
    :param enhance_help: A callable accepting a single parameter, the
        (translated) help string, and returning a (translated) help string. May
        be used by a caller wishing to add qualifying text, such as "Applies to
        version XYZ only", to the help strings for all options produced by this
        method.
    """
    parser.add_argument(
        '--tags',
        metavar='<tag>[,<tag>,...]',
        action=_CommaListAction,
        help=enhance_help(
            _('List %s which have all given tag(s) '
              '(Comma-separated list of tags)') % resource_name)
    )
    parser.add_argument(
        '--any-tags',
        metavar='<tag>[,<tag>,...]',
        action=_CommaListAction,
        help=enhance_help(
            _('List %s which have any given tag(s) '
              '(Comma-separated list of tags)') % resource_name)
    )
    parser.add_argument(
        '--not-tags',
        metavar='<tag>[,<tag>,...]',
        action=_CommaListAction,
        help=enhance_help(
            _('Exclude %s which have all given tag(s) '
              '(Comma-separated list of tags)') % resource_name)
    )
    parser.add_argument(
        '--not-any-tags',
        metavar='<tag>[,<tag>,...]',
        action=_CommaListAction,
        help=enhance_help(
            _('Exclude %s which have any given tag(s) '
              '(Comma-separated list of tags)') % resource_name)
    )


def get_tag_filtering_args(parsed_args, args):
    """Adds the tag arguments to an args list.

    Intended to be used to append the tags to an argument list that will be
    used for service client.

    :param parsed_args: Parsed argument object returned by argparse parse_args.
    :param args: The argument list to add tags to.
    """
    if parsed_args.tags:
        args['tags'] = ','.join(parsed_args.tags)
    if parsed_args.any_tags:
        args['any_tags'] = ','.join(parsed_args.any_tags)
    if parsed_args.not_tags:
        args['not_tags'] = ','.join(parsed_args.not_tags)
    if parsed_args.not_any_tags:
        args['not_any_tags'] = ','.join(parsed_args.not_any_tags)


def add_tag_option_to_parser_for_create(
        parser, resource_name, enhance_help=lambda _h: _h):
    """Add tag options to a parser for create commands.

    :param parser: argparse.Argument parser object.
    :param resource_name: Description of the object being filtered.
    :param enhance_help: A callable accepting a single parameter, the
        (translated) help string, and returning a (translated) help string. May
        be used by a caller wishing to add qualifying text, such as "Applies to
        version XYZ only", to the help strings for all options produced by this
        method.
    """
    tag_group = parser.add_mutually_exclusive_group()
    tag_group.add_argument(
        '--tag',
        action='append',
        dest='tags',
        metavar='<tag>',
        help=enhance_help(
            _("Tag to be added to the %s "
              "(repeat option to set multiple tags)") % resource_name)
    )
    tag_group.add_argument(
        '--no-tag',
        action='store_true',
        help=enhance_help(_("No tags associated with the %s") % resource_name)
    )


def add_tag_option_to_parser_for_set(
        parser, resource_name, enhance_help=lambda _h: _h):
    """Add tag options to a parser for set commands.

    :param parser: argparse.Argument parser object.
    :param resource_name: Description of the object being filtered.
    :param enhance_help: A callable accepting a single parameter, the
        (translated) help string, and returning a (translated) help string. May
        be used by a caller wishing to add qualifying text, such as "Applies to
        version XYZ only", to the help strings for all options produced by this
        method.
    """
    parser.add_argument(
        '--tag',
        action='append',
        dest='tags',
        metavar='<tag>',
        help=enhance_help(
            _("Tag to be added to the %s "
              "(repeat option to set multiple tags)") % resource_name)
    )
    parser.add_argument(
        '--no-tag',
        action='store_true',
        help=enhance_help(
            _("Clear tags associated with the %s. Specify both "
              "--tag and --no-tag to overwrite current tags") % resource_name)
    )


def add_tag_option_to_parser_for_unset(
        parser, resource_name, enhance_help=lambda _h: _h):
    """Add tag options to a parser for set commands.

    :param parser: argparse.Argument parser object.
    :param resource_name: Description of the object being filtered.
    :param enhance_help: A callable accepting a single parameter, the
        (translated) help string, and returning a (translated) help string. May
        be used by a caller wishing to add qualifying text, such as "Applies to
        version XYZ only", to the help strings for all options produced by this
        method.
    """
    tag_group = parser.add_mutually_exclusive_group()
    tag_group.add_argument(
        '--tag',
        action='append',
        dest='tags',
        metavar='<tag>',
        help=enhance_help(
            _("Tag to be removed from the %s "
              "(repeat option to remove multiple tags)") % resource_name))
    tag_group.add_argument(
        '--all-tag',
        action='store_true',
        help=enhance_help(
            _("Clear all tags associated with the %s") % resource_name))


def update_tags_for_set(client, obj, parsed_args):
    """Set the tags on an object.

    :param client: The service client to use setting the tags.
    :param obj: The object (Resource) to set the tags on.
    :param parsed_args: Parsed argument object returned by argparse parse_args.
    """
    if parsed_args.no_tag:
        tags = set()
    else:
        tags = set(obj.tags or [])
    if parsed_args.tags:
        tags |= set(parsed_args.tags)
    if set(obj.tags or []) != tags:
        client.set_tags(obj, sorted(list(tags)))


def update_tags_for_unset(client, obj, parsed_args):
    """Unset the tags on an object.

    :param client: The service client to use unsetting the tags.
    :param obj: The object (Resource) to unset the tags on.
    :param parsed_args: Parsed argument object returned by argparse parse_args.
    """
    tags = set(obj.tags)
    if parsed_args.all_tag:
        tags = set()
    if parsed_args.tags:
        tags -= set(parsed_args.tags)
    if set(obj.tags) != tags:
        client.set_tags(obj, sorted(list(tags)))
