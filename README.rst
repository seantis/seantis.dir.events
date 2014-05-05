Seantis Events
==============

Directory of upcoming Events.

seantis.dir.events builds on seantis.dir.base, adding information about
upcoming events.

seantis.dir.base allows to put dexterity objects into 1-4 categories, showing
those categories in a browsable and searchable catalog. To learn more about
seantis.dir.base visit https://github.com/seantis/seantis.dir.base.


Dependencies
------------

seantis.dir.events relies on Plone 4.3+ with dexterity and seantis.dir.base.

python-magic is used to identify the type of uploaded files which requires the
'libmagic' library.

Installation
------------

1. Use Plone 4.3 or newer

::

    extends =
        http://dist.plone.org/release/4.3/versions.cfg

2. Add the module to your instance eggs

::

    [instance]
    eggs +=
        seantis.dir.events


3. Ensure that the i18n files are compiled by adding

::

    [instance]
    ...
    environment-vars =
        ...
        zope_i18n_compile_mo_files true


4. Install dexterity and seantis.dir.events using portal_quickinstaller


Special Views
-------------

JSON export
~~~~~~~~~~~
* JSON export of all events: *?type=json*
* Export a limited number of events: *?type=json&max=10*
* Export all events with a given category: *?type=json&filter=1&cat1=text&cat2=text*
* Export all events with a given keyword: *?type=json&search=1&searchtext=text*
* Export events with RRULES: *?type=json&compact=1*

Index
~~~~~
* View event index: */eventindex*
* Rebuild Z-catalog: */eventindex?rebuild*
* Reindex event indices: */eventindex?reindex*

Cleanup
~~~~~~~
* Archive past events, remove stale previews and archived events: */cleanup?run=1*

Import
~~~~~~
* Import events: */fetch?run=1*
* Reimport event: */fetch?run=1&reimport=1*
* Import only events with a given ID: */fetch?run=1&source-ids=event1,event2*
* Don't process source in random order: */fetch?run=1&no_shuffle=1*


Setup
-----

Clean-up
~~~~~~~~

Cleaning up events is done by calling the corresponding up view.
This can either be done externally with a cron job or internally by setting the
following environment variable of the instance (which results in a daily
cleanup at 00:30):

::

    [instance]
    ...
    environment-vars =
        ...
        seantis_events_cleanup true


Import
~~~~~~

Importing events is done by calling the corresponding view.
This can either be done externally with a cron job or internally by setting the
following environment variable of the instance (which results in an import
every 15 minutes):

::

    [instance]
    ...
    environment-vars =
        ...
        seantis_events_import true

Build Status
------------

.. image:: https://api.travis-ci.org/seantis/seantis.dir.events.png?branch=master
  :target: https://travis-ci.org/seantis/seantis.dir.events
  :alt: Build Status


Coverage
--------

.. image:: https://coveralls.io/repos/seantis/seantis.dir.events/badge.png?branch=master
  :target: https://coveralls.io/r/seantis/seantis.dir.events?branch=master
  :alt: Project Coverage


Latests PyPI Release
--------------------
.. image:: https://pypip.in/v/seantis.dir.events/badge.png
  :target: https://crate.io/packages/seantis.dir.events
  :alt: Latest PyPI Release


License
-------
seantis.dir.events is released under GPL v2
