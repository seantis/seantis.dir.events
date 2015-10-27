# -- coding: utf-8 --

from copy import copy
from five import grok
from collections import OrderedDict
from datetime import date

from Acquisition import aq_inner, aq_base
from Acquisition.interfaces import IAcquirer

from plone.directives import form
from plone.z3cform.fieldsets import extensible
from plone.dexterity.utils import createContent, addContentToContainer
from plone.formwidget.recurrence.z3cform.widget import RecurrenceWidget

from Products.statusmessages.interfaces import IStatusMessage

import zope.event
import zope.lifecycleevent

from zope.interface import implements
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.schema import Choice, TextLine
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary
from zope.component.interfaces import ComponentLookupError

from z3c.form import field, group, button, widget
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget

from collective.z3cform.mapwidget.widget import MapFieldWidget
from collective.geo.contentlocations.interfaces import IGeoManager
from collective.geo.geographer.interfaces import IGeoreferenced

from plone.formwidget.datetime.z3cform.widget import DateWidget
from plone.app.event.base import default_timezone
from plone.app.event.dx.behaviors import first_weekday_sun0

from seantis.dir.base import utils as base_utils
from seantis.dir.base.interfaces import IDirectoryPage, IDirectoryCategorized

from seantis.dir.events.interfaces import (
    IEventsDirectory,
    IEventsDirectoryItem,
    ITerms,
    IEventSubmissionData,
    IExternalEvent
)

from seantis.dir.events.token import (
    verify_token,
    apply_token,
    clear_token,
    append_token,
    event_by_token,
    current_token
)

from seantis.dir.events import utils, dates
from seantis.dir.events.submission import validate_event_submission
from seantis.dir.events.recurrence import occurrences, grouped_occurrences
from seantis.dir.events import _


# plone.formwidget.recurrence got rid of the parameterized widget
# in favor ofusing plone.autoform. unfortunately, plone.autoform seems
# incapable of dealing with groups instead forms.
#
# I hate form libs.
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget


class ParameterizedFieldWidget(object):
    implements(IFieldWidget)

    def __new__(cls, field, request):
        widget = FieldWidget(field, cls.widget(request))
        for k, v in cls.kw.items():
            setattr(widget, k, v)
        return widget


def ParameterizedWidgetFactory(widget, **kw):
    return type('%sFactory' % widget.__name__,
                (ParameterizedFieldWidget,),
                {'widget': widget, 'kw': kw})


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
            if result is None:
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


class NavigationStep(object):
    def __init__(self, id=None, text=None, url=None):
        self.id, self.text, self.url = id, text, url


class NavigationMixin(object):

    _steps = None

    @property
    def show_navigation(self):
        return self.__name__ in ('submit', 'preview', 'finish')

    @property
    def steps(self):

        if self._steps:
            return self._steps

        steps = [
            NavigationStep('submit', _(u'Enter'), None),
            NavigationStep('preview', _(u'Verify'), None),
            NavigationStep('finish', _(u'Finish'), None)
        ]

        if self.__name__ == 'submit':
            steps[0].url = self.context.absolute_url() + '/@@submit'
            steps[1].url = None
            steps[2].url = None
        elif self.__name__ == 'preview':
            steps[0].url = self.directory.absolute_url() + '/@@submit'
            steps[1].url = self.context.absolute_url() + '/@@preview'
            steps[2].url = None
        elif self.__name__ == 'finish':
            steps[0].url = self.directory.absolute_url() + '/@@submit'
            steps[1].url = self.context.absolute_url() + '/@@preview'
            steps[2].url = self.context.absolute_url() + '/@@finish'

        for i in range(0, len(steps)):
            if steps[i].url:
                steps[i].url = append_token(self.context, steps[i].url)

        self._steps = steps
        return self._steps

    @property
    def current_step(self):
        for step in self.steps:
            if self.__name__ == step.id:
                return step

    def step_classes(self, step):

        classes = ["formTab"]

        if step.id == self.steps[0].id:
            classes.append("firstFormTab")

        if step.id == self.steps[-1].id:
            classes.append("lastFormTab")

        if step.id == self.current_step.id:
            classes.append("selected")

        if self.steps.index(step) < self.steps.index(self.current_step):
            classes.append("visited")

        return ' '.join(classes)


