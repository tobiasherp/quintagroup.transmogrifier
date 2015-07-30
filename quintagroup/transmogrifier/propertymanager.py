from zExceptions import BadRequest
from copy import deepcopy

from zope.interface import classProvides, implements
from lxml import etree

from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher
from quintagroup.transmogrifier.utils import make_skipfunc

from OFS.interfaces import IPropertyManager
from Products.GenericSetup.utils import PropertyManagerHelpers, NodeAdapterBase


class Helper(PropertyManagerHelpers, NodeAdapterBase):
    """ We need this class because PropertyManagerHelpers in _initProperties
        method uses _convertToBoolean and _getNodeText methods from
        NodeAdapterBase class.
    """

    _encoding = 'utf-8'  # overridden by __init__; preserved for subclassing

    def __init__(self, encoding='utf-8', safe_decode=None,
                 whitelist=None, blacklist=None):
        """
        safe_decode -- a function which will decode all given non-unicode strings
                       to unicode without raising exceptions

        whitelist -- a whitelist of properties to be read
        blacklist -- a blacklist of properties to be skipped
                     (only one of those can be specified)

        Unless a whitelist is given, 'i18n_domain' properties are skipped.
        """
        self._skip_this = make_skipfunc(whitelist, blacklist,
                                        default_blacklist=['i18n_domain'])
        self._encoding = encoding or 'utf-8'
        self._safe_decode = safe_decode or None

    def _getNodeText(self, node):
        # We override method in NodeAdapterBase, because it return bad property value.
        # When properties are extracted newline charcters and indentation were added to
        # them, but these aren't stripped on import. Maybe this method doesn't handle
        # properly multiline string values, but it is needed for importing.
        text = ''
        for child in node:
            if child.tag != '#text':
                continue
            text += child.text.strip()
        return text

    def _extractProperties(self):
        fragment = etree.Element("root")
        # if safe_decode is given, use it for *all* strings, including unicode;
        # it might serve additional purposes, e.g. removal of vertical tabs etc.
        safe_decode = self._safe_decode
        skip = self._skip_this

        for prop_map in self.context._propertyMap():
            prop_id = prop_map['id']
            if skip(prop_id):
                continue

            # Don't export read-only nodes
            if 'w' not in prop_map.get('mode', 'wd'):
                continue

            node = etree.SubElement(fragment, 'property')
            node.attrib['name'] = prop_id

            prop = self.context.getProperty(prop_id)
            if isinstance(prop, (tuple, list)):
                try:
                    for value in prop:
                        if isinstance(value, basestring):
                            if safe_decode is not None:
                                value = safe_decode(value)
                            elif isinstance(value, str):
                                value = value.decode(self._encoding)
                        child = etree.SubElement(node, 'element')
                        child.text = value
                        node.append(child)
                except ValueError as e:
                    print e
                    print 'value: %(value)r (1)' % locals()
                    raise
            else:
                try:
                    if prop_map.get('type') == 'boolean':
                        prop = unicode(bool(prop))
                    elif not isinstance(prop, basestring):
                        prop = unicode(prop)
                    elif safe_decode is not None:
                        prop = safe_decode(prop)
                    elif isinstance(prop, str):
                        prop = prop.decode(self._encoding)
                    node.text = prop
                except ValueError as e:
                    print e
                    print 'prop: %(prop)r (2)' % locals()
                    raise

            if 'd' in prop_map.get('mode', 'wd') and not prop_id == 'title':
                prop_type = prop_map.get('type', 'string')
                node.attrib['type'] = unicode(prop_type)
                select_variable = prop_map.get('select_variable', None)
                if select_variable is not None:
                    node.attrib['select_variable'] = select_variable

            if hasattr(self, '_i18n_props') and prop_id in self._i18n_props:
                node.attrib['i18n:translate'] = ''

            fragment.append(node)

        return fragment.iter(tag='property')

    def _initProperties(self, node):
        obj = self.context
        if 'i18n:domain' in node.attrib:
            i18n_domain = str(node.attrib['i18n:domain'])
            obj._updateProperty('i18n_domain', i18n_domain)
        for child in node.iter(tag='property'):
            prop_id = str(child.attrib['name'])
            prop_map = obj.propdict().get(prop_id, None)
            if prop_map is None:
                if 'type' in child.attrib:
                    val = str(child.attrib.get('select_variable', ''))
                    prop_type = str(child.attrib['type'])
                    obj._setProperty(prop_id, val, prop_type)
                    prop_map = obj.propdict().get(prop_id, None)
                else:
                    raise ValueError("undefined property '%s'" % prop_id)

            if not 'w' in prop_map.get('mode', 'wd'):
                raise BadRequest('%s cannot be changed' % prop_id)

            elements = []
            remove_elements = []
            for sub in child:
                if sub.tag == 'element':
                    if len(sub) > 0:
                        value = sub[0].nodeValue.strip()
                        if isinstance(value, unicode):
                            value = value.encode(self._encoding)
                        if self._convertToBoolean(sub.attrib['remove']
                                                  or 'False'):
                            remove_elements.append(value)
                            if value in elements:
                                elements.remove(value)
                        else:
                            elements.append(value)
                            if value in remove_elements:
                                remove_elements.remove(value)

            if elements or prop_map.get('type') == 'multiple selection':
                prop_value = tuple(elements) or ()
            elif prop_map.get('type') == 'boolean':
                prop_value = self._convertToBoolean(self._getNodeText(child))
            elif isinstance(child.text, unicode):
                prop_value = child.text.encode(self._encoding)
            else:
                # if we pass a *string* to _updateProperty, all other values
                # are converted to the right type
                prop_value = child.text

            if not self._convertToBoolean(child.attrib.get('purge') or 'True'):
                # If the purge attribute is False, merge sequences
                prop = obj.getProperty(prop_id)
                if isinstance(prop, (tuple, list)):
                    prop_value = (tuple([p for p in prop
                                         if p not in prop_value and
                                            p not in remove_elements]) +
                                  tuple(prop_value))

            obj._updateProperty(prop_id, prop_value)


class PropertiesExporterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context

        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.fileskey = options.get('files-key', '_files').strip()

        self.excludekey = defaultMatcher(options, 'exclude-key', name, 'excluded_properties')
        self.exclude = filter(None, [i.strip() for i in
                              options.get('exclude', '').splitlines()])

        # helper_kwargs are currently the only possibility to pass arguments
        # to the helper, e.g. a safe_decode function.
        # They can only be given by calling code, rather than by configuration.
        helper_kwargs = options.get('helper_kwargs', {})
        self.helper = Helper(**helper_kwargs)
        self.doc = etree.Element('properties')
        self.helper._doc = self.doc

    def __iter__(self):
        helper = self.helper
        doc = self.doc

        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]

            if not pathkey:
                yield item
                continue

            path = item[pathkey]
            obj = self.context.unrestrictedTraverse(path, None)
            if obj is None:         # path doesn't exist
                yield item
                continue

            if IPropertyManager.providedBy(obj):
                data = None
                excludekey = self.excludekey(*item.keys())[0]
                excluded_props = tuple(self.exclude)
                if excludekey:
                    excluded_props = tuple(set(item[excludekey]) | set(excluded_props))

                helper.context = obj
                for elem in helper._extractProperties():
                    if elem.attrib['name'] not in excluded_props:
                        doc.append(deepcopy(elem))
                if len(doc):
                    data = etree.tostring(doc, xml_declaration=True,
                                          encoding='utf-8', pretty_print=True)
                    doc.clear()

                if data:
                    item.setdefault(self.fileskey, {})
                    item[self.fileskey]['propertymanager'] = {
                        'name': '.properties.xml',
                        'data': data,
                    }

            yield item


class PropertiesImporterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context

        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.fileskey = defaultMatcher(options, 'files-key', name, 'files')

        self.excludekey = defaultMatcher(options, 'exclude-key', name, 'excluded_properties')
        self.exclude = filter(None, [i.strip() for i in
                            options.get('exclude', '').splitlines()])

        helper_kwargs = options.get('helper_kwargs', {})
        self.helper = Helper(**helper_kwargs)

    def __iter__(self):
        helper = self.helper

        for item in self.previous:
            pathkey = self.pathkey(*item.keys())[0]
            fileskey = self.fileskey(*item.keys())[0]

            if not (pathkey and fileskey):
                yield item
                continue
            if 'propertymanager' not in item[fileskey]:
                yield item
                continue

            path = item[pathkey]
            obj = self.context.unrestrictedTraverse(path, None)
            if obj is None:         # path doesn't exist
                yield item
                continue

            if IPropertyManager.providedBy(obj):
                data = None
                excludekey = self.excludekey(*item.keys())[0]
                excluded_props = self.exclude
                if excludekey:
                    excluded_props = tuple(set(item[excludekey]) | set(excluded_props))

                data = item[fileskey]['propertymanager']['data']
                doc = etree.fromstring(data)
                for child in doc:
                    if child.tag != 'property':
                        continue
                    if child.attrib['name'] in excluded_props:
                        doc.remove(child)

                helper.context = obj
                helper._initProperties(doc)

            yield item
