from Products.CMFCore.utils import getToolByName
from seantis.plonetools import setuphandlers

indexes = [
    ('source', 'FieldIndex'),
]


def import_indexes(context):
    setuphandlers.import_indexes('seantis.dir.events', indexes, context)


def enable_jquerytools_dateinput_js(context):
    # Ensure that jquerytools.dateinput.js is enabled, it might be disabled
    # with plone.app.jquerytools >= 1.7

    try:
        jstool = getToolByName(context, 'portal_javascripts')
    except AttributeError:
        return

    resource_id = '++resource++plone.app.jquerytools.dateinput.js'
    resource = jstool.getResource(resource_id)
    if resource:
        resource.setEnabled(True)

    jstool.cookResources()
