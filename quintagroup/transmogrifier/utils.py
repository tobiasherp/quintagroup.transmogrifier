# -*- coding: utf-8 -*- äöü (for doctest)
"""
quintagroup.transmogrifier.utils
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
