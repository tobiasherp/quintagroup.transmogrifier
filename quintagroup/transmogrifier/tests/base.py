import tempfile
from os.path import join
import quintagroup
from Products.Five.testbrowser import Browser
from Products.PloneTestCase import ptc
from Products.CMFPlone.utils import versionTupleFromString, getToolByName

from quintagroup.transmogrifier import testing

ptc.setupPloneSite()


class TransmogrifierTestCase(ptc.PloneTestCase):
    """ base class for integration tests """

    layer = testing.transmogrifier
    tempfolder = tempfile.mkdtemp()
    data_path = join(quintagroup.transmogrifier.tests.__path__[0], "data")

    @property
    def target(self):
        """return the 2nd plone site, the target for our import tests."""
        return self.app.target

    def getPloneVersion(self):
        """Returns plone version tuple."""

        self.pm = getToolByName(self.portal, 'portal_migration')
        try:
            version = versionTupleFromString(self.pm.getSoftwareVersion())
        except AttributeError:
            version = versionTupleFromString(self.pm.getFileSystemVersion())

        return version


class TransmogrifierFunctionalTestCase(ptc.FunctionalTestCase):
    """ base class for functional tests """

    layer = testing.transmogrifier

    def getCredentials(self):
        return '%s:%s' % (ptc.default_user, ptc.default_password)

    def getBrowser(self, loggedIn=True):
        """ instantiate and return a testbrowser for convenience """
        browser = Browser()
        if loggedIn:
            auth = 'Basic %s' % self.getCredentials()
            browser.addHeader('Authorization', auth)
        return browser
