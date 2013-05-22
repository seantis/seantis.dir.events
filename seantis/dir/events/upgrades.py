from Products.CMFCore.utils import getToolByName

from seantis.dir.events.interfaces import IEventsDirectory
from seantis.dir.base.interfaces import IDirectoryCatalog


def setup_indexing(context):
    setup = getToolByName(context, 'portal_setup')

    profile = 'profile-seantis.dir.events:default'
    setup.runImportStepFromProfile(profile, 'typeinfo')
    setup.runImportStepFromProfile(profile, 'catalog')

    # reindex everything
    catalog = getToolByName(context, 'portal_catalog')
    catalog.clearFindAndRebuild()

    # rebuild eventindexes
    directories = catalog(object_provides=IEventsDirectory.__identifier__)

    for directory in directories:

        directory_catalog = IDirectoryCatalog(directory.getObject())
        directory_catalog.reindex()
