# -- coding: utf-8 --

from copy import copy
from five import grok
from collections import OrderedDict

from plone.directives import form
from plone.z3cform.fieldsets import extensible
from plone.dexterity.utils import createContent, addContentToContainer
from plone.formwidget.recurrence.z3cform.widget import (
    RecurrenceWidget, ParameterizedWidgetFactory
)

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import Choice
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary

from z3c.form import field, group
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget

from collective.z3cform.mapwidget.widget import MapFieldWidget

from plone.app.event.base import default_timezone
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

class EventBaseGroup(group.Group):
    
    group_fields = {}
    dynamic_fields = []

    _cached_fields = []

    @property
    def fields(self):
        """ Returns the fields defined in group_fields, making sure that
        dynamic fields are shallow copied before they are touched. 
        
        Dynamic fields in this context are fields whose schame properties
        are changed on the fly and it is important that they are copied
        since these changes otherwise leak through to other forms. 

        """

        if self._cached_fields:
            return self._cached_fields

        result = None

        for interface, fields in self.group_fields.items():
            if result == None:
                result = field.Fields(interface).select(*fields)
            else:
                result += field.Fields(interface).select(*fields)

        for f in self.dynamic_fields:
            if f in result:
                result[f].field = copy(result[f].field)

        self._cached_fields = result
        return result

    def updateWidgets(self):
        self.update_dynamic_fields()
        super(EventBaseGroup, self).updateWidgets()
        self.update_widgets()

    def update_dynamic_fields(self):
        """ Called when it's time to update the dynamic fields. """

    def update_widgets(self):
        """ Called when it's time to make changes to the widgets. """

class GeneralGroup(EventBaseGroup):
    
    label = _(u'Event')
    
    dynamic_fields = ('recurrence', 'cat1', 'cat2')
    
    group_fields = OrderedDict()
    group_fields[IEventsDirectoryItem] = (
        'title', 'short_description', 'long_description', 'cat1', 'cat2'
    )
    group_fields[IEventBasic] = (
        'start', 'end', 'whole_day'
    )
    group_fields[IEventRecurrence] = (
        'recurrence',
    )

    def update_dynamic_fields(self):
        recurrence = self.fields['recurrence']
        recurrence.widgetFactory = ParameterizedWidgetFactory(
            RecurrenceWidget, start_field='start'
        )

        categories = (self.fields['cat1'], self.fields['cat2'])

        for category in categories:
            category.field.description = u''
            category.field.value_type = Choice(
                source=self.available_categories(self.context, category.__name__)
            )
        
        categories[0].widgetFactory = CheckBoxFieldWidget
        categories[1].widgetFactory = RadioFieldWidget

    def update_widgets(self):
        # update labels of categories
        labels = self.context.labels()
        widgets = [w for w in self.widgets if w in labels]
        
        for widget in widgets:
            self.widgets[widget].label = labels[widget]

    def available_categories(self, context, category):

        @grok.provider(IContextSourceBinder)
        def get_categories(ctx):
            terms = []

            encode = lambda s: s.encode('utf-8')

            for value in context.suggested_values(category):
                terms.append(SimpleVocabulary.createTerm(encode(value), hash(value), value))

            return SimpleVocabulary(terms)

        return get_categories

class LocationGroup(EventBaseGroup):
    
    label = _(u'Location')
    
    dynamic_fields = ('coordinates', )
    group_fields = OrderedDict() 
    group_fields[IEventsDirectoryItem] = (
        'locality', 'street', 'housenumber', 'zipcode', 'town'
    )
    group_fields[ICoordinates] = (
        'coordinates',
    )

    def update_dynamic_fields(self):
        coordinates = self.fields['coordinates']
        coordinates.widgetFactory = MapFieldWidget

class InformationGroup(EventBaseGroup):
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

    def create(self, data):
        data['timezone'] = default_timezone()
        return createContent('seantis.dir.events.item', **data)

    def add(self, obj):
        addContentToContainer(self.context, obj)

