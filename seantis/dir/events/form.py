# -- coding: utf-8 --

from copy import copy
from five import grok
from collections import OrderedDict

from Acquisition import aq_inner, aq_base
from Acquisition.interfaces import IAcquirer

from plone.directives import form
from plone.z3cform.fieldsets import extensible
from plone.dexterity.utils import createContent, addContentToContainer
from plone.formwidget.recurrence.z3cform.widget import (
    RecurrenceWidget, ParameterizedWidgetFactory
)

from Products.statusmessages.interfaces import IStatusMessage

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import Choice, TextLine
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary
from zope.component.interfaces import ComponentLookupError

from z3c.form import field, group, button, widget
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget

from collective.z3cform.mapwidget.widget import MapFieldWidget
from collective.geo.contentlocations.interfaces import IGeoManager

from plone.app.event.base import default_timezone
from plone.app.event.dx.behaviors import (
    IEventBasic,
    IEventRecurrence
)

from seantis.dir.events.interfaces import (
    IEventsDirectory, 
    IEventsDirectoryItem,
)

from seantis.dir.events.token import (
    verify_token, apply_token, clear_token, append_token
)

from seantis.dir.events import utils
from seantis.dir.events import _

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
    
    dynamic_fields = ('wkt', )
    group_fields = OrderedDict() 
    group_fields[IEventsDirectoryItem] = (
        'locality', 'street', 'housenumber', 'zipcode', 'town'
    )
    group_fields[IGeoManager] = (
        'wkt',
    )

    def update_dynamic_fields(self):
        coordinates = self.fields['wkt']
        coordinates.widgetFactory = MapFieldWidget

class InformationGroup(EventBaseGroup):
    label = _(u'Information')
    fields = field.Fields(IEventsDirectoryItem).select(
        'organizer', 'contact_name', 'contact_email',
        'contact_phone', 'prices', 'event_url', 'registration',
        'image', 'attachment_1', 'attachment_2'
    )

class EventSubmissionForm(extensible.ExtensibleForm):
    
    grok.baseclass()
    grok.require('zope2.View')

    template = ViewPageTemplateFile('templates/form.pt')

    groups = (GeneralGroup, LocationGroup, InformationGroup)
    enable_form_tabbing = True

    label = _(u'Event Submission Form')
    description = _(
        u'Send us your events and we will publish them on this website'
    )

    coordinates = None

    @property
    def directory(self):
        raise NotImplementedError

    def prepare_coordinates(self, data):
        if data.get('wkt'):
            self.coordinates = utils.verify_wkt(data['wkt']).__geo_interface__
        else:
            self.coordinates = None

        del data['wkt']

    def apply_coordinates(self, content):
        c = self.coordinates
        if c:
            IGeoManager(content).setCoordinates(c['type'], c['coordinates'])
        else:
            IGeoManager(content).removeCoordinates()

    def handle_cancel(self):
        try:
            clear_token(self.context)
        except ComponentLookupError:
            pass
        IStatusMessage(self.request).add(_(u"Event submission cancelled"), "info")
        self.request.response.redirect(self.directory.absolute_url())

class EventSubmissionAddForm(EventSubmissionForm, form.AddForm):
    grok.context(IEventsDirectory)
    grok.name('submit-event')

    coordinates = None
    content = None

    @property
    def directory(self):
        return self.context

    def create(self, data):
        data['timezone'] = default_timezone()
        
        self.prepare_coordinates(data)

        content = createContent('seantis.dir.events.item', **data)

        if IAcquirer.providedBy(content):
            content = content.__of__(aq_inner(self.context))

        return aq_base(content)

    def add(self, obj):
        # not checking the contrains means two things
        # * impossible content types could theoretically added
        # * anonymous users can post events
        self.content = addContentToContainer(
            aq_inner(self.context), obj, checkConstraints=False
        )

        self.apply_coordinates(self.content)
        apply_token(self.content)

    @button.buttonAndHandler(_('Preview Event'), name='save')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        obj = self.createAndAdd(data)
        
        if obj is not None:
            self._finishedAdd = True
            IStatusMessage(self.request).addStatusMessage(
                _(u"Preview created"), "info"
            )

            preview_url = self.context.absolute_url() + '/' + obj.id
            preview_url += '/preview-event'
            preview_url = append_token(obj, preview_url)

            self.request.response.redirect(preview_url)

    @button.buttonAndHandler(_(u'Cancel Event Submission'), name='cancel')
    def handleCancel(self, action):
        self.handle_cancel()

class EventSubmissionEditForm(EventSubmissionForm, form.EditForm):
    grok.context(IEventsDirectoryItem)
    grok.name('edit-event')

    @property
    def directory(self):
        return self.context.directory

    def update(self, *args, **kwargs):
        verify_token(self.context, self.request)
        super(EventSubmissionEditForm, self).update(*args, **kwargs)

    def applyChanges(self, data):
        self.prepare_coordinates(data)
        self.apply_coordinates(self.getContent())

        return super(EventSubmissionEditForm, self).applyChanges(data)

    @button.buttonAndHandler(_('Update Event Preview'), name='save')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        
        changes = self.applyChanges(data)

        if changes:
            IStatusMessage(self.request).add(_(u"Preview updated"), "info")
        else:
            IStatusMessage(self.request).add(_(u"No changes made"), "info")

        preview_url = self.context.absolute_url() + '/preview-event'
        self.request.response.redirect(append_token(self.context, preview_url))

    @button.buttonAndHandler(_(u'Cancel Event Submission'), name='cancel')
    def handleCancel(self, action):
        self.handle_cancel()

class IPreview(form.Schema):
    title = TextLine(required=False)

class DetailPreviewWidget(widget.Widget):

    _template = ViewPageTemplateFile('templates/previewdetail.pt')

    def render(self):
        self.directory = self.context.parent()
        return self._template(self)

def DetailPreviewFieldWidget(field, request):
    """IFieldWidget factory for MapWidget."""
    return widget.FieldWidget(field, DetailPreviewWidget(request))

class PreviewGroup(EventBaseGroup):
    
    label = _(u'Detail Preview')

    dynamic_fields = ('title', )

    group_fields = OrderedDict()
    group_fields[IPreview] = ('title', )

    def update_dynamic_fields(self):
        self.fields['title'].widgetFactory = DetailPreviewFieldWidget

class PreviewForm(EventSubmissionForm, form.AddForm):
    grok.context(IEventsDirectoryItem)
    grok.name('preview-event')

    groups = (PreviewGroup, )
    template = ViewPageTemplateFile('templates/previewform.pt')

    label = _(u'Event Submission Preview')
    description = u''

    @property
    def directory(self):
        return self.context.aq_parent

    @property
    def edit_url(self):
        return append_token(self.context, self.context.absolute_url() + '/edit-event')

    def onclick_url(self, url):
        return "location.href='%s';" % url

    def update(self, *args, **kwargs):
        verify_token(self.context, self.request)
        super(PreviewForm, self).update(*args, **kwargs)

    @button.buttonAndHandler(_('Submit Event'), name='save')
    def handleSubmit(self, action):
        clear_token(self.context)
        self.context.submit()
        IStatusMessage(self.request).add(_(u"Event submitted"), "info")
        self.request.response.redirect(self.directory.absolute_url())

    @button.buttonAndHandler(_(u'Cancel Event Submission'), name='cancel')
    def handleCancel(self, action):
        self.handle_cancel()