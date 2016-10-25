import pytz
import urllib

from datetime import datetime

from five import grok

from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from plone.memoize import view
from plone.app.event.ical.exporter import construct_icalendar
from plone.event.interfaces import IICalendarEventComponent
from plone.app.event.ical import ICalendarEventComponent
from OFS.interfaces import IObjectClonedEvent
from zExceptions import NotFound

from seantis.dir.base import item
from seantis.dir.base import core
from seantis.dir.base.interfaces import (
    IFieldMapExtender,
    IDirectoryCategorized
)

from seantis.dir.events import _
from seantis.dir.events import dates
from seantis.dir.events import recurrence
from seantis.dir.events import utils
from seantis.dir.events.token import verify_token
from seantis.dir.events.interfaces import (
    IEventsDirectory, IEventsDirectoryItem, IExternalEvent
)

from AccessControl import getSecurityManager
from Products.CMFCore import permissions


# when an event is cloned put it in the submitted state
@grok.subscribe(IEventsDirectoryItem, IObjectClonedEvent)
def onClonedEvent(item, event):
    item.submit()


class EventsDirectoryItem(item.DirectoryItem):

    actions_order = (
        'submit', 'publish', 'deny', 'archive', 'hide',
        'archive_permanently'
    )

    # there's currently an issue with seantis.dir.events, plone.app.event and
    # plone.app.imaging. this mock function servers as a work-around.
    # see https://github.com/plone/plone.app.event/issues/78
    def Schema(self):

        class MockSchema(object):
            def get(self, field):
                return None

        return MockSchema()

    def get_parent(self):
        return self.aq_inner.aq_parent

    @property
    def tz(self):
        return pytz.timezone(self.timezone)

    @property
    def local_start(self):
        return self.tz.normalize(self.start)

    @property
    def local_end(self):
        return self.tz.normalize(self.end)

    def as_occurrence(self):
        return recurrence.Occurrence(self, self.start, self.end)

    @property
    def state(self):
        """ Return the workflow state. """
        return utils.workflow_tool().getInfoFor(self, 'review_state')

    @property
    def review_state(self):
        return self.state

    def action_url(self, action):
        baseurl = self.absolute_url() + '/do-action?action=%s'
        return baseurl % action['id']

    def list_actions(self):
        sortkey = lambda a: self.actions_order.index(a['id'])

        workflowTool = getToolByName(self, "portal_workflow")
        return sorted(workflowTool.listActions(object=self), key=sortkey)

    def do_action(self, action):
        """ Execute the given action. """
        workflowTool = getToolByName(self, "portal_workflow")
        workflowTool.doActionFor(self, action)

    def allow_action(self, action):
        return self.get_parent().allow_action(action, self)

    def submit(self):
        self.do_action("submit")

    def deny(self):
        self.do_action("deny")

    def publish(self):
        self.do_action("publish")

    def archive(self):
        self.do_action("archive")

    def archive_permanently(self):
        self.do_action("archive_permanently")

    def hide(self):
        self.do_action("hide")

    def reindex(self):
        utils.get_catalog(self.get_parent()).reindex()

    def attachment_filename(self, attachment):
        filename = getattr(self, attachment).filename

        if not filename:
            number = attachment[-1]
            return _(u'Attachment ${number}', mapping=dict(number=number))

        if len(filename) > 100:
            return filename[:100] + '...'
        else:
            return filename

    def eventtags(self):
        """ Return a list of tuples containing the event tag value
        (category value) in position 0 and the link to the related
        filter in position 1.

        The results are sorted by value (position 0).
        """

        categorized = IDirectoryCategorized(self)

        categories = dict()
        categories['cat1'] = categorized.keywords(categories=('cat1', ))
        categories['cat2'] = categorized.keywords(categories=('cat2', ))

        baseurl = self.get_parent().absolute_url() + '?filter=true&%s=%s'

        tags = list()

        for key in sorted(categories):
            for tag in sorted(categories[key]):
                if not tag:
                    continue

                tags.append((
                    tag.strip().replace(' ', '&nbsp;'),
                    baseurl % (key, urllib.quote(tag.encode('utf-8')))
                ))

        return tags

    @property
    def allow_edit(self):
        return not IExternalEvent.providedBy(self)


class DoActionView(grok.View):
    """ Pretty much like modify_content_status, but with
    better messages and redirection to the directory. """

    grok.name('do-action')
    grok.context(IEventsDirectoryItem)
    grok.require('cmf.ReviewPortalContent')

    messages = {
        'publish': _(u'Event was published'),
        'archive': _(u'Event was archived'),
        'deny': _(u'Publication of event was denied'),
        'hide': _(u'Event was hidden'),
        'archive_permanently': _(u'Event was archived permanently')
    }

    def render(self):

        action = self.request.get('action')
        assert action in self.messages

        IStatusMessage(self.request).add(self.messages[action], "info")
        self.context.do_action(action)
        self.request.response.redirect(
            self.context.get_parent().absolute_url()
        )

        return ""


