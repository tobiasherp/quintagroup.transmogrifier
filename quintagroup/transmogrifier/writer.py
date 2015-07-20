import mimetypes
import time

from zope.interface import classProvides, implements

from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher

from Products.GenericSetup import context
from Products.CMFCore import utils

# import monkey patches for GS TarballContext
import quintagroup.transmogrifier.patches

class WriterSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.context = transmogrifier.context

        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.fileskey = defaultMatcher(options, 'files-key', name, 'files')

        if 'prefix' in options:
            self.prefix = options['prefix'].strip()
        else:
            self.prefix = ''

        context_type = options.get('context', 'tarball').strip()

        setup_tool = utils.getToolByName(self.context, 'portal_setup')
        if context_type == 'directory':
            profile_path = options.get('path', '')
            self.export_context = context.DirectoryExportContext(setup_tool, profile_path)
        elif context_type == 'tarball':
            self.export_context = context.TarballExportContext(setup_tool)
        elif context_type == 'snapshot':
            items = ('snapshot',) + time.gmtime()[:6]
            snapshot_id = '%s-%4d%02d%02d%02d%02d%02d' % items
            self.export_context = context.SnapshotExportContext(setup_tool, snapshot_id)
        else:
            self.export_context = context.TarballExportContext(setup_tool)

    def __iter__(self):
        for item in self.previous:
            item['_export_context'] = self.export_context

            pathkey = self.pathkey(*item.keys())[0]
            fileskey = self.fileskey(*item.keys())[0]

            if not (pathkey and fileskey): # path doesn't exist or no data to write
                yield item; continue

            path = item[pathkey]

            if path:
                item_path = '/'.join((self.prefix, path))
            else:
                item_path = self.prefix

            for k, v in item[fileskey].items():
                # contenttype is only used to determine whether to open the
                # output file in text or binary mode.
                contenttype = v.get('contenttype', None)
                if contenttype is None:
                    contenttype, encoding = mimetypes.guess_type(v['name'])
                if contenttype is None:
                    contenttype = 'application/octet-stream'
                if isinstance(v['data'], unicode):
                    data = v['data'].encode('utf-8')
                else:
                    data = v['data']
                self.export_context.writeDataFile(v['name'], data, contenttype, subdir=item_path)

            yield item
