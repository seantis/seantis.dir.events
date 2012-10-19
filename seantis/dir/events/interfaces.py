import imghdr
import magic

from dateutil.rrule import rrulestr

from collective.dexteritytextindexer import searchable
from plone.namedfile.field import NamedImage, NamedFile
from plone.directives import form
from plone.app.event.dx.behaviors import IEventRecurrence
from z3c.form import util, validator
from zope.schema import Text, TextLine, URI, List
from zope.interface import Invalid

from seantis.dir.base.schemafields import Email
from seantis.dir.base.interfaces import IDirectory, IDirectoryItem
from seantis.dir.events import _

class IEventsDirectory(IDirectory):
    """Extends the seantis.dir.base.directory.IDirectory"""

    image = NamedImage(
            title=_(u'Image'),
            required=False,
            default=None
        )

    locality_suggestions = List(
            title=_(u'Suggested Values for the Locality'),
            description=_(
                u'Will be shown as a list to choose from in the '
                u'anonymous submission form.'
            ),
            required=False,
            value_type=TextLine()
        )

# Hide all categories as they are predefined
IEventsDirectory.setTaggedValue('seantis.dir.base.omitted', 
    ['cat1', 'cat2', 'cat3', 'cat4', 'cat3_suggestions', 'cat4_suggestions']
)

IEventsDirectory.setTaggedValue('seantis.dir.base.labels', { 
    'cat1_suggestions': _("Suggested Values for the What-Category"),
    'cat2_suggestions': _("Suggested Values for the Where-Category"),
})

class IEventsDirectoryItem(IDirectoryItem):
    """Extends the seantis.dir.IDirectoryItem."""

    submitter = TextLine(
        title=_(u'Submitter Name'),
        required=False
    )

    submitter_email = Email(
        title=_(u'Submitter Email'),
        required=False,
    )

    searchable('short_description')
    short_description = Text(
        title=_(u'Short Description'),
        required=True
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

    searchable('event_url')
    event_url = TextLine(
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
    registration = URI(
        title=_(u'Ticket / Registration Website'),
        required=False
    )

# don't show these fields as they are not used
IEventsDirectoryItem.setTaggedValue('seantis.dir.base.omitted', 
    ['cat3', 'cat4', 'description']
)

# define the event items order
IEventsDirectoryItem.setTaggedValue('seantis.dir.base.order',
    ['title', 'cat1', 'cat2', 'short_description', 'long_description', 
     'IEventBasic.start', 'IEventBasic.end', 'IEventBasic.whole_day', 
     'IEventBasic.timezone', 'IEventRecurrence.recurrence', 
     'image','attachment_1', 'attachment_2', 'locality', 'street', 
     'housenumber', 'zipcode', 'town', 'event_url', 'organizer', 
     'contact_name', 'contact_email', 'contact_phone', 'prices', 
     'registration', '*'
    ]
)

# plone.app.event is currently not working well with an unlimited or huge
# number of recurrences with abysmal performance. For this reason the occurences
# are limited for now and the infinite option is hidden using recurrence.css
@form.validator(field=IEventRecurrence['recurrence'])
def validate_recurrence(value):
    if not value:
        return
        
    max_occurrences = 52 # one occurrence per week

    rrule = rrulestr(value)
    for ix, rule in enumerate(rrule):
        if ix > max_occurrences:
            raise Invalid(_(u'You may not add more than ${max} occurences',
                mapping={'number': max_occurrences}))

# images and attachments are limited in size
def check_filesize(value, size_in_mb, type):

    if value.getSize() > size_in_mb * 1024**2:
        raise Invalid(_(u'${type} bigger than ${max} Megabyte are not allowed',
            mapping={'max': size_in_mb, 'type': type}
        ))

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
    'application/pdf':_(u'PDF'),
}

@form.validator(field=IEventsDirectoryItem['attachment_1'])
@form.validator(field=IEventsDirectoryItem['attachment_2'])
def validate_attachment(value):
    if not value:
        return

    filetype = magic.from_buffer(value.data[:1024], mime=True)

    if not filetype in mime_whitelist:
        print filetype
        raise Invalid(_(u'Unsupported fileformat. Supported is ${formats}',
            mapping={'formats': u','.join(sorted(mime_whitelist.values()))}
        ))

    check_filesize(value, 10, _(u'Attachments'))

# Ensure that the event date is correct
class EventValidator(validator.InvariantsValidator):
    def validateObject(self, obj):
        errors = super(EventValidator, self).validateObject(obj)
        if obj.start > obj.end:
            errors += (Invalid(_(u'Event end before start')))
    
        return errors

validator.WidgetsValidatorDiscriminators(EventValidator, 
    schema=util.getSpecification(IEventsDirectoryItem, force=True)
)