class GeneralGroup(EventBaseGroup):

    label = _(u'Event')

    dynamic_fields = ('cat1', 'cat2')

    group_fields = OrderedDict()
    group_fields[IEventsDirectoryItem] = (
        'title', 'short_description', 'long_description'
    )
    group_fields[IDirectoryCategorized] = (
        'cat1', 'cat2'
    )

    def update_dynamic_fields(self):
        categories = (self.fields['cat1'], self.fields['cat2'])

        for category in categories:
            category.field.description = u''
            category.field.value_type = Choice(
                source=self.available_categories(
                    self.context, category.__name__
                )
            )

        categories[0].widgetFactory = CheckBoxFieldWidget
        categories[0].field.required = True
        categories[1].widgetFactory = RadioFieldWidget
        categories[1].field.required = True

    def update_widgets(self):
        # update labels of categories
        labels = self.context.labels()
        widgets = [w for w in self.widgets if w in labels]

        for widget in widgets:
            self.widgets[widget].label = labels[widget]

        self.widgets['title'].label = _(u'Title of event')

    def available_categories(self, context, category):

        @grok.provider(IContextSourceBinder)
        def get_categories(ctx):
            terms = []

            for value in context.suggested_values(category):
                terms.append(
                    SimpleVocabulary.createTerm(value, hash(value), value)
                )

            return SimpleVocabulary(terms)

        return get_categories


class DateGroup(EventBaseGroup):

    label = _(u'Event date')

    dynamic_fields = (
        'submission_date',
        'submission_range_start_date',
        'submission_range_end_date',
        'submission_date_type',
        'submission_recurrence',
        'submission_days'
    )

    group_fields = OrderedDict()

    group_fields[IEventSubmissionData] = (
        'submission_date_type',
        'submission_date',
        'submission_start_time',
        'submission_end_time',
        'submission_range_start_date',
        'submission_range_end_date',
        'submission_range_start_time',
        'submission_range_end_time',
        'submission_whole_day',
        'submission_recurrence',
        'submission_days'
    )

    def update_dynamic_fields(self):
        recurrence = self.fields['submission_recurrence']
        recurrence.widgetFactory = ParameterizedWidgetFactory(
            RecurrenceWidget, start_field='submission_date'
        )

        self.fields['submission_date_type'].widgetFactory = RadioFieldWidget

        # plone.formwidget.recurrencewidget needs this... obviously?
        date_widget_fields = (
            'submission_date',
            'submission_range_start_date',
            'submission_range_end_date'
        )
        for field in date_widget_fields:
            self.fields[field].widgetFactory = ParameterizedWidgetFactory(
                DateWidget, first_day=first_weekday_sun0
            )

        self.fields['submission_days'].widgetFactory = CheckBoxFieldWidget

        default_date = date.today()
        self.fields['submission_date'].field.default = default_date
        self.fields['submission_range_start_date'].field.default = default_date
        self.fields['submission_range_end_date'].field.default = default_date


class LocationGroup(EventBaseGroup):

    label = _(u'Location')

    group_fields = OrderedDict()
    group_fields[IEventsDirectoryItem] = (
        'locality', 'street', 'housenumber', 'zipcode', 'town', 'location_url'
    )


class MapGroup(EventBaseGroup):

    label = _(u'Map')

    dynamic_fields = ('wkt', )

    group_fields = OrderedDict()
    group_fields[IGeoManager] = (
        'wkt',
    )

    def update_widgets(self):
        self.widgets['wkt'].label = _(u'Coordinates')

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

    coordinates = None

    def directory(self):
        return self.context

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

    def check_coordinates_present(self):
        try:
            geo = IGeoreferenced(self.context)
            if geo.type:
                return
        except TypeError:
            pass

        self.context.plone_utils.addPortalMessage(
            _(
                u'No location set. The event will not be displayed in the'
                u' map.'
            ), 'warning'
        )

    def handle_cancel(self):
        try:
            clear_token(self.context)
        except ComponentLookupError:
            pass
        IStatusMessage(self.request).add(
            _(u"Event submission cancelled"), "info"
        )
        self.request.response.redirect(self.directory.absolute_url())


