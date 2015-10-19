import transaction

from datetime import date, datetime
from seantis.dir.events import dates
from seantis.dir.events.tests import IntegrationTestCase

from seantis.dir.events.catalog import (
    LazyList,
    EventOrderIndex,
    attach_reindex_to_transaction,
    ReindexDataManager,
)

from mock import Mock


class TestCatalog(IntegrationTestCase):

    def test_export_with_categories(self):

        self.login_testuser()

        events = [
            self.create_event(title='1', cat1=['a'], cat2=['1']),
            self.create_event(title='2', cat1=['a', 'b'], cat2=['2']),
            self.create_event(title='3', cat1=['b', 'c'], cat2=['2', '3']),
            self.create_event(title='4', cat1=['c'], cat2=['1', '3'])
        ]
        for event in events:
            event.submit()
            event.publish()
        transaction.commit()

        def _get(cat1=-1, cat2=-1):
            term = {}
            if cat1 != -1:
                term['cat1'] = cat1
            if cat2 != -1:
                term['cat2'] = cat2

            return sorted([s.title for s in self.catalog.export(term=term)])

        self.assertEquals(_get(cat1=None), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat1=[]), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat1=''), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat1='a'), ['1', '2'])

        self.assertEquals(_get(cat1=['a']), ['1', '2'])
        self.assertEquals(_get(cat1=['b']), ['2', '3'])
        self.assertEquals(_get(cat1=['c']), ['3', '4'])
        self.assertEquals(_get(cat1=['a', 'b']), ['1', '2', '3'])
        self.assertEquals(_get(cat1=['a', 'c']), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat1=['b', 'c']), ['2', '3', '4'])
        self.assertEquals(_get(cat1=['a', 'b', 'c']), ['1', '2', '3', '4'])

        self.assertEquals(_get(cat2=None), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat2=[]), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat2=''), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat2='1'), ['1', '4'])

        self.assertEquals(_get(cat2=['1']), ['1', '4'])
        self.assertEquals(_get(cat2=['2']), ['2', '3'])
        self.assertEquals(_get(cat2=['3']), ['3', '4'])
        self.assertEquals(_get(cat2=['1', '2']), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat2=['1', '3']), ['1', '3', '4'])
        self.assertEquals(_get(cat2=['2', '3']), ['2', '3', '4'])
        self.assertEquals(_get(cat2=['1', '2', '3']), ['1', '2', '3', '4'])

        self.assertEquals(_get(cat1=None, cat2=None), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat1=[], cat2=[]), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat1='', cat2=''), ['1', '2', '3', '4'])
        self.assertEquals(_get(cat1='a', cat2='1'), ['1'])

        self.assertEquals(_get(cat1=['a', 'c'], cat2=['1']), ['1', '4'])
        self.assertEquals(_get(cat1=['a'], cat2=['2', '3']), ['2'])
        self.assertEquals(_get(cat1=['b', 'c'], cat2=['3', '4']), ['3', '4'])

        self.directory.manage_delObjects(['1', '2', '3', '4'])
        self.portal.manage_delObjects([self.directory.id])
        transaction.commit()
