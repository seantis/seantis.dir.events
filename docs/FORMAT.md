# Export/Import Format

## Format

The events are exported as JSON. Calling the export view returns an array of event objects of the following format:

| Name              | Type             | Opt. *3)* | Description                              |
| ----------------- | ---------------- | --------- | ---------------------------------------- |
| last_update       | String           | -         | The date and time of the last change. ISO 8601 format. |
| id                | String           | *         | The unique identifier of the event.      |
| url               | String           | *         | The URL of the event.                    |
| title             | String           | *         | The title of the event.                  |
| short_description | String           | *         | The short description of the event. Up to 140 characters. |
| long_description  | String           | -         | The long description of the event.       |
| cat1              | Array of Strings | *         | The *what* categories. A new category is automatically added to the existing categories. |
| cat2              | Array of Strings | *         | The *where* categories. A new category is automatically added to the existing categories. |
| start             | String           | *         | The start date and time of the event. ISO 8601 format (UTC). *2), 3)* |
| end               | String           | *         | The start date and time of the event. ISO 8601 format (UTC). |
| recurrence        | String           | *         | An iCalendar RRULE (RFC 2445) describing the recurrence of the event. *3)* |
| whole_day         | Boolean          | *         | True, if this is an all-day event.       |
| timezone          | String           | *         | The timezone of the event . It is the name in the form of `area/location` as used by the IANA tz database. *2)* |
| locality          | String           | -         | The name of the locatity this event happens. |
| street            | String           | -         | The street number of the locality.       |
| housenumber       | String           | -         | The house number of the locality.        |
| zipcode           | String           | -         | The zip code of the locality.            |
| town              | String           | -         | The town of the locality.                |
| location_url      | String           | -         | The URL to the locality.                 |
| organizer         | String           | -         | The organizer of this event.             |
| contact_name      | String           | -         | The name of the contact for this event.  |
| contact_phone     | String           | -         | The phone number of the contact for this event. |
| contact_email     | String           | -         | The e-mail address of the contact for this event. |
| prices            | String           | -         | A text providing information about the admission prices. |
| event_url         | String           | -         | An URL to the event (e.g. on the organizers website). |
| registration      | String           | -         | An URL to the registration for this event. |
| submitter         | String           | -         | The name of the submitter of this event. |
| submitter_email   | String           | -         | The e-mail of the submitter of this event. |
| images            | Array of Objects | -         | The image(s) for this event. Currently, only one image is supported. *4)* |
| attachements      | Array of Objects | -         | The attachements for this event. Currently, only two attachements are supported. *4)* |
| longitude         | Float            | -         | The longitude of the event.              |
| latitude          | Float            | -         | The latitude of the event.               |

*Note 1) Mandatory and optional fields (importing):* `*` = the field is mandatory, a valid value must be provided; `-` = the field is optional, the field might be `null`.

*Note 2) Date and timezone:* The start and end dates are in UTC, use the provided timezone to localized them.

*Note 3) Date and recurrence:* It is possible to use a recurrence rule (RRULE) to describe the recurrences of this event. If RRULES are used, the start and end dates are the dates of the first occurrence. If RRULES are not used (the RRULE is an empty string), each occurence is exported as a single event.

*Note 4) Images and Attachements*: For each image or attachement, an object provides a `name` (String, mandatory) and an `url` (String, mandatory).



## Exporting

To export the calendar as JSON, open `{URL to Calendar}?type=json`. The following (optional) query parameters can be used to adjust the results:

| Name       | Type    | Description                              |
| ---------- | ------- | ---------------------------------------- |
| max        | Integer | The maximum number of results.           |
| filter     | Any     | If this parameter is provided, category filters are used (see below). |
| cat1       | String  | Return only events with the given *what* category. Use together with "filter", e.g `filter=1&cat1=somehting`. |
| cat2       | String  | Return only events with the given *where* category. Use together with "filter", e.g `filter=1&cat2=somewhere`. |
| search     | String  | If this parameter is provided, searching is used (see below). |
| searchtext | String  | Return only events with the given search term. Use together with "filter", e.g `search=1&searchtext=something`. |
| compact    | Any     | If this parameter is provided, RRULES are used. |
| imported   | Any     | If this parameter is provided, events that have been imported are returned as well. |



## Importing

It is possible to provide a source for importing events. Just provide a web service that returns your events in the format specified (use RRULES whenever possible). Optionally implement the category filter parameters.
