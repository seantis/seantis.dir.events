import pytz
from datetime import datetime

from five import grok

from Products.CMFCore.utils import getToolByName

from plone.memoize import view
from plone.app.event.ical import construct_calendar
from plone.event.interfaces import IICalendarEventComponent
from plone.app.event.ical import ICalendarEventComponent

from seantis.dir.base import item
from seantis.dir.base import core
from seantis.dir.base.interfaces import IFieldMapExtender, IDirectoryItemBase

from seantis.dir.events import dates
from seantis.dir.events import recurrence
from seantis.dir.events import utils
from seantis.dir.events.token import verify_token
from seantis.dir.events.interfaces import (
    IActionGuard, IEventsDirectory, IEventsDirectoryItem
)

from AccessControl import getSecurityManager
from Products.CMFCore import permissions

class EventsDirectoryItem(item.DirectoryItem):
    
    actions_order = ['submit', 'publish', 'deny', 'archive']

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

    def list_actions(self):
        sortkey = lambda a: self.actions_order.index(a['id'])

        workflowTool = getToolByName(self, "portal_workflow")
        return sorted(workflowTool.listActions(object=self), key=sortkey)

    def allow_action(self, action):
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
        return IActionGuard(self).allow_action(action)

    def do_action(self, action):
        """ Execute the given action. """
        workflowTool = getToolByName(self, "portal_workflow")
        workflowTool.doActionFor(self, action)

    def submit(self):
        self.do_action("submit")

    def publish(self):
        self.do_action("publish")

    def archive(self):
        self.do_action("archive")

class DefaultActionGuard(grok.Adapter):

    grok.context(IDirectoryItemBase)
    grok.implements(IActionGuard)

    def allow_action(self, action):
        return True
        
class EventsDirectoryItemViewlet(grok.Viewlet):
    grok.context(IEventsDirectoryItem)
    grok.name('seantis.dir.events.item.detail')
    grok.require('zope2.View')
    grok.viewletmanager(item.DirectoryItemViewletManager)

    template = grok.PageTemplateFile('templates/listitem.pt')

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

    def render(self):
        if not self.is_ical_export:
            return self._template.render(self)
        else:
            calendar = construct_calendar(self.context.parent(), [self.context])

            if self.request.get('only_this') == 'true':
                for component in calendar.subcomponents:
                    if 'RRULE' in component:
                        del component['RRULE']

            utils.render_ical_response(self.request, self.context, calendar)

    def ical_url(self, only_this):
        url = self.context.absolute_url() + '?type=ical'
        if only_this:
            url += '&only_this=true'
        return url

    @property
    def is_recurring(self):
        return self.context.recurrence and True or False

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
        min_date, max_date = dates.event_range()
        
        return recurrence.occurrences(self.context, min_date, max_date)

    def attachment_filename(self, attachment):
        filename = getattr(self.context, attachment).filename
        if len(filename) > 100:
            return filename[:100] + '...'
        else:
            return filename

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

class ICalendarEventItemComponent(ICalendarEventComponent, grok.Adapter):
    """ Adds custom information to the default ical implementation. """
    
    grok.implements(IICalendarEventComponent)
    grok.context(IEventsDirectoryItem)

    def get_coordinates(self):

        if not self.context.has_mapdata:
            return None

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
            ical.add('geo', coordinates)

        # plone.app.event.ical does the following, but when I tried
        # to use their interfaces for contact and location I got really
        # weird problems that made me give up at some point out of fed-up-ness          
        e = self.context

        if e.locality:
            ical.add('location', e.locality)

        contact = [e.contact_name, e.contact_phone, e.contact_email, e.event_url]
        contact = filter(lambda c: c, contact)

        if contact:
            ical.add('contact', u', '.join(contact))
        
        return ical

class ExtendedDirectoryItemFieldMap(grok.Adapter):
    """Adapter extending the import/export fieldmap of seantis.dir.events.item."""
    grok.context(IEventsDirectory)
    grok.provides(IFieldMapExtender)

    def __init__(self, context):
        self.context = context

    def extend_import(self, itemmap):
        itemmap.typename = 'seantis.dir.events.item'
        itemmap.interface = IEventsDirectoryItem

        extended = [
            "start", "end", "timezone", "whole_day", "recurrence",
            "short_description", "long_description", "locality", "street",
            "housenumber", "zipcode", "town", "event_url", "organizer",
            "contact_name", "contact_email", "contact_phone", "prices",
            "registration", "submitter", "submitter_email"
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