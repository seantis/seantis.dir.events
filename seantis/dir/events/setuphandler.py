from seantis.plonetools import setuphandlers

indexes = [
    ('source', 'FieldIndex'),
]


def import_indexes(context):
    setuphandlers.import_indexes('seantis.dir.events', indexes, context)
