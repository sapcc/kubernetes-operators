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

import datetime
import debtcollector
import functools
import io
import itertools
import logging
import logging.config
import logging.handlers
import re
import socket
import sys
import traceback

from dateutil import tz

from oslo_context import context as context_utils
from oslo_serialization import jsonutils
from oslo_utils import encodeutils


def _dictify_context(context):
    if getattr(context, 'get_logging_values', None):
        return context.get_logging_values()
    elif getattr(context, 'to_dict', None):
        debtcollector.deprecate(
            'The RequestContext.get_logging_values() '
            'method should be defined for logging context specific '
            'information.  The to_dict() method is deprecated '
            'for oslo.log use.', version='3.8.0', removal_version='5.0.0')
        return context.to_dict()
    # This dict only style logging format will become deprecated
    # when projects using a dictionary object for context are updated
    elif isinstance(context, dict):
        return context

    return {}


# A configuration object is given to us when the application registers
# the logging options.
_CONF = None


def _store_global_conf(conf):
    global _CONF
    _CONF = conf


def _update_record_with_context(record):
    """Given a log record, update it with context information.

    The request context, if there is one, will either be passed with the
    incoming record or in the global thread-local store.
    """
    context = record.__dict__.get(
        'context',
        context_utils.get_current()
    )
    if context:
        d = _dictify_context(context)
        # Copy the context values directly onto the record so they can be
        # used by the formatting strings.
        for k, v in d.items():
            setattr(record, k, v)

    return context


def _ensure_unicode(msg):
    """Do our best to turn the input argument into a unicode object.
    """
    if isinstance(msg, str):
        return msg
    if not isinstance(msg, bytes):
        return str(msg)
    return encodeutils.safe_decode(
        msg,
        incoming='utf-8',
        errors='xmlcharrefreplace')


def _get_error_summary(record):
    """Return the error summary

    If there is no active exception, return the default.

    If the record is being logged below the warning level, return an
    empty string.

    If there is an active exception, format it and return the
    resulting string.

    """
    error_summary = ''
    if record.levelno < logging.WARNING:
        return ''

    if record.exc_info:
        # Save the exception we were given so we can include the
        # summary in the log line.
        exc_info = record.exc_info
    else:
        # Check to see if there is an active exception that was
        # not given to us explicitly. If so, save it so we can
        # include the summary in the log line.
        exc_info = sys.exc_info()
        # If we get (None, None, None) because there is no
        # exception, convert it to a simple None to make the logic
        # that uses the value simpler.
        if not exc_info[0]:
            exc_info = None
        elif exc_info[0] in (TypeError, ValueError,
                             KeyError, AttributeError, ImportError):
            # NOTE(dhellmann): Do not include information about
            # common built-in exceptions used to detect cases of
            # bad or missing data. We don't use isinstance() here
            # to limit this filter to only the built-in
            # classes. This check is only performed for cases
            # where the exception info is being detected
            # automatically so if a caller gives us an exception
            # we will definitely log it.
            exc_info = None

    # If we have an exception, format it to be included in the
    # output.
    if exc_info:
        try:
            # Build the exception summary in the line with the
            # primary log message, to serve as a mnemonic for error
            # and warning cases.
            error_summary = traceback.format_exception_only(
                exc_info[0],
                exc_info[1],
            )[0].rstrip()
            # If the exc_info wasn't explicitly passed to us, take only the
            # first line of it. _Remote exceptions from oslo.messaging append
            # the full traceback to the exception message, so we want to avoid
            # outputting the traceback unless we've been passed exc_info
            # directly (via LOG.exception(), for example).
            if not record.exc_info:
                error_summary = error_summary.split('\n', 1)[0]
        except TypeError as type_err:
            # Work around https://bugs.python.org/issue28603
            error_summary = "<exception with %s>" % str(type_err)
        finally:
            # Remove the local reference to the exception and
            # traceback to avoid a memory leak through the frame
            # references.
            del exc_info

    return error_summary


class _ReplaceFalseValue(dict):
    def __getitem__(self, key):
        return dict.get(self, key, None) or '-'


_MSG_KEY_REGEX = re.compile(r'(%+)\((\w+)\)')


