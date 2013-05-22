from Products.CMFCore.utils import getToolByName

from seantis.dir.base.interfaces import IDirectoryCatalog
from seantis.dir.base.upgrades import (
    add_behavior_to_item,
    reset_images_and_attachments
)

from seantis.dir.events.interfaces import (
    IEventsDirectory,
    IEventsDirectoryItem
)


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


def upgrade_1000_to_1001(context):
    add_behavior_to_item(context, 'seantis.dir.events', IEventsDirectoryItem)
    reset_images_and_attachments(
        context,
        (IEventsDirectory, IEventsDirectoryItem),
        ['image', 'attachment_1', 'attachment_2']
    )
