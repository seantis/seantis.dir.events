from five import grok

from plone.directives import form
from plone.z3cform.fieldsets import extensible

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form import field, group
from plone.formwidget.recurrence.z3cform.widget import RecurrenceWidget, ParameterizedWidgetFactory
from collective.z3cform.mapwidget.widget import MapFieldWidget

from plone.app.event.dx.behaviors import (
    IEventBasic,
    IEventRecurrence
)

from seantis.dir.events.interfaces import (
    ICoordinates,
    IEventsDirectory, 
    IEventsDirectoryItem
)

from seantis.dir.events import _

# I don't even..
class EventBaseForm(extensible.ExtensibleForm, form.AddForm):
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
    fields = field.Fields(ICoordinates).select('coordinates')
    fields += field.Fields(IEventsDirectoryItem).select(
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

    template = ViewPageTemplateFile('templates/form.pt')

    groups = (GeneralGroup, LocationGroup, InformationGroup)
    enable_form_tabbing = True

    label = _(u'Event Submission Form')
    description = _(
        u'Send us your events and we will publish them on this website'
    )

    def updateFields(self):
        super(EventSubmissionForm, self).updateFields()

        # apply the recurrence widget
        recurrence = self.groups[0].fields['recurrence']
        recurrence.widgetFactory = ParameterizedWidgetFactory(
            RecurrenceWidget, start_field='start'
        )
        
        coordinates = self.groups[1].fields['coordinates']
        coordinates.widgetFactory = MapFieldWidget