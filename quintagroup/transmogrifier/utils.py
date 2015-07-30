# -*- coding: utf-8 -*- äöü (for doctest)
"""
quintagroup.transmogrifier.utils

The functions of this module should depend on standard modules only
(for doctests)
"""


def add_info(transmogrifier, category, section, info):
    """
    Store a chunk of information with the transmogrifier object;
    needed e.g. to access an export_context after the __call__.
    The information is stored in an _collected_info attribute.
    """
    try:
        a = transmogrifier._collected_info
    except AttributeError:
        a = []
        transmogrifier._collected_info = a
    a.append({'category': category,
              'section':  section,
              'info':     info,
              })


def get_info(transmogrifier, category=None, section=None, short=True):
    """
    Get a filtered list of stored information
    """
    res = []
    try:
        rows = transmogrifier._collected_info
    except AttributeError:
        return res
    else:
        for dic in rows:
            if category is not None and dic['category'] != category:
                continue
            if section is not None and dic['section'] != section:
                continue
            if short:
                res.append(dic['info'])
            else:
                res.append(dic)
        return res


def wrapped_tarball(export_context, context):
    """
    Return a tarball, created as an export context, for download
    """
    result = export_result_dict(export_context)
    RESPONSE = context.REQUEST.RESPONSE
    RESPONSE.setHeader('Content-type', 'application/x-gzip')
    RESPONSE.setHeader('Content-disposition',
                       'attachment; filename=%s' % result['filename'])
    return result['tarball']


def export_result_dict(context, steps=None, messages=None):
    """
    Return a dictionary, like returned by SetupTool._doRunExportSteps
    (Products/GenericSetup/tool.py)

    context -- an *export* context!

    (helper for --> wrapped_tarball)
    """
    return {'steps': steps,
            'messages': messages,
            'tarball': context.getArchive(),
            'filename': context.getArchiveFilename()}


def make_safe_decoder(preferred='utf-8', preflist=None, errors='replace',
                      logger=None):
    r"""
    Create a "safe_decode" function which returns unicode for any given
    basestring.

    >>> safe_decode = make_safe_decoder()
    >>> safe_decode('äöü')
    u'\xe4\xf6\xfc'

    If given unicode, this is returned unchanged immediately:
    >>> safe_decode(u'\xe4\xf6\xfc')
    u'\xe4\xf6\xfc'

    Latin-1 strings are the 2nd guess by default:
    >>> u'\xe4\xf6\xfc'.encode('latin1')
    '\xe4\xf6\xfc'
    >>> safe_decode('\xe4\xf6\xfc')
    u'\xe4\xf6\xfc'

    To try 'utf-8' only:

    >>> accept_unicode_or_utf8 = make_safe_decoder(preflist=['utf-8'],
    ...                                            errors='strict')
    >>> accept_unicode_or_utf8('\xe4\xf6\xfc')
    ...                               # doctest: +IGNORE_EXCEPTION_DETAIL +SKIP
    u'\xe4\xf6\xfc'
    Traceback (most recent call last):
      ...
        return codecs.utf_8_decode(input, errors, True)
    UnicodeDecodeError: 'utf8' codec can't decode byte 0xe4 in position 0: invalid continuation byte
    """
    if preflist is None:
        preflist = ['utf-8', 'latin-1']
    if preferred and preferred not in preflist:
        preflist.insert(0, preferred)

    def safe_decode_inner(s):
        """
        Take any basestring and return unicode
        """
        if isinstance(s, unicode):
            return s
        for encoding in preflist:
            try:
                return s.decode(encoding, 'strict')
            except UnicodeDecodeError:
                if logger is not None:
                    logger.warn("Assuming %(encoding)r, can't decode %(s)r",
                                locals())
        if errors != 'strict' and preferred:
            return s.decode(preferred, errors)
        raise

    return safe_decode_inner

# default version, accepting utf-8 and latin-1:
safe_decode = make_safe_decoder()


def make_skipfunc(whitelist=None, blacklist=None,
                  default_blacklist=None,
                  verbose=False):
    r"""
    Return a function which checks a given string (e.g. a property name)
    against a whitelist *or* a blacklist.
    Only one of them may be given!

    The sanity checks for whitelist and blacklist arguments are performed by
    this factory; when used, the given value is checked against (at most) one
    of them.

    The return value tells whether to *skip* the given argument;
    thus, it is False for "good" values!

    >>> skip = make_skipfunc(whitelist='one\ntwo')
    >>> skip('one')
    False
    >>> skip('three')
    True

    >>> make_skipfunc(blacklist='one\ntwo')('three')
    False

    The entries of <default_blacklist> are used if no whitelist is given:

    >>> kwargs = dict(default_blacklist='oddkey')
    >>> default_skipfunc = make_skipfunc(**kwargs)
    >>> default_skipfunc('oddkey')
    True

    The whitelist and blacklist arguments are intended for configurable values,
    e.g. in a section; the default_blacklist argument is usually hardcoded
    and will have effect *unless a whitelist was given*:

    >>> kwargs['whitelist'] = kwargs['default_blacklist']
    >>> skip_oddkey = make_skipfunc(**kwargs)
    >>> skip_oddkey('oddkey')
    False
    >>> skip_oddkey('anyother')
    True

    If even the default_blacklist is empty, nothing is skipped:

    >>> skip_none = make_skipfunc()
    >>> skip_none('oddkey')
    False

    For development, you can specify verbose=True; this will give you
    a line of output to stdout for every call to your skip function:

    >>> skip_none = make_skipfunc(verbose=True)
    >>> skip_none('oddkey')
    skip 'oddkey'? Don't skip anything --> False
    False

    """
    assert not (whitelist and blacklist)
    def make_set(s):
        if s is None:
            return set()
        if isinstance(s, basestring):
            s = filter(None,
                       [item.strip()
                        for item in s.splitlines()])
        return set(s)

    whitelist = make_set(whitelist)
    has_whitelist = bool(whitelist)

    if has_whitelist:
        has_blacklist = False
    else:
        blacklist = make_set(blacklist)
        blacklist.update(make_set(default_blacklist))
        has_blacklist = bool(blacklist)

    def check_whitelist(s):
        return s not in whitelist

    def check_blacklist(s):
        return s in blacklist

    def return_false(s):
        return False

    def check_whitelist_verbose(s):
        res = s not in whitelist
        print 'skip %r? whitelist %s --> %r' \
                % (s, whitelist, res)
        return res

    def check_blacklist_verbose(s):
        res = s in blacklist
        print 'skip %r? blacklist %s --> %r' \
                % (s, blacklist, res)
        return res

    def return_false_verbose(s):
        res = False
        print 'skip %r? Don\'t skip anything --> %r' \
                % (s, res)
        return res

    if verbose:
        if has_whitelist:
            return check_whitelist_verbose
        elif has_blacklist:
            return check_blacklist_verbose
        else:
            return return_false_verbose
    else:
        if has_whitelist:
            return check_whitelist
        elif has_blacklist:
            return check_blacklist
        else:
            return return_false


if __name__ == '__main__':
    import doctest
    doctest.testmod()
