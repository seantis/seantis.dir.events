
Changelog
---------

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
