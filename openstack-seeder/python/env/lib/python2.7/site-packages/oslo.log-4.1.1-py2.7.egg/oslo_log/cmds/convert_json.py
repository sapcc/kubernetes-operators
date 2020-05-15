#!/usr/bin/env python
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

from __future__ import print_function

import argparse
import collections
import functools
import sys
import time

from oslo_serialization import jsonutils
from oslo_utils import importutils

from oslo_log import log

termcolor = importutils.try_import('termcolor')


_USE_COLOR = False
DEFAULT_LEVEL_KEY = 'levelname'
DEFAULT_TRACEBACK_KEY = 'traceback'


def main():
    global _USE_COLOR
    args = parse_args()
    _USE_COLOR = args.color
    formatter = functools.partial(
        console_format,
        args.prefix,
        args.locator,
        loggers=args.loggers,
        levels=args.levels,
        level_key=args.levelkey,
        traceback_key=args.tbkey,
        )
    if args.lines:
        # Read backward until we find all of our newline characters
        # or reach the beginning of the file
        args.file.seek(0, 2)
        newlines = 0
        pos = args.file.tell()
        while newlines <= args.lines and pos > 0:
            pos = pos - 1
            args.file.seek(pos)
            if args.file.read(1) == '\n':
                newlines = newlines + 1
    try:
        for line in reformat_json(args.file, formatter, args.follow):
            print(line)
    except KeyboardInterrupt:
        sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("file",
                        nargs='?', default=sys.stdin,
                        type=argparse.FileType(),
                        help="JSON log file to read from (if not provided"
                             " standard input is used instead)")
    parser.add_argument("--prefix",
                        default='%(asctime)s.%(msecs)03d'
                                ' %(process)s %(levelname)s %(name)s',
                        help="Message prefixes")
    parser.add_argument("--locator",
                        default='[%(funcname)s %(pathname)s:%(lineno)s]',
                        help="Locator to append to DEBUG records")
    parser.add_argument("--levelkey",
                        default=DEFAULT_LEVEL_KEY,
                        help="Key in the JSON record where the level is held")
    parser.add_argument("--tbkey",
                        default=DEFAULT_TRACEBACK_KEY,
                        help="Key in the JSON record where the"
                             " traceback/exception is held")
    parser.add_argument("-c", "--color",
                        action='store_true', default=False,
                        help="Color log levels (requires `termcolor`)")
    parser.add_argument("-f", "--follow",
                        action='store_true', default=False,
                        help="Continue parsing new data until"
                             " KeyboardInterrupt")
    parser.add_argument("-n", "--lines",
                        required=False, type=int,
                        help="Last N number of records to view."
                             " (May show less than N records when used"
                             " in conjuction with --loggers or --levels)")
    parser.add_argument("--loggers",
                        nargs='*', default=[],
                        help="only return results matching given logger(s)")
    parser.add_argument("--levels",
                        nargs='*', default=[],
                        help="Only return lines matching given log level(s)")
    args = parser.parse_args()
    if args.color and not termcolor:
        raise ImportError("Coloring requested but `termcolor` is not"
                          " importable")
    return args


def colorise(key, text=None):
    if text is None:
        text = key
    if not _USE_COLOR:
        return text
    colors = {
        'exc': ('red', ['reverse', 'bold']),
        'FATAL': ('red', ['reverse', 'bold']),
        'ERROR': ('red', ['bold']),
        'WARNING': ('yellow', ['bold']),
        'WARN': ('yellow', ['bold']),
        'INFO': ('white', ['bold']),
    }
    color, attrs = colors.get(key, ('', []))
    if color:
        return termcolor.colored(text, color=color, attrs=attrs)
    return text


def warn(prefix, msg):
    return "%s: %s" % (colorise('exc', prefix), msg)


def reformat_json(fh, formatter, follow=False):
    # using readline allows interactive stdin to respond to every line
    while True:
        line = fh.readline()
        if not line:
            if follow:
                time.sleep(0.1)
                continue
            else:
                break
        line = line.strip()
        if not line:
            continue
        try:
            record = jsonutils.loads(line)
        except ValueError:
            yield warn("Not JSON", line)
            continue
        for out_line in formatter(record):
            yield out_line


def console_format(prefix, locator, record, loggers=[], levels=[],
                   level_key=DEFAULT_LEVEL_KEY,
                   traceback_key=DEFAULT_TRACEBACK_KEY):
    # Provide an empty string to format-specifiers the record is
    # missing, instead of failing. Doesn't work for non-string
    # specifiers.
    record = collections.defaultdict(str, record)
    # skip if the record doesn't match a logger we are looking at
    if loggers:
        name = record.get('name')
        if not any(name.startswith(n) for n in loggers):
            return
    if levels:
        if record.get(level_key) not in levels:
            return
    levelname = record.get(level_key)
    if levelname:
        record[level_key] = colorise(levelname)

    try:
        prefix = prefix % record
    except TypeError:
        # Thrown when a non-string format-specifier can't be filled in.
        # Dict comprehension cleans up the output
        yield warn('Missing non-string placeholder in record',
                   {str(k): str(v) if isinstance(v, str) else v
                    for k, v in record.items()})
        return

    locator = ''
    if (record.get('levelno', 100) <= log.DEBUG or levelname == 'DEBUG'):
        locator = locator % record

    yield ' '.join(x for x in [prefix, record['message'], locator] if x)

    tb = record.get(traceback_key)
    if tb:
        if type(tb) is str:
            tb = tb.rstrip().split("\n")
        for tb_line in tb:
            yield ' '.join([prefix, tb_line])


if __name__ == '__main__':
    main()
