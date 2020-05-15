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

"""
Helpers for comparing version strings.
"""

import functools
import inspect
import logging

from oslo_config import cfg

from oslo_log._i18n import _


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
_DEPRECATED_EXCEPTIONS = set()


deprecated_opts = [
    cfg.BoolOpt('fatal_deprecations',
                default=False,
                help='Enables or disables fatal status of deprecations.'),
]


_deprecated_msg_with_alternative = _(
    '%(what)s is deprecated as of %(as_of)s in favor of '
    '%(in_favor_of)s and may be removed in %(remove_in)s.')

_deprecated_msg_no_alternative = _(
    '%(what)s is deprecated as of %(as_of)s and may be '
    'removed in %(remove_in)s. It will not be superseded.')

_deprecated_msg_with_alternative_no_removal = _(
    '%(what)s is deprecated as of %(as_of)s in favor of %(in_favor_of)s.')

_deprecated_msg_with_no_alternative_no_removal = _(
    '%(what)s is deprecated as of %(as_of)s. It will not be superseded.')


_RELEASES = {
    # NOTE(morganfainberg): Bexar is used for unit test purposes, it is
    # expected we maintain a gap between Bexar and Folsom in this list.
    'B': 'Bexar',
    'F': 'Folsom',
    'G': 'Grizzly',
    'H': 'Havana',
    'I': 'Icehouse',
    'J': 'Juno',
    'K': 'Kilo',
    'L': 'Liberty',
    'M': 'Mitaka',
    'N': 'Newton',
    'O': 'Ocata',
    'P': 'Pike',
    'Q': 'Queens',
    'R': 'Rocky',
    'S': 'Stein',
    'T': 'Train',
    'U': 'Ussuri',
    'V': 'Victoria',
    'W': 'Wallaby',
}


def register_options():
    """Register configuration options used by this library.

    .. note: This is optional since the options are also registered
        automatically when the functions in this module are used.

    """
    CONF.register_opts(deprecated_opts)


class deprecated(object):
    """A decorator to mark callables as deprecated.

    This decorator logs a deprecation message when the callable it decorates is
    used. The message will include the release where the callable was
    deprecated, the release where it may be removed and possibly an optional
    replacement. It also logs a message when a deprecated exception is being
    caught in a try-except block, but not when subclasses of that exception
    are being caught.

    Examples:

    1. Specifying the required deprecated release

    >>> @deprecated(as_of=deprecated.ICEHOUSE)
    ... def a(): pass

    2. Specifying a replacement:

    >>> @deprecated(as_of=deprecated.ICEHOUSE, in_favor_of='f()')
    ... def b(): pass

    3. Specifying the release where the functionality may be removed:

    >>> @deprecated(as_of=deprecated.ICEHOUSE, remove_in=+1)
    ... def c(): pass

    4. Specifying the deprecated functionality will not be removed:

    >>> @deprecated(as_of=deprecated.ICEHOUSE, remove_in=None)
    ... def d(): pass

    5. Specifying a replacement, deprecated functionality will not be removed:

    >>> @deprecated(as_of=deprecated.ICEHOUSE, in_favor_of='f()',
    ...             remove_in=None)
    ... def e(): pass

    .. warning::

       The hook used to detect when a deprecated exception is being
       *caught* does not work under Python 3. Deprecated exceptions
       are still logged if they are thrown.

    """

    # NOTE(morganfainberg): Bexar is used for unit test purposes, it is
    # expected we maintain a gap between Bexar and Folsom in this list.
    BEXAR = 'B'
    FOLSOM = 'F'
    GRIZZLY = 'G'
    HAVANA = 'H'
    ICEHOUSE = 'I'
    JUNO = 'J'
    KILO = 'K'
    LIBERTY = 'L'
    MITAKA = 'M'
    NEWTON = 'N'
    OCATA = 'O'
    PIKE = 'P'
    QUEENS = 'Q'
    ROCKY = 'R'
    STEIN = 'S'
    TRAIN = 'T'
    USSURI = 'U'

    def __init__(self, as_of, in_favor_of=None, remove_in=2, what=None):
        """Initialize decorator

        :param as_of: the release deprecating the callable. Constants
            are define in this class for convenience.
        :param in_favor_of: the replacement for the callable (optional)
        :param remove_in: an integer specifying how many releases to wait
            before removing (default: 2)
        :param what: name of the thing being deprecated (default: the
            callable's name)

        """
        self.as_of = as_of
        self.in_favor_of = in_favor_of
        self.remove_in = remove_in
        self.what = what

    def __call__(self, func_or_cls):
        report_deprecated = functools.partial(
            deprecation_warning,
            what=self.what or func_or_cls.__name__ + '()',
            as_of=self.as_of,
            in_favor_of=self.in_favor_of,
            remove_in=self.remove_in)

        if inspect.isfunction(func_or_cls):

            @functools.wraps(func_or_cls)
            def wrapped(*args, **kwargs):
                report_deprecated()
                return func_or_cls(*args, **kwargs)
            return wrapped
        elif inspect.isclass(func_or_cls):
            orig_init = func_or_cls.__init__

            @functools.wraps(orig_init, assigned=('__name__', '__doc__'))
            def new_init(self, *args, **kwargs):
                if self.__class__ in _DEPRECATED_EXCEPTIONS:
                    report_deprecated()
                orig_init(self, *args, **kwargs)
            func_or_cls.__init__ = new_init
            _DEPRECATED_EXCEPTIONS.add(func_or_cls)

            if issubclass(func_or_cls, Exception):
                # NOTE(dhellmann): The subclasscheck is called,
                # sometimes, to test whether a class matches the type
                # being caught in an exception. This lets us warn
                # folks that they are trying to catch an exception
                # that has been deprecated. However, under Python 3
                # the test for whether one class is a subclass of
                # another has been optimized so that the abstract
                # check is only invoked in some cases. (See
                # PyObject_IsSubclass in cpython/Objects/abstract.c
                # for the short-cut.)
                class ExceptionMeta(type):
                    def __subclasscheck__(self, subclass):
                        if self in _DEPRECATED_EXCEPTIONS:
                            report_deprecated()
                        return super(ExceptionMeta,
                                     self).__subclasscheck__(subclass)
                func_or_cls.__meta__ = ExceptionMeta
                _DEPRECATED_EXCEPTIONS.add(func_or_cls)

            return func_or_cls
        else:
            raise TypeError('deprecated can be used only with functions or '
                            'classes')


