import logging
log = logging.getLogger('seantis.dir.events')

from five import grok

from datetime import date, timedelta
from dateutil.parser import parse

from zope.component import queryAdapter
from zope.component.hooks import getSite
from Products.CMFPlone.PloneBatch import Batch

from seantis.dir.base import directory
from seantis.dir.base import session
from seantis.dir.base.utils import cached_property

from seantis.dir.events.unrestricted import execute_under_special_role
from seantis.dir.events.interfaces import (
    IEventsDirectory, IActionGuard
)

from seantis.dir.events.recurrence import grouped_occurrences
from seantis.dir.events import dates
from seantis.dir.events import utils
from seantis.dir.events import maintenance
from seantis.dir.events import _

from AccessControl import getSecurityManager
from Products.CMFCore import permissions

from seantis.dir.events import pages


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

        There's no actual implementation of that in seantis.dir.events
        but client specific packages like izug.seantis.dir.events may
        use a custom adapter to implement such a thing.
        """
        guard = queryAdapter(self, IActionGuard)

        if guard:
            return guard.allow_action(action, item_brain)
        else:
            return True


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

    def get_last_custom_start_date(self):
        """ Returns the last selected custom start date. """
        default, unused = getattr(dates.DateRanges(), 'custom')
        return session.get_session(self.context,
                                   'custom_date_start') or default

    def get_last_custom_end_date(self):
        """ Returns the last selected custom end date. """
        unused, default = getattr(dates.DateRanges(), 'custom')
        return session.get_session(self.context,
                                   'custom_date_end') or default

    def set_last_custom_dates(self, start, end):
        """ Store the last selected custom dates on the session. """
        session.set_session(self.context, 'custom_date_start', start)
        session.set_session(self.context, 'custom_date_end', end)

    def get_last_state(self):
        """ Returns the last selected event state. """
        return session.get_session(self.context, 'state') or 'published'

    def set_last_state(self, method):
        """ Store the last selected event state on the session. """
        session.set_session(self.context, 'state', method)

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
    def custom_date_min(self):
        return date.today().strftime('%Y-%m-%d')

    @property
    def custom_date_max(self):
        mim_date, max_date = dates.eventrange()
        return max_date.strftime('%Y-%m-%d')

    @property
    def custom_date_from(self):
        return self.catalog.custom_start_date().strftime('%Y-%m-%d')

    @property
    def custom_date_to(self):
        return self.catalog.custom_end_date().strftime('%Y-%m-%d')

    @property
    def custom_date_url(self):
        url = self.daterange_url('custom')
        url += '&from=' + self.custom_date_from
        url += '&to=' + self.custom_date_to
        return url

    @cached_property
    def locale(self):
        # borrowed from widget collective.z3form.datetimewidget.DateWidget
        cal = self.request.locale.dates.calendars['gregorian']
        locale = {
            'lang': getattr(self.request, 'LANGUAGE', 'en'),
            'months': ','.join(cal.getMonthNames()),
            'shortmonths': ','.join(cal.getMonthAbbreviations()),
            'days': ','.join([cal.getDayNames()[6]] + cal.getDayNames()[:6]),
            'shortdays': ','.join(
                [cal.getDayAbbreviations()[6]] + cal.getDayAbbreviations()[:6]
            ),
            'format': 'dd.mm.yyyy'
        }
        return locale

    @property
    def has_results(self):
        return len(self.batch) > 0

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
        # Update date range
        daterange = self.request.get('range', self.get_last_daterange())
        if not dates.is_valid_daterange(daterange):
            daterange = 'this_month'
        else:
            self.set_last_daterange(daterange)

        # Update custom dates
        start = self.get_last_custom_start_date()
        end = self.get_last_custom_end_date()
        if daterange == 'custom':
            tz = start.tzinfo
            try:
                start = parse(self.request.get('from'), ignoretz=True)
                start = start.replace(tzinfo=tz)
                end = parse(self.request.get('to'), ignoretz=True)
                end = end.replace(tzinfo=tz)
                end = max(start, end)
                self.set_last_custom_dates(start, end)
            except:
                pass

        # Update state
        state = self.request.get('state', self.get_last_state())
        if not self.show_state_filters or state not in (
            'submitted', 'published', 'archived'
        ):
            state = 'published'
        else:
            self.set_last_state(state)

        # Set catalog
        self.catalog.state = state
        self.catalog.daterange = daterange
        self.catalog.set_custom_dates(start, end)

        if not self.is_ical_export and not self.is_json_export:
            super(EventsDirectoryView, self).update(**kwargs)

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
            ('published', _(u'Published'))
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


class CleanupView(grok.View):

    grok.name('cleanup')
    grok.context(IEventsDirectory)
    grok.require('zope2.View')

    def render(self):

        # dryrun must be disabled explicitly using &run=1
        dryrun = not self.request.get('run') == '1'

        # this maintenance feature may be run unrestricted as it does not
        # leak any information and it's behavior cannot be altered by the
        # user. This allows for easy use via cronjobs.
        execute_under_special_role(
            getSite(), 'Manager',
            maintenance.cleanup_directory, self.context, dryrun
        )

        return u''