class EventSubmitForm(extensible.ExtensibleForm, form.Form, NavigationMixin):
    """Event submission form mainly targeted at anonymous users.

    This form combines add- and edit-form functionality to streamline
    the user's experience. The idea is that this form and the
    PreviewForm below work in tandem:

    1. User opens directory/submit and enters an event (add-form)
    2. User saves result and is directed to directory/event/preview
    3. User changes his mind and clicks the back button
    4. User resubmits the form (which is now an edit-form)

    This can go back and forth providing a tight feedback-loop.
    If an edit form is thrown into the mix, the back button cannot
    work correctly because it will lead the user to the add form
    even if he really means to edit.

    The form is an edit-form if the user has a token in the session which
    machtes an existing event in preview state.

    The form is an add-form if the user does not have a token or it does
    not exist in the database.

    If the user clicks 'cancel' the token is thrown away, leaving
    an event in limbo. This will be cleaned up by a cron job.

    """

    implements(IDirectoryPage)

    grok.name('submit')
    grok.require('cmf.RequestReview')
    grok.context(IEventsDirectory)

    template = ViewPageTemplateFile('templates/form.pt')

    portal_type = 'seantis.dir.events.item'

    groups = (
        GeneralGroup, DateGroup, LocationGroup, MapGroup, InformationGroup
    )
    enable_form_tabbing = False

    label = _(u'Event Submission Form')
    description = _(u'Send us your events and we will publish them')

    # if true, render() will return nothing
    empty_body = False

    def __init__(self, context, request, fti=None):
        super(EventSubmitForm, self).__init__(context, request)

        # do not show the edit/action bar
        self.request['disable_border'] = True

    def __of__(self, context):
        return self

    def update(self):
        self.setup_form()
        super(EventSubmitForm, self).update()

    def render(self):
        if self.directory.submit_event_link:
            self.redirect(self.directory.submit_event_link)
            return ''

        if self.empty_body:
            return ''

        return super(EventSubmitForm, self).render()

    def redirect(self, url):
        self.empty_body = True
        self.request.response.redirect(url)

    def message(self, message, type="info"):
        IStatusMessage(self.request).add(message, type)

    @property
    def directory(self):
        return self.context

    def form_type(self):
        self.event = event_by_token(
            self.directory, current_token(self.request)
        )
        return self.event and 'editform' or 'addform'

    def setup_form(self):
        self.buttons = button.Buttons()
        self.handlers = button.Handlers()

        if self.form_type() == 'addform':
            preview = button.Button(title=_(u'Continue'), name='save')
            self.buttons += button.Buttons(preview)

            preview_handler = button.Handler(
                preview, self.__class__.handle_preview
            )
            self.handlers.addHandler(preview, preview_handler)

            self.ignoreContext = True
            self.ignoreReadonly = True
        else:
            update = button.Button(title=_(u'Continue'), name='save')
            self.buttons += button.Buttons(update)

            update_handler = button.Handler(
                update, self.__class__.handle_update
            )
            self.handlers.addHandler(update, update_handler)

            self.context = self.event

        cancel = button.Button(title=_(u'Cancel'), name='cancel')
        self.buttons += button.Buttons(cancel)

        cancel_handler = button.Handler(cancel, self.__class__.handle_cancel)
        self.handlers.addHandler(cancel, cancel_handler)

    def prepare_coordinates(self, data):
        """ The coordinates need to be verified and converted. First they are
        converted and kept out of the item creation process. Later they
        are added to the object once that exists.

        """
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

    def prepare_submission(self, data):
        self.submission = {}

        submission_fields = IEventSubmissionData.names()
        submitted_fields = data.keys()

        for field in submitted_fields:
            if field in submission_fields:
                self.submission[field] = data[field]
                del data[field]

    def apply_submission(self, content):
        submission = IEventSubmissionData(content)

        for field, value in self.submission.items():
            setattr(submission, field, value)

        submission.inject_sane_dates()

    def handle_preview(self, action):
        data, errors = self.extractData()
        validate_event_submission(data)

        if errors:
            self.status = self.formErrorsMessage
            return

        obj = self.create_and_add(data)
        if obj is not None:
            url = self.context.absolute_url() + '/' + obj.id + '/preview'
            self.redirect(append_token(obj, url))

    def handle_update(self, action):
        data, errors = self.extractData()
        validate_event_submission(data)

        if errors:
            self.status = self.formErrorsMessage
            return

        self.prepare_coordinates(data)
        self.apply_coordinates(self.getContent())

        self.prepare_submission(data)
        self.apply_submission(self.getContent())

        changes = self.applyChanges(data)

        if changes:
            self.message(_(u'Event Preview Updated'))
        else:
            self.message(_(u'No changes were applied'))

        url = self.context.absolute_url() + '/preview'
        self.redirect(append_token(self.context, url))

    def handle_cancel(self, action):
        try:
            clear_token(self.context)
        except ComponentLookupError:
            pass

        self.message(_(u"Event submission cancelled"))
        self.redirect(self.directory.absolute_url())

    def create(self, data):
        data['timezone'] = default_timezone()

        self.prepare_coordinates(data)
        self.prepare_submission(data)

        content = createContent('seantis.dir.events.item', **data)

        if IAcquirer.providedBy(content):
            content = content.__of__(aq_inner(self.context))

        # must be done before adding to the container
        self.apply_submission(content)

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

    def create_and_add(self, data):
        obj = self.create(data)
        zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(obj))
        self.add(obj)
        return obj

    @property
    def allow_edit(self):
        return True

    @property
    def import_source(self):
        return ""


