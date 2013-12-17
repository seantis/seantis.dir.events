import logging
log = logging.getLogger('seantis.dir.events')

from five import grok

from zope.component import queryAdapter
from zope.interface import implements
from zope.event import notify
from Products.CMFPlone.PloneBatch import Batch

from seantis.dir.base import directory
from seantis.dir.base import session
from seantis.dir.base.utils import cached_property

from seantis.dir.events.interfaces import (
    IEventsDirectory, IActionGuard, IResourceViewedEvent, IExternalEvent
)

from seantis.dir.events.recurrence import grouped_occurrences
from seantis.dir.events import dates
from seantis.dir.events import utils
from seantis.dir.events import _

from AccessControl import getSecurityManager
from Products.CMFCore import permissions

from seantis.dir.events import pages


class ResourceViewedEvent(object):
    implements(IResourceViewedEvent)

    def __init__(self, context):
        self.context = context


class EventsDirectory(directory.Directory, pages.CustomPageHook):

    def labels(self):
        return dict(cat1=_(u'What'), cat2=_(u'Where'))

    def used_categories(self):
        return ('cat1', 'cat2')

    def unused_categories(self):
        return ('cat3', 'cat4')

    def allow_action(self, action, item_brain):
        """ Return true if the given action is allowed. This is not a
        wrapper for the transition guards of the event workflow. Instead
        it is called *by* the transition guards.

        This allows a number of people to work together on an event website
        with every person having its own group of events which he or she is
        responsible for.

        Per default, only external events may be hidden and only internal
        events archived. 

        A client specific packages like izug.seantis.dir.events may
        use a custom adapter to override the default behaviour.
        """
        result = True

        try:
            IExternalEvent(item_brain)
            external_event = True
        except:
            external_event = False

        if ((action == 'archive' and external_event) or
                (action == 'hide' and not external_event)):
            result = False

        guard = queryAdapter(self, IActionGuard)
        if guard:
            result = guard.allow_action(action, item_brain)
        return result


class ExtendedDirectoryViewlet(grok.Viewlet, pages.CustomDirectory):
    grok.context(IEventsDirectory)
    grok.name('seantis.dir.events.directory.detail')
    grok.require('zope2.View')
    grok.viewletmanager(directory.DirectoryViewletManager)

    template = grok.PageTemplateFile('templates/directorydetail.pt')

    def __init__(self, *args, **kwargs):
        super(ExtendedDirectoryViewlet, self).__init__(*args, **kwargs)
        self.context = self.custom_directory


class EventsDirectoryIndexView(grok.View, directory.DirectoryCatalogMixin):

    grok.name('eventindex')
    grok.context(IEventsDirectory)
    grok.require('cmf.ManagePortal')

    template = None

    def render(self):

        self.request.response.setHeader("Content-type", "text/plain")

        if 'rebuild' in self.request:
            log.info('rebuilding ZCatalog')
            self.catalog.catalog.clearFindAndRebuild()

        if 'reindex' in self.request:
            log.info('reindexing event indices')
            self.catalog.reindex()

        result = []
        for name, index in self.catalog.indices.items():

            result.append(name)
            result.append('-' * len(name))
            result.append('')

            for ix, identity in enumerate(index.index):
                result.append('%i -> %s' % (ix, identity))

            result.append('')

            dateindex = index.get_metadata('dateindex')

            if dateindex:
                result.append('-> dateindex')

                for date in sorted(dateindex):
                    result.append('%s -> %s' % (
                        date.strftime('%y.%m.%d'), dateindex[date])
                    )

        return '\n'.join(result)


