#   Copyright 2019 Red Hat, Inc. All rights reserved.
#
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

import argparse
import mock

from osc_lib.tests import utils as test_utils
from osc_lib.utils import tags


def help_enhancer(_h):
    """A simple helper to validate the ``enhance_help`` kwarg."""
    return ''.join(reversed(_h))


class TestTags(test_utils.TestCase):

    def test_add_tag_filtering_option_to_parser(self):
        parser = argparse.ArgumentParser()
        tags.add_tag_filtering_option_to_parser(parser, 'test')

        parsed_args = parser.parse_args(['--tags', 'tag1,tag2',
                                         '--any-tags', 'tag4',
                                         '--not-tags', 'tag5',
                                         '--not-any-tags', 'tag6'])

        actual = getattr(parsed_args, 'tags', [])
        expected = ['tag1', 'tag2']
        self.assertItemsEqual(expected, actual)

        actual = getattr(parsed_args, 'any_tags', [])
        expected = ['tag4']
        self.assertItemsEqual(expected, actual)

        actual = getattr(parsed_args, 'not_tags', [])
        expected = ['tag5']
        self.assertItemsEqual(expected, actual)

        actual = getattr(parsed_args, 'not_any_tags', [])
        expected = ['tag6']
        self.assertItemsEqual(expected, actual)

    def test_get_tag_filtering_args(self):
        parser = argparse.ArgumentParser()
        tags.add_tag_filtering_option_to_parser(parser, 'test')

        parsed_args = parser.parse_args(['--tags', 'tag1,tag2',
                                         '--any-tags', 'tag4',
                                         '--not-tags', 'tag5',
                                         '--not-any-tags', 'tag6'])
        expected = {'tags': 'tag1,tag2', 'any_tags': 'tag4',
                    'not_tags': 'tag5', 'not_any_tags': 'tag6'}
        args = {}
        tags.get_tag_filtering_args(parsed_args, args)
        self.assertEqual(expected, args)

    def test_add_tag_option_to_parser_for_create(self):
        parser = argparse.ArgumentParser()
        tags.add_tag_option_to_parser_for_create(parser, 'test')

        # Test that --tag and --no-tag are mutually exclusive
        self.assertRaises(SystemExit, parser.parse_args,
                          ['--tag', 'tag1', '--no-tag'])

        parsed_args = parser.parse_args(['--tag', 'tag1'])
        actual = getattr(parsed_args, 'tags', [])
        expected = ['tag1']
        self.assertItemsEqual(expected, actual)

        parsed_args = parser.parse_args(['--no-tag'])
        actual = getattr(parsed_args, 'no-tag', [])
        expected = []
        self.assertItemsEqual(expected, actual)

    def test_add_tag_option_to_parser_for_set(self):
        parser = argparse.ArgumentParser()
        tags.add_tag_option_to_parser_for_set(parser, 'test')

        parsed_args = parser.parse_args(['--tag', 'tag1'])
        actual = getattr(parsed_args, 'tags', [])
        expected = ['tag1']
        self.assertItemsEqual(expected, actual)

        parsed_args = parser.parse_args(['--no-tag'])
        actual = getattr(parsed_args, 'no-tag', [])
        expected = []
        self.assertItemsEqual(expected, actual)

    def test_add_tag_option_to_parser_for_unset(self):
        parser = argparse.ArgumentParser()
        tags.add_tag_option_to_parser_for_unset(parser, 'test')

        # Test that --tag and --all-tag are mutually exclusive
        self.assertRaises(SystemExit, parser.parse_args,
                          ['--tag', 'tag1', '--all-tag'])

        parsed_args = parser.parse_args(['--tag', 'tag1'])
        actual = getattr(parsed_args, 'tags', [])
        expected = ['tag1']
        self.assertItemsEqual(expected, actual)

        parsed_args = parser.parse_args(['--all-tag'])
        actual = getattr(parsed_args, 'all-tag', [])
        expected = []
        self.assertItemsEqual(expected, actual)

    def test_update_tags_for_set(self):
        mock_client = mock.MagicMock()
        mock_obj = mock.MagicMock()
        mock_parsed_args = mock.MagicMock()

        # no-tag True path
        mock_parsed_args.no_tag = True
        mock_parsed_args.tags = ['tag1']
        mock_obj.tags = None
        tags.update_tags_for_set(mock_client, mock_obj, mock_parsed_args)
        mock_client.set_tags.assert_called_once_with(
            mock_obj, list(mock_parsed_args.tags))

        # no-tag False path
        mock_client.set_tags.reset_mock()
        mock_parsed_args.no_tag = False
        mock_parsed_args.tags = ['tag1']
        mock_obj.tags = ['tag2']
        expected_list = ['tag1', 'tag2']
        tags.update_tags_for_set(mock_client, mock_obj, mock_parsed_args)
        mock_client.set_tags.assert_called_once_with(
            mock_obj, expected_list)

        # no new tags path
        mock_client.set_tags.reset_mock()
        mock_parsed_args.no_tag = False
        mock_parsed_args.tags = None
        mock_obj.tags = ['tag2']
        tags.update_tags_for_set(mock_client, mock_obj, mock_parsed_args)
        mock_client.set_tags.assert_not_called()

    def test_update_tags_for_unset(self):
        mock_client = mock.MagicMock()
        mock_obj = mock.MagicMock()
        mock_parsed_args = mock.MagicMock()

        # No new tags
        mock_obj.tags = ['tag1']
        mock_parsed_args.all_tag = False
        mock_parsed_args.tags = None
        tags.update_tags_for_unset(mock_client, mock_obj, mock_parsed_args)
        mock_client.set_tags.assert_not_called()

        # Clear all tags
        mock_obj.tags = ['tag1']
        mock_parsed_args.all_tag = True
        mock_parsed_args.tags = None
        tags.update_tags_for_unset(mock_client, mock_obj, mock_parsed_args)
        mock_client.set_tags.assert_called_once_with(
            mock_obj, [])

        # Remove one tag
        mock_client.set_tags.reset_mock()
        mock_obj.tags = ['tag1', 'tag2']
        mock_parsed_args.all_tag = False
        mock_parsed_args.tags = ['tag2']
        tags.update_tags_for_unset(mock_client, mock_obj, mock_parsed_args)
        mock_client.set_tags.assert_called_once_with(
            mock_obj, ['tag1'])


