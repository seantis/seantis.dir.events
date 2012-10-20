from five import grok

from plone.directives import form
from plone.z3cform.fieldsets import extensible

from z3c.form import field, group

from plone.app.event.dx.behaviors import (
    IEventBasic,
    IEventRecurrence
)

from seantis.dir.events.interfaces import (
    IEventsDirectory, 
    IEventsDirectoryItem
)

from seantis.dir.events import _

# I don't even..
class EventBaseForm(extensible.ExtensibleForm, form.AddForm, group.GroupForm):
    grok.baseclass()

class GeneralGroup(group.Group):
    label = _(u'General')
    fields = field.Fields(IEventsDirectoryItem).select(
        'title', 'short_description', 'long_description'
    )
    fields += field.Fields(IEventBasic).select('start', 'end', 'whole_day')
    fields += field.Fields(IEventRecurrence).select('recurrence')

class LocationGroup(group.Group):
    label = _(u'Location')
    fields = field.Fields(IEventsDirectoryItem).select(
        'locality', 'street', 'housenumber', 'zipcode', 'town'
    )

class InformationGroup(group.Group):
    label = _(u'Information')
    fields = field.Fields(IEventsDirectoryItem).select(
        'organizer', 'contact_name', 'contact_email',
        'contact_phone', 'prices', 'event_url', 'registration',
        'image', 'attachment_1', 'attachment_2'
    )

class EventSubmissionForm(EventBaseForm):
    grok.name('submit-event')
    grok.require('seantis.dir.events.SubmitEvents')
    grok.context(IEventsDirectory)

    groups = (GeneralGroup, LocationGroup, InformationGroup)
    enable_form_tabbing = True

    label = _(u'Event Submission Form')
    description = _(
        u'Send us your events and we will publish them on this website'
    )