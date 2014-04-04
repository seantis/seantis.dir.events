load_libraries(['jQuery', '_'], function($, _) {
    "use strict";

    var daterange_input_from = '.event-navigation-dates .custom-date-from';
    var daterange_input_to = '.event-navigation-dates .custom-date-to';
    var daterange_link = '.event-navigation-dates a.link-custom-date';

    var initalize_dateinput = function(dateinput) {
        var input = $(dateinput);
        var locale = input.data("locale");
        var ml = input.data("months");
        var ms = input.data("short-months");
        var dl = input.data("days");
        var ds = input.data("short-days");
        var fmt = input.data("format");
        var mindate = input.data("min-date");
        var maxdate = input.data("max-date");

        // localize
        if (locale && ml && ms && dl && ds) {
            jQuery.tools.dateinput.localize(locale,  {
                months:       ml,
                shortMonths:  ms,
                days:         dl,
                shortDays:    ds
            });
        } else {
            locale = 'en';
        }

        // initalize
        if (fmt && mindate && maxdate) {
            input.dateinput({
                min: mindate,
                max: maxdate,
                lang: locale,
                format: fmt
            });
        }
    };

    var daterange_change = function() {
        var from = $(daterange_input_from).data("dateinput");
        var to = $(daterange_input_to).data("dateinput");
        var a = $(daterange_link);
        var href = a.attr('href');

        if (from && to && href) {
            href = href.split('&')[0];
            href = href + '&from=' + from.getValue('yyyy-mm-dd');
            href = href + '&to=' + to.getValue('yyyy-mm-dd');
            a.attr('href', href);
            a[0].click();
        }
    };

    var register_change_handler = function(dateinput) {
        var api = $(dateinput).data("dateinput");
        if (api) {
            api.change(daterange_change);
        }
    };

    $(document).ready(function() {
        initalize_dateinput(daterange_input_from);
        initalize_dateinput(daterange_input_to);
        register_change_handler(daterange_input_from);
        register_change_handler(daterange_input_to);
    });
});