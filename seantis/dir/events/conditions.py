from OFS.SimpleItem import SimpleItem

from zope.interface import implements, Interface
from zope.component import adapts
from zope.formlib import form

from zope.component.interfaces import IObjectEvent

from plone.contentrules.rule.interfaces import IExecutable, IRuleElementData

from plone.app.contentrules.browser.formhelper import AddForm, EditForm

from Acquisition import aq_inner

from seantis.dir.events import _
from seantis.dir.events.interfaces import ISourceCondition


class SourceCondition(SimpleItem):

    """The actual persistent implementation of the source condition element.
    
    Note that we must mix in SimpleItem to keep Zope 2 security happy.
    """
    implements(ISourceCondition, IRuleElementData)

    source = ''
    element = 'seantis.dir.events.conditions.source'

    @property
    def summary(self):
        return _(u"Source contains: ${source}",
                 mapping={'source': self.source})


class SourceConditionExecutor(object):

    """The executor for this condition.
    
    This is registered as an adapter in configure.zcml
    """
    implements(IExecutable)
    adapts(Interface, ISourceCondition, IObjectEvent)

    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        context = aq_inner(self.event.object)
        try:
            source = context.source
        except (AttributeError, TypeError,):
            # The object doesn't have a source
            return False
        if not self.element.source:
            # Any source
            return True
        try:
            matched = (source.split('/')[-1] == self.element.source)
            return matched
        except:
            return False


class SourceConditionAddForm(AddForm):

    """An add form for portal type conditions.
    """
    form_fields = form.FormFields(ISourceCondition)
    label = _(u"Add import source condition")
    description = _(
        u"An import source condition makes the rule apply only to content "
        u"with the given import source.")
    form_name = _(u"Configure source condition")

    def create(self, data):
        c = SourceCondition()
        form.applyChanges(c, self.form_fields, data)
        return c


class SourceConditionEditForm(EditForm):

    """An edit form for portal type conditions
    """
    form_fields = form.FormFields(ISourceCondition)
    label = _(u"Edit import source condition")
    description = _(
        u"An import source condition makes the rule apply only to content "
        u"with the given import source.")
    form_name = _(u"Configure source condition")
