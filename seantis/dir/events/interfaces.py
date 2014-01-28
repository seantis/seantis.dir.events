import logging
log = logging.getLogger('seantis.dir.events')

import imghdr
import magic

from collective.dexteritytextindexer import searchable
from plone.namedfile.field import NamedImage, NamedFile
from plone.app.event.dx.behaviors import first_weekday_sun0
from plone.directives import form
from plone.app.z3cform.wysiwyg import WysiwygFieldWidget
from plone.autoform.interfaces import IFormFieldProvider
from plone.formwidget.recurrence.z3cform.widget import RecurrenceWidget
from zope.schema import Text, TextLine, Bool, List, Choice, Time, Date
from zope.interface import Invalid, Interface, Attribute, alsoProvides
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from seantis.plonetools.schemafields import Email, Website

from seantis.dir.base.interfaces import (
    IDirectory,
    IDirectoryItem,
    IDirectoryItemCategories
)

from seantis.dir.events import _


days = SimpleVocabulary(
    [
        SimpleTerm(value='MO', title=_(u'Mo')),
        SimpleTerm(value='TU', title=_(u'Tu')),
        SimpleTerm(value='WE', title=_(u'We')),
        SimpleTerm(value='TH', title=_(u'Th')),
        SimpleTerm(value='FR', title=_(u'Fr')),
        SimpleTerm(value='SA', title=_(u'Sa')),
        SimpleTerm(value='SU', title=_(u'Su')),
    ]
)

# cannot use the comprehension in the zope interface definition
# because zope takes some weird magic to work
days.keys = [str(d.value) for d in days._terms]


class ITokenAccess(Interface):

    def attach_token(self, token=None):
        "Optionally create and store the access token."

    def has_access(self, request):
        "Return true if the given request has access on the context"

    def clear_token(self):
        "Remove the token from context and session."


class IActionGuard(Interface):

    def allow_action(self, action, item):
        """Return true if the given workflow_events action is allowed.
        The item can currently be a brain or not which is fugly, so maybe
        don't use for now and wait for a better implementation."""


class IExternalEvent(Interface):

    source = Attribute("Name of external source -> seantis.dir.events.sources")
    source_id = Attribute("""
        Id of external source event. External sources may use the same id
        for multiple events. If the id already exists when fetching the source
        the source is used and the existing events with the same id are deleted
    """)


class IEventsDirectory(IDirectory):
    """Extends the seantis.dir.base.directory.IDirectory"""

    image = NamedImage(
        title=_(u'Image'),
        required=False,
        default=None
    )

    searchable('terms')
    terms = Text(
        title=_(u'Terms and Conditions'),
        description=_(
            u'If entered, the terms and conditions have '
            u'to be agreed to by anyone submitting an event.'
        ),
        required=False,
        default=None
    )
    form.widget(terms=WysiwygFieldWidget)

# Hide all categories as they are predefined
IEventsDirectory.setTaggedValue(
    'seantis.dir.base.omitted',
    [
        'cat1',
        'cat2',
        'cat3',
        'cat4',
        'cat3_suggestions',
        'cat4_suggestions',
        'cat1_descriptions',
        'cat2_descriptions',
        'cat3_descriptions',
        'cat4_descriptions',
        'allow_custom_categories'  # always locked
    ]
)

IEventsDirectory.setTaggedValue('seantis.dir.base.labels', {
    'cat1_suggestions': _("Suggested Values for the What-Category"),
    'cat2_suggestions': _("Suggested Values for the Where-Category"),
})


class IEventsDirectoryItem(IDirectoryItem):
    """Extends the seantis.dir.IDirectoryItem."""

    submitter = TextLine(
        title=_(u'Submitter Name'),
        required=False,
    )

    submitter_email = Email(
        title=_(u'Submitter Email'),
        required=False,
    )

    searchable('short_description')
    short_description = Text(
        title=_(u'Short Description'),
        description=_(u'Up to 140 characters'),
        required=True,
        max_length=140
    )

    searchable('long_description')
    long_description = Text(
        title=_(u'Long Description'),
        required=False
    )

    image = NamedImage(
        title=_(u'Image'),
        required=False
    )

    attachment_1 = NamedFile(
        title=_(u'Attachment 1'),
        required=False
    )

    attachment_2 = NamedFile(
        title=_(u'Attachment 2'),
        required=False
    )

    searchable('locality')
    locality = TextLine(
        title=_(u'Locality'),
        required=False
    )

    searchable('street')
    street = TextLine(
        title=_(u'Street'),
        required=False
    )

    searchable('housenumber')
    housenumber = TextLine(
        title=_(u'Housenumber'),
        required=False
    )

    searchable('zipcode')
    zipcode = TextLine(
        title=_(u'Zipcode'),
        required=False
    )

    searchable('town')
    town = TextLine(
        title=_(u'Town'),
        required=False
    )

    searchable('location_url')
    location_url = Website(
        title=_(u'Location Website'),
        required=False
    )

    searchable('event_url')
    event_url = Website(
        title=_(u'Event Website'),
        required=False
    )

    searchable('organizer')
    organizer = TextLine(
        title=_(u'Organizer'),
        required=False
    )

    searchable('contact_name')
    contact_name = TextLine(
        title=_(u'Contact Name'),
        required=False
    )

    searchable('contact_email')
    contact_email = Email(
        title=_(u'Contact Email'),
        required=False
    )

    searchable('contact_phone')
    contact_phone = TextLine(
        title=_(u'Contact Phone'),
        required=False
    )

    searchable('prices')
    prices = Text(
        title=_(u'Prices'),
        required=False
    )

    searchable('registration')
    registration = Website(
        title=_(u'Ticket / Registration Website'),
        required=False
    )