class EventEditForm(EventSubmitForm):

    implements(IDirectoryPage)

    grok.name('edit')
    grok.require('cmf.ModifyPortalContent')
    grok.context(IEventsDirectoryItem)

    @property
    def allow_edit(self):
        return not IExternalEvent.providedBy(self.context)

    @property
    def import_source(self):
        try:
            result = IExternalEvent(self.context).source
        except:
            result = ""
        return result

    def setup_form(self):
        self.buttons = button.Buttons()
        self.handlers = button.Handlers()

        save = button.Button(title=_(u'Save Event'), name='save')
        self.buttons += button.Buttons(save)

        save_handler = button.Handler(save, self.__class__.handle_save)
        self.handlers.addHandler(save, save_handler)

        self.event = self.context

        cancel = button.Button(
            title=_(u'Cancel Event Submission'), name='cancel'
        )
        self.buttons += button.Buttons(cancel)

        cancel_handler = button.Handler(cancel, self.__class__.handle_cancel)
        self.handlers.addHandler(cancel, cancel_handler)

    def handle_save(self, action):
        if not self.allow_edit:
            self.message(_(u'Imported events may not be edited, '
                           u'no changes where applied'))
            return

        data, errors = self.extractData()
        validate_event_submission(data)

        if errors:
            self.status = self.formErrorsMessage
            return

        self.prepare_coordinates(data)
        self.apply_coordinates(self.getContent())

        self.prepare_submission(data)
        self.apply_submission(self.getContent())

        changes = self.applyChanges(data)

        if changes:
            self.message(_(u'Event Saved'))
        else:
            self.message(_(u'No changes were applied'))

        url = self.context.absolute_url()
        self.redirect(append_token(self.context, url))


class IPreview(form.Schema):
    title = TextLine(required=False)


class DetailPreviewWidget(widget.Widget):

    _template = ViewPageTemplateFile('templates/previewdetail.pt')

    def render(self):
        self.directory = self.context.get_parent()
        return self._template(self)

    def safe_html(self, html):
        return base_utils.safe_html(html)


class ListPreviewWidget(DetailPreviewWidget):

    _template = ViewPageTemplateFile('templates/previewlist.pt')
    show_map = False

    @base_utils.cached_property
    def occurrence_groups(self):
        dr = dates.DateRanges()
        start, end = dr.this_year[0], dr.next_year[1]
        result = grouped_occurrences(
            occurrences(self.context, start, end), self.request
        )
        return result

    @base_utils.cached_property
    def occurrences_count(self):
        count = 0

        for day, occurrences in self.occurrence_groups.items():
            count += len(occurrences)

        return count


def DetailPreviewFieldWidget(field, request):
    """IFieldWidget factory for MapWidget."""
    return widget.FieldWidget(field, DetailPreviewWidget(request))


def ListPreviewFieldWidget(field, request):
    """IFieldWidget factory for MapWidget."""
    return widget.FieldWidget(field, ListPreviewWidget(request))


