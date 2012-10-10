import imghdr
from datetime import datetime
from subprocess import Popen, PIPE

from five import grok
from zope.schema import Text, TextLine, URI
from zope.interface import Invalid
from collective.dexteritytextindexer import searchable
from plone.namedfile.field import NamedImage, NamedFile
from plone.directives import form
from plone.memoize import view
from plone.app.event.dx.behaviors import IEventRecurrence
from dateutil.rrule import rrulestr

from z3c.form import util, validator

from seantis.dir.base import item
from seantis.dir.base import core
from seantis.dir.base.schemafields import Email
from seantis.dir.base.interfaces import IFieldMapExtender, IDirectoryItem

from seantis.dir.events import utils
from seantis.dir.events import dates
from seantis.dir.events import recurrence
from seantis.dir.events.directory import IEventsDirectory
from seantis.dir.events import _
  
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

    searchable('website')
    website = URI(
        title=_(u'Website'),
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
        title=_(u'Tickets / Registration'),
        required=False
    )

IEventsDirectoryItem.setTaggedValue('seantis.dir.base.omitted', 
    ['cat3', 'cat4', 'description']
)

IEventsDirectoryItem.setTaggedValue('seantis.dir.base.order',
    ['title', 'cat1', 'cat2', 'short_description', 'long_description', 
     'IEventBasic.start', 'IEventBasic.end', 'IEventBasic.whole_day', 
     'IEventBasic.timezone', 'IEventRecurrence.recurrence', 
     'image','attachment_1', 'attachment_2', 'locality', 'street', 
     'housenumber', 'zipcode', 'town', 'website', 'organizer', 'contact_name', 
     'contact_email', 'contact_phone', 'prices', 'registration', '*'
    ]
)

# plone.app.event is currently not working well with an unlimited or huge
# number of recurrences with abysmal performance. For this reason the occurences
# are limited for now and the infinite option is hidden using recurrence.css
@form.validator(field=IEventRecurrence['recurrence'])
def validate_recurrence(value):
    if not value:
        return
        
    rrule = rrulestr(value)
    for ix, rule in enumerate(rrule):
        if ix > 52: # one occurrence per week
            raise Invalid(_(u'You may not add more than 52 occurences'))

# Ensure that the uploaded image at least has an image header, a check
# which is important because users can upload files anonymously
@form.validator(field=IEventsDirectoryItem['image'])
def validate_image(value):
    if not value:
        return

    if not imghdr.what(value.filename, value.data):
        raise Invalid(_(u'Unknown image format'))

# Attachments are limited to certain filetypes
mime_whitelist = {
    'application/pdf':_(u'PDF'),
}

# unix only currently (-> /user/bin/file)
utils.assert_unix()

@form.validator(field=IEventsDirectoryItem['attachment_1'])
@form.validator(field=IEventsDirectoryItem['attachment_2'])
def validate_attachment(value):
    if not value:
        return

    filecheck = Popen("/usr/bin/file -b --mime -", 
        shell=True, stdout=PIPE, stdin=PIPE
    ) 
    filetype = filecheck.communicate(value.data[:1024])[0].strip().split(';')[0]

    if not filetype in mime_whitelist:
        raise Invalid(_(u'Unsupported Fileformat. Supported is ${formats}',
            mapping={'formats': u','.join(sorted(mime_whitelist.values()))}
        ))

# Ensure that the event date is corrent
class EventValidator(validator.InvariantsValidator):
    def validateObject(self, obj):
        errors = super(EventValidator, self).validateObject(obj)
        if obj.start > obj.end:
            errors += (Invalid(_(u'Event start before end')))
    
        return errors

validator.WidgetsValidatorDiscriminators(EventValidator, 
    schema=util.getSpecification(IEventsDirectoryItem, force=True)
)

class EventsDirectoryItem(item.DirectoryItem):
    pass

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

    template = grok.PageTemplateFile('templates/item.pt')
    hide_search_viewlet = True

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
    def start(self):
        occurrence = self.occurrence or self.context
        return occurrence.start

    @property
    def end(self):
        occurrence = self.occurrence or self.context
        return occurrence.end

    @property
    def human_date(self):
        return dates.human_date(self.start, self.request)

    @property
    def human_daterange(self):
        return dates.human_daterange(self.start, self.end)

    @property
    @view.memoize
    def occurrence(self):
        date = self.date
        if date and self.is_recurring:
            return recurrence.pick_occurrence(self.context, self.date)
        else:
            return None

    @property
    def occurrence_exists(self):
        return self.occurrence and True or False

    @property
    @view.memoize
    def occurrences(self):
        min_date, max_date = dates.event_range()
        
        return recurrence.occurrences(self.context, min_date, max_date)

    def attachment_filename(self, attachment):
        filename = getattr(self.context, attachment).filename
        if len(filename) > 30:
            return filename[:30] + '...'
        else:
            return filename

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
            "housenumber", "zipcode", "town", "website", "organizer",
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