class TestTagHelps(test_utils.TestCase):

    def _test_tag_method_help(self, meth, exp_normal, exp_enhanced):
        """Vet the help text of the options added by the tag filtering helpers.

        :param meth: One of the ``add_tag_*`` methods.
        :param exp_normal: Expected help output without ``enhance_help``.
        :param exp_enhanced: Expected output with ``enhance_help`` set to
            ``help_enhancer``
        """
        parser = argparse.ArgumentParser()
        meth(parser, 'test')
        self.assertEqual(exp_normal, parser.format_help())

        parser = argparse.ArgumentParser()
        meth(parser, 'test', enhance_help=help_enhancer)
        self.assertEqual(exp_enhanced, parser.format_help())

    def test_add_tag_filtering_option_to_parser(self):
        self._test_tag_method_help(
            tags.add_tag_filtering_option_to_parser,
            """\
usage: run.py [-h] [--tags <tag>[,<tag>,...]] [--any-tags <tag>[,<tag>,...]]
              [--not-tags <tag>[,<tag>,...]]
              [--not-any-tags <tag>[,<tag>,...]]

optional arguments:
  -h, --help            show this help message and exit
  --tags <tag>[,<tag>,...]
                        List test which have all given tag(s) (Comma-separated
                        list of tags)
  --any-tags <tag>[,<tag>,...]
                        List test which have any given tag(s) (Comma-separated
                        list of tags)
  --not-tags <tag>[,<tag>,...]
                        Exclude test which have all given tag(s) (Comma-
                        separated list of tags)
  --not-any-tags <tag>[,<tag>,...]
                        Exclude test which have any given tag(s) (Comma-
                        separated list of tags)
""",
            """\
usage: run.py [-h] [--tags <tag>[,<tag>,...]] [--any-tags <tag>[,<tag>,...]]
              [--not-tags <tag>[,<tag>,...]]
              [--not-any-tags <tag>[,<tag>,...]]

optional arguments:
  -h, --help            show this help message and exit
  --tags <tag>[,<tag>,...]
                        )sgat fo tsil detarapes-ammoC( )s(gat nevig lla evah
                        hcihw tset tsiL
  --any-tags <tag>[,<tag>,...]
                        )sgat fo tsil detarapes-ammoC( )s(gat nevig yna evah
                        hcihw tset tsiL
  --not-tags <tag>[,<tag>,...]
                        )sgat fo tsil detarapes-ammoC( )s(gat nevig lla evah
                        hcihw tset edulcxE
  --not-any-tags <tag>[,<tag>,...]
                        )sgat fo tsil detarapes-ammoC( )s(gat nevig yna evah
                        hcihw tset edulcxE
""")

    def test_add_tag_option_to_parser_for_create(self):
        self._test_tag_method_help(
            tags.add_tag_option_to_parser_for_create,
            """\
usage: run.py [-h] [--tag <tag> | --no-tag]

optional arguments:
  -h, --help   show this help message and exit
  --tag <tag>  Tag to be added to the test (repeat option to set multiple
               tags)
  --no-tag     No tags associated with the test
""",
            """\
usage: run.py [-h] [--tag <tag> | --no-tag]

optional arguments:
  -h, --help   show this help message and exit
  --tag <tag>  )sgat elpitlum tes ot noitpo taeper( tset eht ot dedda eb ot
               gaT
  --no-tag     tset eht htiw detaicossa sgat oN
""")

    def test_add_tag_option_to_parser_for_set(self):
        self._test_tag_method_help(
            tags.add_tag_option_to_parser_for_set,
            """\
usage: run.py [-h] [--tag <tag>] [--no-tag]

optional arguments:
  -h, --help   show this help message and exit
  --tag <tag>  Tag to be added to the test (repeat option to set multiple
               tags)
  --no-tag     Clear tags associated with the test. Specify both --tag and
               --no-tag to overwrite current tags
""",
            """\
usage: run.py [-h] [--tag <tag>] [--no-tag]

optional arguments:
  -h, --help   show this help message and exit
  --tag <tag>  )sgat elpitlum tes ot noitpo taeper( tset eht ot dedda eb ot
               gaT
  --no-tag     sgat tnerruc etirwrevo ot gat-on-- dna gat-- htob yficepS .tset
               eht htiw detaicossa sgat raelC
""")

    def test_add_tag_option_to_parser_for_unset(self):
        self._test_tag_method_help(
            tags.add_tag_option_to_parser_for_unset,
            """\
usage: run.py [-h] [--tag <tag> | --all-tag]

optional arguments:
  -h, --help   show this help message and exit
  --tag <tag>  Tag to be removed from the test (repeat option to remove
               multiple tags)
  --all-tag    Clear all tags associated with the test
""",
            """\
usage: run.py [-h] [--tag <tag> | --all-tag]

optional arguments:
  -h, --help   show this help message and exit
  --tag <tag>  )sgat elpitlum evomer ot noitpo taeper( tset eht morf devomer
               eb ot gaT
  --all-tag    tset eht htiw detaicossa sgat lla raelC
""")
