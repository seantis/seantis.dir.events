
Changelog
---------

1.3 (2014-06-23)
~~~~~~~~~~~~~~~~~~

- Allow export of imported events. Implements #68.
  [msom]

- Display number of removed already imported events in fetch view.
  Implements #71.
  [msom]

- Fix cleanup scheduler.
  [msom]

- Prevent creation of log entries by viewing the events. Updates #70.
  [msom]

- Split guidle events that last over a day. Fixes #50.
  [msom]

1.2.4 (2014-06-04)
~~~~~~~~~~~~~~~~~~

- Add upgrade step to ensure source-index is set up.
  [msom]

1.2.3 (2014-05-08)
~~~~~~~~~~~~~~~~~~

- Handle timezones correctly in import/export. Fixes #60.
  [msom]

1.2.2 (2014-05-05)
~~~~~~~~~~~~~~~~~~

- Remove profile function.
  [msom]

- Remove pages. Implements #51.
  [msom]

- Reindex directory during transaction, clean up and import events in a
  specific instance. Fixes #52.
  [msom]

1.2.1 (2014-04-28)
~~~~~~~~~~~~~~~~~~

- Allow concurrent import in different directories.
  [msom]


1.2 (2014-04-28)
~~~~~~~~~~~~~~~~

- Add import.
  [msom]

1.1.1 (2014-04-24)
~~~~~~~~~~~~~~~~~~

- Move event submission link to top and style it as button
  [msom]

1.1 (2014-04-07)
~~~~~~~~~~~~~~~~

- Add locality to list view. Implements #40.
  [msom]

- Show organizer and ticket / registration website on detail view.
  Implements #41.
  [msom]

- Set coordinates using the location. Implements #43.
  [msom]

- Add custom date filter. Implements #33.
  [msom]

1.0.1 (2014-02-15)
~~~~~~~~~~~~~~~~~~

- Fixes a rare bug occurring when an event exist for the last day of a year,
  but no events exist for the whole next year. Fixes #37.
  [href]

1.0
~~~

- Removes plone.app.event.dx profile depencency - it is deprecated.
  [href]

- Adds plone.app.event.ploneintegration profile dependency.
  [href]

- Integrates seantis.plonetools.
  [href]

- Search with no results no longer shows all events.
  [msom]

- Upgrade steps are no longer displayed in the coverage report.
  [msom]

- Update teamraum theme integration.
  [msom]

- Show a single today's whole-day event correctly.
  [msom]

1.0rc3
~~~~~~

- Add JSON export.
  [msom]

1.0rc2
~~~~~~

- Stops event reindexing from running more than once per transaction.
  [href]

- Makes event reindexing threadsafe.
  [href]

- Add tests.
  [msom]

1.0rc1
~~~~~~

- Fixes ical export error
  [href]

- Fixes typos in add event form
  [msom]

- Fixes date formating with superfluous point
  [msom]

- Upgrade to seantis.dir.base 1.7
  [msom]

1.0a3
~~~~~~

- Bind event reindexing directly to the transaction

- Fixes errors when using plone.app.event 1.0rc2

1.0a2
~~~~~~

- It is now easier to enter common events like events which happen on a single
  day, or events which happen on different days.

- All-day events in different timezones than the server no longer lead to
  crashes in the middle of the night

- Events are no longer shown on the wrong day

- Single events are no longer shown twice

- Deleting an event (as opposed to denying it's publication) no longer results
  in a corrupt event index.

- Event submission now works in IE7/IE8 on Windows XP

1.0a1
~~~~~~

- Initial release