# don't show these fields as they are not used
IEventsDirectoryItem.setTaggedValue(
    'seantis.dir.base.omitted', ['cat3', 'cat4', 'description']
)


class IEventSubmissionData(form.Schema):
    """ The event submission form uses this interfaces to get the event dates
    from the user, since the default IEventBasic interface turned out to be
    too confusing for many.

    """

    submission_date_type = List(
        title=_(u'When will this event occur?'),
        required=True,
        value_type=Choice(
            vocabulary=SimpleVocabulary([
                SimpleTerm(value='date', title=_(u'On a single day')),
                SimpleTerm(value='range', title=_(u'On several days'))
            ])
        ),
        default=['date']
    )

    submission_date = Date(
        title=_(u'Date'),
        required=False
    )

    submission_start_time = Time(
        title=_(u'Start time'),
        required=False
    )

    submission_end_time = Time(
        title=_(u'End time'),
        required=False
    )

    submission_range_start_date = Date(
        title=_(u'Start date'),
        required=False
    )

    submission_range_end_date = Date(
        title=_(u'End date'),
        required=False
    )

    submission_range_start_time = Time(
        title=_(u'Starts each day at'),
        required=False
    )

    submission_range_end_time = Time(
        title=_(u'Ends each day at'),
        required=False
    )

    submission_whole_day = Bool(
        title=_(u'All day'),
        required=False
    )

    submission_recurrence = Text(
        title=_(u'Recurrence'),
        required=False
    )

    submission_days = List(
        title=_(u'On these days'),
        value_type=Choice(vocabulary=days),
        required=False,
        default=days.keys
    )

    form.widget(
        'submission_recurrence', RecurrenceWidget,
        start_field='IEventSubmissionData.submission_date',
        first_day=first_weekday_sun0
    )


alsoProvides(IEventSubmissionData, IFormFieldProvider)


# force the user to select at least one value for each category
@form.validator(field=IDirectoryItemCategories['cat1'])
@form.validator(field=IDirectoryItemCategories['cat2'])
def validate_category(value):
    if not value:
        raise Invalid(_(u'Please choose at least one category'))


# to enforce the last rule, categories must exist
@form.validator(field=IEventsDirectory['cat1_suggestions'])
@form.validator(field=IEventsDirectory['cat2_suggestions'])
def validate_suggestion(value):
    if not value:
        raise Invalid(_(u'Please enter at least one suggestion'))


# images and attachments are limited in size
def check_filesize(value, size_in_mb, type):

    if value.getSize() > size_in_mb * 1024 ** 2:
        raise Invalid(
            _(
                u'${type} bigger than ${max} Megabyte are not allowed',
                mapping={'max': size_in_mb, 'type': type}
            )
        )


# Ensure that the uploaded image at least has an image header, a check
# which is important because users can upload files anonymously
@form.validator(field=IEventsDirectoryItem['image'])
def validate_image(value):
    if not value:
        return

    if not imghdr.what(value.filename, value.data):
        raise Invalid(_(u'Unknown image format'))

    check_filesize(value, 1, _(u'Images'))


# Attachments are limited to certain filetypes
mime_whitelist = {
    'application/pdf': _(u'PDF'),
}


@form.validator(field=IEventsDirectoryItem['attachment_1'])
@form.validator(field=IEventsDirectoryItem['attachment_2'])
def validate_attachment(value):
    if not value:
        return

    filetype = magic.from_buffer(value.data[:1024], mime=True)

    if not filetype in mime_whitelist:
        print filetype
        raise Invalid(
            _(
                u'Unsupported fileformat. Supported is ${formats}',
                mapping={'formats': u','.join(sorted(mime_whitelist.values()))}
            )
        )

    check_filesize(value, 10, _(u'Attachments'))


class ITerms(form.Schema):
    agreed = Bool(
        required=True, default=False
    )


@form.validator(field=ITerms['agreed'])
def validate_terms_and_conditions(agreed):
    if not agreed:
        raise Invalid(
            _(
                u'You have to agree to the terms '
                u'and conditions to submit this event'
            )
        )