def _get_safe_to_remove_release(release, remove_in):
    # TODO(dstanek): this method will have to be reimplemented once
    #    when we get to the X release because once we get to the Y
    #    release, what is Y+2?
    if remove_in is None:
        remove_in = 0
    new_release = chr(ord(release) + remove_in)
    if new_release in _RELEASES:
        return _RELEASES[new_release]
    else:
        return new_release


def deprecation_warning(what, as_of, in_favor_of=None,
                        remove_in=2, logger=LOG):
    """Warn about the deprecation of a feature.

    :param what: name of the thing being deprecated.
    :param as_of: the release deprecating the callable.
    :param in_favor_of: the replacement for the callable (optional)
    :param remove_in: an integer specifying how many releases to wait
        before removing (default: 2)
    :param logger: the logging object to use for reporting (optional).
    """
    details = dict(what=what,
                   as_of=_RELEASES[as_of],
                   remove_in=_get_safe_to_remove_release(as_of, remove_in))

    if in_favor_of:
        details['in_favor_of'] = in_favor_of
        if remove_in is not None and remove_in > 0:
            msg = _deprecated_msg_with_alternative
        else:
            # There are no plans to remove this function, but it is
            # now deprecated.
            msg = _deprecated_msg_with_alternative_no_removal
    else:
        if remove_in is not None and remove_in > 0:
            msg = _deprecated_msg_no_alternative
        else:
            # There are no plans to remove this function, but it is
            # now deprecated.
            msg = _deprecated_msg_with_no_alternative_no_removal

    report_deprecated_feature(logger, msg, details)


# Track the messages we have sent already. See
# report_deprecated_feature().
_deprecated_messages_sent = {}


def report_deprecated_feature(logger, msg, *args, **kwargs):
    """Call this function when a deprecated feature is used.

    If the system is configured for fatal deprecations then the message
    is logged at the 'critical' level and :class:`DeprecatedConfig` will
    be raised.

    Otherwise, the message will be logged (once) at the 'warn' level.

    :raises: :class:`DeprecatedConfig` if the system is configured for
             fatal deprecations.
    """
    stdmsg = _("Deprecated: %s") % msg
    register_options()
    if CONF.fatal_deprecations:
        logger.critical(stdmsg, *args, **kwargs)
        raise DeprecatedConfig(msg=stdmsg)

    # Using a list because a tuple with dict can't be stored in a set.
    sent_args = _deprecated_messages_sent.setdefault(msg, list())

    if args in sent_args:
        # Already logged this message, so don't log it again.
        return

    sent_args.append(args)
    logger.warning(stdmsg, *args, **kwargs)


class DeprecatedConfig(Exception):
    message = _("Fatal call to deprecated config: %(msg)s")

    def __init__(self, msg):
        super(Exception, self).__init__(self.message % dict(msg=msg))
