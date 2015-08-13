from zope.interface import classProvides, implements
from zope.component import queryMultiAdapter

from collective.transmogrifier.interfaces import ISection, ISectionBlueprint
from collective.transmogrifier.utils import defaultMatcher

from quintagroup.transmogrifier.interfaces import IExportDataCorrector
from quintagroup.transmogrifier.interfaces import IImportDataCorrector


class DataCorrectorSection(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.previous = previous
        self.transmogrifier = transmogrifier
        self.context = transmogrifier.context
        self.count = transmogrifier.create_itemcounter(name)

        self.pathkey = defaultMatcher(options, 'path-key', name, 'path')
        self.fileskey = defaultMatcher(options, 'files-key', name, 'files')

        # 'type' options specifies adapter interface
        self.type_ = options.get('type', 'export')
        if self.type_ == 'export':
            self.interface = IExportDataCorrector
        elif self.type_ == 'import':
            self.interface = IImportDataCorrector
        else:
            self.interface = None

        # 'sources' specifies names of adapters
        self.sources = options.get('sources', '')
        self.sources = filter(None, [i.strip() for i in self.sources.splitlines()])

    def __iter__(self):
        count = self.count
        for item in self.previous:
            count('got')
            pathkey = self.pathkey(*item.keys())[0]
            fileskey = self.fileskey(*item.keys())[0]

            if not (pathkey and fileskey and self.sources):
                count('forwarded')
                yield item
                continue

            path = item[pathkey]
            obj = self.context.unrestrictedTraverse(path, None)
            if obj is None:         # path doesn't exist
                count('forwarded')
                continue

            file_store = item[fileskey]
            if not file_store:
                count('forwarded')
                yield item
                continue

            changed = False
            for name in self.sources:
                if not name in file_store:
                    continue
                adapter = queryMultiAdapter((obj, self.transmogrifier),
                                            self.interface, name)
                if adapter:
                    file_store[name] = adapter(file_store[name])
                    count('changes')
                    changed = True

            if changed:
                count('changed')

            count('forwarded')
            yield item