def _json_dumps_with_fallback(obj):
    # Bug #1593641: If an object cannot be serialized to JSON, convert
    # it using repr() to prevent serialization errors. Using repr() is
    # not ideal, but serialization errors are unexpected on logs,
    # especially when the code using logs is not aware that the
    # JSONFormatter will be used.
    convert = functools.partial(jsonutils.to_primitive, fallback=repr)
    return jsonutils.dumps(obj, default=convert)


class JSONFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%'):
        # NOTE(sfinucan) we ignore the fmt and style arguments, but they're
        # still there since logging.config.fileConfig passes the former in
        # Python < 3.2 and both in Python >= 3.2
        self.datefmt = datefmt
        try:
            self.hostname = socket.gethostname()
        except socket.error:
            self.hostname = None

    def formatException(self, ei, strip_newlines=True):
        try:
            lines = traceback.format_exception(*ei)
        except TypeError as type_error:
            # Work around https://bugs.python.org/issue28603
            msg = str(type_error)
            lines = ['<Unprintable exception due to %s>\n' % msg]
        if strip_newlines:
            lines = [filter(
                lambda x: x,
                line.rstrip().splitlines()) for line in lines]
            lines = list(itertools.chain(*lines))
        return lines

    def format(self, record):
        args = record.args
        if isinstance(args, dict):
            msg_keys = _MSG_KEY_REGEX.findall(record.msg)
            # NOTE(bnemec): The logic around skipping escaped placeholders is
            # tricky and error-prone to include in the regex.  Much easier to
            # just grab them all and filter after the fact.
            msg_keys = [m[1] for m in msg_keys if len(m[0]) == 1]
            # If no named keys were found, then the entire dict must have been
            # the value to be formatted.  Don't filter anything.
            if msg_keys:
                args = {k: v for k, v in args.items() if k in msg_keys}
        message = {'message': record.getMessage(),
                   'asctime': self.formatTime(record, self.datefmt),
                   'name': record.name,
                   'msg': record.msg,
                   'args': args,
                   'levelname': record.levelname,
                   'levelno': record.levelno,
                   'pathname': record.pathname,
                   'filename': record.filename,
                   'module': record.module,
                   'lineno': record.lineno,
                   'funcname': record.funcName,
                   'created': record.created,
                   'msecs': record.msecs,
                   'relative_created': record.relativeCreated,
                   'thread': record.thread,
                   'thread_name': record.threadName,
                   'process_name': record.processName,
                   'process': record.process,
                   'traceback': None,
                   'hostname': self.hostname,
                   'error_summary': _get_error_summary(record)}

        # Build the extra values that were given to us, including
        # the context.
        context = _update_record_with_context(record)
        if hasattr(record, 'extra'):
            extra = record.extra.copy()
        else:
            extra = {}
        for key in getattr(record, 'extra_keys', []):
            if key not in extra:
                extra[key] = getattr(record, key)
        # The context object might have been given from the logging call. if
        # that was the case, it'll come in the 'extra' entry already. If not,
        # lets use the context we fetched above. In either case, we explode it
        # into the 'context' entry because the values are more useful than the
        # object reference.
        if 'context' in extra and extra['context']:
            message['context'] = _dictify_context(extra['context'])
        elif context:
            message['context'] = _dictify_context(context)
        else:
            message['context'] = {}
        extra.pop('context', None)
        message['extra'] = extra

        if record.exc_info:
            message['traceback'] = self.formatException(record.exc_info)

        return _json_dumps_with_fallback(message)