class View(core.View):
    """Default view of a seantis.dir.events item."""
    grok.context(IEventsDirectoryItem)
    grok.require('zope2.View')

    # don't show the search viewlet the item's view
    hide_search_viewlet = True

    template = None
    _template = grok.PageTemplateFile('templates/item.pt')

    def update(self):
        verify_token(self.context, self.request)

        super(View, self).update()

    @property
    def is_ical_export(self):
        return self.request.get('type') == 'ical'

    @property
    def is_valid_date(self):
        return self.occurrence is not None

    def render(self):
        if not self.is_valid_date:
            raise NotFound()

        if not self.is_ical_export:
            return self._template.render(self)
        else:
            if self.date:
                calendar = construct_icalendar(
                    self.context, [self.occurrence]
                )
                for component in calendar.subcomponents:
                    if 'RRULE' in component:
                        del component['RRULE']
            else:
                calendar = construct_icalendar(
                    self.context, [self.context]
                )

            return utils.render_ical_response(self.request, self.context,
                                              calendar)

    @utils.webcal
    def ical_url(self, only_this):
        url = self.context.absolute_url() + '?type=ical'
        if only_this and self.request.get('date'):
            url += '&date=' + self.request.get('date')
        return url

    @property
    def is_recurring(self):
        return self.context.recurrence and True or False

    def recurrence_url(self, event):
        return utils.recurrence_url(self.context.get_parent(), event)

    @property
    def date(self):
        date = self.request.get('date')
        if not date:
            return None

        try:
            return datetime.strptime(date, '%Y-%m-%d')
        except:
            return None

    @property
    def human_date(self):
        return self.occurrence.human_date(self.request)

    @property
    def human_daterange(self):
        return self.occurrence.human_daterange(self.request)

    @property
    @view.memoize
    def occurrence(self):
        date = self.date
        if date and self.is_recurring:
            return recurrence.pick_occurrence(self.context, self.date)
        else:
            return self.context.as_occurrence()

    @property
    @view.memoize
    def occurrences(self):
        min_date, max_date = dates.eventrange()

        return recurrence.occurrences(self.context, min_date, max_date)

    @property
    def show_submitter(self):
        # if the information not present, do not show
        if not all((self.context.submitter, self.context.submitter_email)):
            return False

        # someone who may open the edit view can see the submitter there,
        # so we can display it on the detail view in this case
        return getSecurityManager().checkPermission(
            permissions.ModifyPortalContent, self.context
        )

    @property
    def show_source(self):
        if not IExternalEvent.providedBy(self.context):
            return False

        return getSecurityManager().checkPermission(
            permissions.ReviewPortalContent, self.context
        )

    @property
    def import_source(self):
        try:
            result = IExternalEvent(self.context).source
        except:
            result = ""
        return result


class ICalendarEventItemComponent(ICalendarEventComponent, grok.Adapter):
    """ Adds custom information to the default ical implementation. """

    grok.implements(IICalendarEventComponent)
    grok.context(IEventsDirectoryItem)

    def get_coordinates(self):

        coordinates = self.context.get_coordinates()

        if not len(coordinates) == 2:
            return None

        if not (coordinates[0] or '').upper() == 'POINT':
            return None

        return coordinates[1]

    def to_ical(self):
        ical = ICalendarEventComponent.to_ical(self)

        coordinates = self.get_coordinates()
        if coordinates:
            # ical actually needs a tuple here, not a list which I argue is
            # a bug: https://github.com/collective/icalendar/issues/83
            ical.add('geo', tuple(coordinates))

        # plone.app.event.ical does the following, but when I tried
        # to use their interfaces for contact and location I got really
        # weird problems that made me give up at some point out of fed-up-ness
        e = self.context

        if e.locality:
            ical.add('location', e.locality)

        contact = [
            e.contact_name, e.contact_phone, e.contact_email, e.event_url
        ]
        contact = filter(lambda c: c, contact)

        if contact:
            ical.add('contact', u', '.join(contact))

        return ical


class ExtendedDirectoryItemFieldMap(grok.Adapter):
    """Adapter extending the import/export fieldmap of
    seantis.dir.events.item.

    """
    grok.context(IEventsDirectory)
    grok.provides(IFieldMapExtender)

    def __init__(self, context):
        self.context = context

    def extend_import(self, itemmap):
        itemmap.typename = 'seantis.dir.events.item'
        itemmap.interface = IEventsDirectoryItem

        extended = [
            'start', 'end', 'timezone', 'whole_day', 'recurrence',
            'short_description', 'long_description', 'locality', 'street',
            'housenumber', 'zipcode', 'town', 'location_url', 'event_url',
            'organizer', 'contact_name', 'contact_email', 'contact_phone',
            'prices', 'registration', 'submitter', 'submitter_email'
        ]

        boolwrap = lambda v: v and '1' or ''
        boolunwrap = lambda v: v == '1'

        itemmap.bind_wrapper("whole_day", boolwrap)
        itemmap.bind_unwrapper("whole_day", boolunwrap)

        datewrap = lambda v: v.strftime('%Y.%m.%d %H-%M')
        dateunwrap = lambda v: datetime.strptime(v, '%Y.%m.%d %H-%M')

        itemmap.bind_wrapper("start", datewrap)
        itemmap.bind_unwrapper("start", dateunwrap)

        itemmap.bind_wrapper("end", datewrap)
        itemmap.bind_unwrapper("end", dateunwrap)

        itemmap.add_fields(extended, len(itemmap))