class PreviewGroup(EventBaseGroup):

    label = _(u'Detail Preview')

    dynamic_fields = ('title', )

    group_fields = OrderedDict()
    group_fields[IPreview] = ('title', )

    def update_dynamic_fields(self):
        self.fields['title'].widgetFactory = DetailPreviewFieldWidget


class ListPreviewGroup(PreviewGroup):

    label = _(u'List Preview')

    def update_dynamic_fields(self):
        self.fields['title'].widgetFactory = ListPreviewFieldWidget

    def update_widgets(self):
        occurrences = self.widgets['title'].occurrences_count
        if occurrences > 1:
            self.label = _(u'List Preview (${number} Occurrences)', mapping={
                'number': occurrences
            })
        else:
            self.label = _(u'List Preview (No Occurrences)')


class SubmitterGroup(EventBaseGroup):

    label = _(u'Submitter')

    dynamic_fields = ('submitter', 'submitter_email')

    group_fields = OrderedDict()
    group_fields[IEventsDirectoryItem] = ('submitter', 'submitter_email')
    group_fields[ITerms] = ('agreed', )

    def update_dynamic_fields(self):
        self.fields['submitter'].field.required = True
        self.fields['submitter_email'].field.required = True

        # remove the terms and conditions agreement if there is none
        if not self.context.get_parent().terms:
            del self.fields['agreed']
        else:
            # otherwise be sure to link to it
            url = self.context.get_parent().absolute_url() + '/@@terms'
            self.fields['agreed'].field.description = utils.translate(
                self.request, _(
                    u"I agree to the <a target='_blank' href='${url}'>"
                    u"Terms and Conditions</a>",
                    mapping={'url': url}
                )
            )


class PreviewForm(EventSubmissionForm, form.AddForm, NavigationMixin):

    implements(IDirectoryPage)

    grok.context(IEventsDirectoryItem)
    grok.name('preview')

    groups = (PreviewGroup, ListPreviewGroup)
    template = ViewPageTemplateFile('templates/previewform.pt')

    enable_form_tabbing = True

    label = _(u'Event Submission Preview')
    description = u''

    @property
    def directory(self):
        return self.context.get_parent()

    def current_token(self):
        return current_token(self.request)

    def update(self, *args, **kwargs):
        self.check_coordinates_present()
        verify_token(self.context, self.request)
        super(PreviewForm, self).update(*args, **kwargs)

    @button.buttonAndHandler(_('Continue'), name='save')
    def handleSubmit(self, action):
        self.request.response.redirect(
            append_token(
                self.context, self.context.absolute_url() + '/@@finish'
            )
        )

    @button.buttonAndHandler(_(u'Adjust'), name='adjust')
    def handleAdjust(self, action):
        self.request.response.redirect(
            append_token(
                self.context, self.directory.absolute_url() + '/@@submit'
            )
        )

    @button.buttonAndHandler(_(u'Cancel'), name='cancel')
    def handleCancel(self, action):
        self.handle_cancel()


class FinishForm(EventSubmissionForm, form.AddForm, NavigationMixin):

    implements(IDirectoryPage)

    grok.context(IEventsDirectoryItem)
    grok.name('finish')

    groups = (SubmitterGroup, )

    template = ViewPageTemplateFile('templates/finishform.pt')

    enable_form_tabbing = False

    label = _(u'Event Submission Finish')
    description = u''

    @property
    def directory(self):
        return self.context.get_parent()

    def current_token(self):
        return current_token(self.request)

    def update(self, *args, **kwargs):
        self.check_coordinates_present()
        verify_token(self.context, self.request)
        super(FinishForm, self).update(*args, **kwargs)

    @button.buttonAndHandler(_('Submit'), name='save')
    def handleSubmit(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self.context.submitter = data['submitter']
        self.context.submitter_email = data['submitter_email']

        clear_token(self.context)
        self.context.submit()
        IStatusMessage(self.request).add(_(u"Event submitted"), "info")
        self.request.response.redirect(self.directory.absolute_url())

    @button.buttonAndHandler(_(u'Back'), name='back')
    def handleBack(self, action):
        self.request.response.redirect(
            append_token(
                self.context, self.context.absolute_url() + '/@@preview'
            )
        )

    @button.buttonAndHandler(_(u'Cancel'), name='cancel')
    def handleCancel(self, action):
        self.handle_cancel()