class FluentFormatter(logging.Formatter):
    """A formatter for fluentd.

    format() returns dict, not string.
    It expects to be used by fluent.handler.FluentHandler.
    (included in fluent-logger-python)

    .. versionadded:: 3.17
    """

    def __init__(self, fmt=None, datefmt=None, style='%s'):
        # NOTE(sfinucan) we ignore the fmt and style arguments for the same
        # reason as JSONFormatter.
        self.datefmt = datefmt
        try:
            self.hostname = socket.gethostname()
        except socket.error:
            self.hostname = None
        self.cmdline = " ".join(sys.argv)

    def formatException(self, exc_info, strip_newlines=True):
        try:
            lines = traceback.format_exception(*exc_info)
        except TypeError as type_error:
            # Work around https://bugs.python.org/issue28603
            msg = str(type_error)
            lines = ['<Unprintable exception due to %s>\n' % msg]
        if strip_newlines:
            lines = functools.reduce(lambda a,
                                     line: a + line.rstrip().splitlines(),
                                     lines, [])
        return lines

    def format(self, record):
        message = {'message': record.getMessage(),
                   'time': self.formatTime(record, self.datefmt),
                   'name': record.name,
                   'level': record.levelname,
                   'filename': record.filename,
                   'lineno': record.lineno,
                   'module': record.module,
                   'funcname': record.funcName,
                   'process_name': record.processName,
                   'cmdline': self.cmdline,
                   'hostname': self.hostname,
                   'traceback': None,
                   'error_summary': _get_error_summary(record)}

        # Build the extra values that were given to us, including
        # the context.
        context = _update_record_with_context(record)
        if hasattr(record, 'extra'):
            extra = record.extra.copy()
        else:
            extra = {}
        for key in getattr(record, 'extra_keys', []):
            if key not in extra:
                extra[key] = getattr(record, key)
        # The context object might have been given from the logging call. if
        # that was the case, it'll come in the 'extra' entry already. If not,
        # lets use the context we fetched above. In either case, we explode it
        # into the extra dictionary because the values are more useful than the
        # object reference.
        if 'context' in extra and extra['context']:
            message['context'] = _dictify_context(extra['context'])
        elif context:
            message['context'] = _dictify_context(context)
        else:
            message['context'] = {}
        extra.pop('context', None)
        # NOTE(vdrok): try to dump complex objects
        primitive_types = (str, int, bool, type(None), float, list, dict)
        for key, value in extra.items():
            if not isinstance(value, primitive_types):
                extra[key] = _json_dumps_with_fallback(value)
        message['extra'] = extra

        if record.exc_info:
            message['traceback'] = self.formatException(record.exc_info)

        return message