class EventsDirectoryView(directory.View, pages.CustomDirectory):

    grok.name('view')
    grok.context(IEventsDirectory)
    grok.require('zope2.View')

    template = None
    _template = grok.PageTemplateFile('templates/directory.pt')

    fired_event = False

    @property
    def title(self):
        return self.custom_directory.title

    @property
    def is_ical_export(self):
        """ Returns true if the current request is an ical request. """
        return self.request.get('type') == 'ical'

    @property
    def is_json_export(self):
        """ Returns true if the current request is an json request. """
        return self.request.get('type') == 'json'

    def get_last_daterange(self):
        """ Returns the last selected daterange. """
        return session.get_session(self.context, 'daterange') \
            or dates.default_daterange

    def set_last_daterange(self, method):
        """ Store the last selected daterange on the session. """
        session.set_session(self.context, 'daterange', method)

    def get_last_state(self):
        """ Returns the last selected event state. """
        return session.get_session(self.context, 'state') or 'published'

    def set_last_state(self, method):
        """ Store the last selected event state on the session. """
        session.set_session(self.context, 'state', method)

    def get_last_import_source(self):
        """ Returns the last selected import source. """
        return session.get_session(self.context, 'source') \
            or ''

    def set_last_import_source(self, source):
        """ Store the last selected import source on the session. """
        session.set_session(self.context, 'source', source)

    @property
    def no_events_helptext(self):
        if 'published' == self.catalog.state:
            return _(u'No events for the current daterange')
        else:
            return _(u'No events for the current state')

    @property
    def selected_daterange(self):
        return self.catalog.daterange

    @property
    def dateranges(self):
        return dates.methods

    def daterange_url(self, method):
        return self.directory.absolute_url() + '?range=' + method

    @property
    def has_results(self):
        return len(self.batch) > 0

    @property
    def show_import_sources(self):
        return getSecurityManager().checkPermission(
            permissions.ReviewPortalContent, self.context
        )

    @property
    def import_sources(self):
        sources = [(source.Title, source.id) for
                   source in self.catalog.import_sources()]
        sources.insert(0, (u'-', ''))
        return sources

    def import_source_url(self, source):
        return self.directory.absolute_url() + '?source=' + source

    @property
    def selected_import_source(self):
        return self.catalog.import_source

    @property
    def import_sources_config(self):
        return [(source.Title, source.getURL() + '/edit')
                for source in self.catalog.import_sources()]

    def render(self):
        """ Renders the ical/json if asked, or the usual template. """
        search = 'search' in self.request.keys() \
            and self.request.get('searchtext') or None
        filter = 'filter' in self.request.keys() \
            and self.get_filter_terms() or None
        max = 'max' in self.request.keys() \
            and self.request.get('max') or None
        try:
            max = int(max)
        except:
            max = None

        if self.is_ical_export:
            calendar = self.catalog.calendar(search=search, filter=filter)
            return utils.render_ical_response(self.request, self.context,
                                              calendar)

        elif self.is_json_export:
            export = self.catalog.export(search=search, filter=filter, max=max)
            return utils.render_json_response(self.request, export)

        else:
            return self._template.render(self)

    def update(self, **kwargs):
        daterange = self.request.get('range', self.get_last_daterange())

        # do not trust the user's input blindly
        if not dates.is_valid_daterange(daterange):
            daterange = 'this_month'
        else:
            self.set_last_daterange(daterange)

        state = self.request.get('state', self.get_last_state())
        if not self.show_state_filters or state not in (
            'submitted', 'published', 'archived', 'hidden'
        ):
            state = 'published'
        else:
            self.set_last_state(state)

        source = self.request.get('source', self.get_last_import_source())
        if not self.show_import_sources:
            source = ''
        else:
            self.set_last_import_source(source)

        self.catalog.daterange = daterange
        self.catalog.state = state
        self.catalog.import_source = source

        if not self.is_ical_export and not self.is_json_export:
            super(EventsDirectoryView, self).update(**kwargs)

        if not self.fired_event:
            notify(ResourceViewedEvent(self.context))
            self.fired_event = True

    def groups(self, items):
        """ Returns the given occurrences grouped by human_date. """
        groups = grouped_occurrences(items, self.request)

        for key, items in groups.items():
            for ix, item in enumerate(items):
                items[ix] = item.get_object()

        return groups

    def translate(self, text, domain="seantis.dir.events"):
        return utils.translate(self.request, text, domain)

    @property
    def show_state_filters(self):
        return getSecurityManager().checkPermission(
            permissions.ReviewPortalContent, self.context
        )

    @cached_property
    def batch(self):
        # use a custom batch whose items are lazy evaluated on __getitem__
        start = int(self.request.get('b_start') or 0)
        lazy_list = self.catalog.lazy_list

        # seantis.dir.events lazy list implementation currently cannot
        # deal with orphans.
        return Batch(lazy_list, directory.ITEMSPERPAGE, start, orphan=0)

    @property
    def selected_state(self):
        return self.catalog.state

    def state_filter_list(self):

        submitted = utils.translate(self.request, _(u'Submitted'))
        submitted += u' (%i)' % self.catalog.submitted_count

        return [
            ('submitted', submitted),
            ('published', _(u'Published')),
            ('hidden', _(u'Hidden'))
        ]

    def state_url(self, method):
        return self.directory.absolute_url() + '?state=' + method

    @utils.webcal
    def ical_url(self, for_all):
        """ Returns the ical url of the current view. """
        url = self.daterange_url('this_year') + '&type=ical'

        if for_all:
            return url

        action, param = self.primary_action()

        if action not in (self.search, self.filter):
            return ''

        if action == self.search:
            if param:
                return url + '&search=true&searchtext=%s' % param
            else:
                return ''

        if action == self.filter:
            terms = dict([(k, v) for k, v in param.items() if v != '!empty'])

            if not terms:
                return ''

            url += '&filter=true'

            for item in terms.items():
                url += '&%s=%s' % item

            return url


class TermsView(grok.View):

    grok.name('terms')
    grok.context(IEventsDirectory)
    grok.require('zope2.View')

    label = _(u'Terms and Conditions')
    template = grok.PageTemplateFile('templates/terms.pt')