class ContextFormatter(logging.Formatter):
    """A context.RequestContext aware formatter configured through flags.

    The flags used to set format strings are: logging_context_format_string
    and logging_default_format_string.  You can also specify
    logging_debug_format_suffix to append extra formatting if the log level is
    debug.

    The standard variables available to the formatter are listed at:
    http://docs.python.org/library/logging.html#formatter

    In addition to the standard variables, one custom variable is
    available to both formatting string: `isotime` produces a
    timestamp in ISO8601 format, suitable for producing
    RFC5424-compliant log messages.

    Furthermore, logging_context_format_string has access to all of
    the data in a dict representation of the context.
    """

    def __init__(self, *args, **kwargs):
        """Initialize ContextFormatter instance

        Takes additional keyword arguments which can be used in the message
        format string.

        :keyword project: project name
        :type project: string
        :keyword version: project version
        :type version: string

        """

        self.project = kwargs.pop('project', 'unknown')
        self.version = kwargs.pop('version', 'unknown')
        self.conf = kwargs.pop('config', _CONF)

        logging.Formatter.__init__(self, *args, **kwargs)

    def format(self, record):
        """Uses contextstring if request_id is set, otherwise default."""
        # store project info
        record.project = self.project
        record.version = self.version

        # FIXME(dims): We need a better way to pick up the instance
        # or instance_uuid parameters from the kwargs from say
        # LOG.info or LOG.warn
        instance_extra = ''
        instance = getattr(record, 'instance', None)
        instance_uuid = getattr(record, 'instance_uuid', None)
        context = _update_record_with_context(record)
        if instance:
            try:
                instance_extra = (self.conf.instance_format
                                  % instance)
            except TypeError:
                instance_extra = instance
        elif instance_uuid:
            instance_extra = (self.conf.instance_uuid_format
                              % {'uuid': instance_uuid})
        elif context:
            # FIXME(dhellmann): We should replace these nova-isms with
            # more generic handling in the Context class.  See the
            # app-agnostic-logging-parameters blueprint.
            instance = getattr(context, 'instance', None)
            instance_uuid = getattr(context, 'instance_uuid', None)

            # resource_uuid was introduced in oslo_context's
            # RequestContext
            resource_uuid = getattr(context, 'resource_uuid', None)

            if instance:
                instance_extra = (self.conf.instance_format
                                  % {'uuid': instance})
            elif instance_uuid:
                instance_extra = (self.conf.instance_uuid_format
                                  % {'uuid': instance_uuid})
            elif resource_uuid:
                instance_extra = (self.conf.instance_uuid_format
                                  % {'uuid': resource_uuid})

        record.instance = instance_extra

        # NOTE(sdague): default the fancier formatting params
        # to an empty string so we don't throw an exception if
        # they get used
        for key in ('instance', 'color', 'user_identity', 'resource',
                    'user_name', 'project_name'):
            if key not in record.__dict__:
                record.__dict__[key] = ''

        # Set the "user_identity" value of "logging_context_format_string"
        # by using "logging_user_identity_format" and
        # get_logging_values of oslo.context.
        if context:
            record.user_identity = (
                self.conf.logging_user_identity_format %
                _ReplaceFalseValue(_dictify_context(context))
            )

        if record.__dict__.get('request_id'):
            fmt = self.conf.logging_context_format_string
        else:
            fmt = self.conf.logging_default_format_string

        # Cache the formatted traceback on the record, Logger will
        # respect our formatted copy
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info, record)

        record.error_summary = _get_error_summary(record)
        if '%(error_summary)s' in fmt:
            # If we have been told explicitly how to format the error
            # summary, make sure there is always a default value for
            # it.
            record.error_summary = record.error_summary or '-'
        elif record.error_summary:
            # If we have not been told how to format the error and
            # there is an error to summarize, make sure the format
            # string includes the bits we need to include it.
            fmt += ': %(error_summary)s'

        if (record.levelno == logging.DEBUG and
                self.conf.logging_debug_format_suffix):
            fmt += " " + self.conf.logging_debug_format_suffix

        self._compute_iso_time(record)

        if sys.version_info < (3, 2):
            self._fmt = fmt
        else:
            self._style = logging.PercentStyle(fmt)
            self._fmt = self._style._fmt

        try:
            return logging.Formatter.format(self, record)
        except TypeError as err:
            # Something went wrong, report that instead so we at least
            # get the error message.
            record.msg = 'Error formatting log line msg={!r} err={!r}'.format(
                record.msg, err).replace('%', '*')
            return logging.Formatter.format(self, record)

    def formatException(self, exc_info, record=None):
        """Format exception output with CONF.logging_exception_prefix."""
        if not record:
            try:
                return logging.Formatter.formatException(self, exc_info)
            except TypeError as type_error:
                # Work around https://bugs.python.org/issue28603
                msg = str(type_error)
                return '<Unprintable exception due to %s>\n' % msg

        stringbuffer = io.StringIO()
        try:
            traceback.print_exception(exc_info[0], exc_info[1], exc_info[2],
                                      None, stringbuffer)
        except TypeError as type_error:
            # Work around https://bugs.python.org/issue28603
            msg = str(type_error)
            stringbuffer.write('<Unprintable exception due to %s>\n' % msg)

        lines = stringbuffer.getvalue().split('\n')
        stringbuffer.close()

        if self.conf.logging_exception_prefix.find('%(asctime)') != -1:
            record.asctime = self.formatTime(record, self.datefmt)

        self._compute_iso_time(record)

        formatted_lines = []
        for line in lines:
            pl = self.conf.logging_exception_prefix % record.__dict__
            fl = '%s%s' % (pl, line)
            formatted_lines.append(fl)
        return '\n'.join(formatted_lines)

    def _compute_iso_time(self, record):
        # set iso8601 timestamp
        localtz = tz.tzlocal()
        record.isotime = datetime.datetime.fromtimestamp(
            record.created).replace(tzinfo=localtz).isoformat()
        if record.created == int(record.created):
            # NOTE(stpierre): when the timestamp includes no
            # microseconds -- e.g., 1450274066.000000 -- then the
            # microseconds aren't included in the isoformat() time. As
            # a result, in literally one in a million cases
            # isoformat() looks different. This adds microseconds when
            # that happens.
            record.isotime = "%s.000000%s" % (record.isotime[:-6],
                                              record.isotime[-6:])
