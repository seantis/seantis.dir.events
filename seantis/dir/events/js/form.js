load_libraries(['jQuery', '_'], function($, _) {
    "use strict";

    var submission_input = 'input[name="form.widgets.submission_date_type"]';

    var submission_type_groups = {
        'date': [
            '#formfield-form-widgets-submission_date',
            '#formfield-form-widgets-submission_start_time',
            '#formfield-form-widgets-submission_end_time',
            '#formfield-form-widgets-submission_recurrence'
        ],
        'range': [
            '#formfield-form-widgets-submission_range_start_date',
            '#formfield-form-widgets-submission_range_end_date',
            '#formfield-form-widgets-submission_range_start_time',
            '#formfield-form-widgets-submission_range_end_time',
            '#formfield-form-widgets-submission_days'
        ]
    };

    var time_fields = [
        '#formfield-form-widgets-submission_start_time input',
        '#formfield-form-widgets-submission_end_time input',
        '#formfield-form-widgets-submission_range_start_time input',
        '#formfield-form-widgets-submission_range_end_time input'
    ];

    var date_type_field = '#formfield-form-widgets-submission_date_type input';

    var kept_in_sync = [
        [
            '#formfield-form-widgets-submission_start_time input',
            '#formfield-form-widgets-submission_range_start_time input'
        ],
        [
            '#formfield-form-widgets-submission_end_time input',
            '#formfield-form-widgets-submission_range_end_time input'
        ],
        [
            '#form-widgets-submission_date-day',
            '#form-widgets-submission_range_start_date-day'
        ],
        [
            '#form-widgets-submission_date-month',
            '#form-widgets-submission_range_start_date-month'
        ],
        [
            '#form-widgets-submission_date-year',
            '#form-widgets-submission_range_start_date-year'
        ]
    ];

    var wholeday_field = '#formfield-form-widgets-submission_whole_day input';

    var range_start_date = '#formfield-form-widgets-submission_range_start_date';
    var range_end_date = '#formfield-form-widgets-submission_range_end_date';

    var locality_fields = [
        '#form-widgets-street',
        '#form-widgets-housenumber',
        '#form-widgets-zipcode',
        '#form-widgets-town'
    ];

    var locality_search_field = "#form-widgets-wkt-map-geocoder input";

    var submission_type = function(shown) {
        if (shown) {
            return $(submission_input + ':checked').val();
        } else {
            return $(submission_input + ':not(:checked)').val();
        }
    };

    var toggle_fields = function(fields, show) {
        _.each(fields, function(field) {
            $(field).toggle(show);
        });
    };

    var enable_fields = function(fields, enable) {
        _.each(fields, function(field) {
            $(field).prop('disabled', !enable);
        });
    };

    var enable_time_fields = function() {
        return ! $(wholeday_field).prop('checked');
    };

    var update_submission_fields = function() {
        var shown_fields = submission_type_groups[submission_type(true)];
        var hidden_fields = submission_type_groups[submission_type(false)];

        toggle_fields(shown_fields, true);
        toggle_fields(hidden_fields, false);

        enable_fields(time_fields, enable_time_fields());
    };

    var get_fieldname_by_id = function(id) {
        return '#' + $(id).data('fieldname').replace(/\./g, '-');
    };

    var get_date = function(field) {
        var date = {};

        var fieldname = get_fieldname_by_id(field);
        date.year = $(fieldname + '-year').val();
        date.month = $(fieldname + '-month').val();
        date.day = $(fieldname + '-day').val();

        if (_.contains([date.year, date.month, date.day], undefined)) {
            return null;
        }

        date.year = parseInt(date.year, 10);
        date.month = parseInt(date.month, 10);
        date.day = parseInt(date.day, 10);

        return new Date(date.year, date.month - 1, date.day);
    };

    var set_date = function(field, date) {
        var fieldname = get_fieldname_by_id(field);
        $(fieldname + '-year').val(date.year);
        $(fieldname + '-month').val(date.month);
        $(fieldname + '-day').val(date.day);
    };

    var autoselect_days = function() {

        var start = get_date(range_start_date);
        var end = get_date(range_end_date);

        if (_.contains([start, end], null)) {
            return;
        }

        if (start > end) {
            return;
        }

        var ids = _.map([6, 0, 1, 2, 3, 4, 5],
            function(ix) {
                return '#form-widgets-submission_days-' + ix;
            }
        );

        var days = _.map(ids, function(id) { return $(id); });

        var span = ((end - start) / 1000 / 60 / 60 / 24) + 1;
        var first = start.getDay();
        var last = end.getDay();

        var checked = [];
        var i = 0;

        if (span >= 7) {
            checked = [0, 1, 2, 3, 4, 5, 6];
        } else if (first == last) {
            checked = [first];
        } else if (first < last) {
            for (i=first; i<=last; i++) {
                checked.push(i);
            }
        } else {
            for (i=0; i<= last; i++) {
                checked.push(i);
            }
            for (i=6; i>= first; i--) {
                checked.push(i);
            }
        }

        _.each(days, function(day) {
            day.removeAttr('checked');
        });

        _.each(checked, function(ix) {
            days[ix].attr('checked', 'checked');
        });
    };

    var pad = function(num, size) {
        var s = "000000000" + num;
        return s.substr(s.length-size);
    };

    var force_valid_time = function(time) {

        var twelve_hour_suffix = function(time) {
            if (time.indexOf('am') != -1)
                return ' AM';
            if (time.indexOf('AM') != -1)
                return ' AM';
            if (time.indexOf('pm') != -1)
                return ' PM';
            if (time.indexOf('PM') != -1)
                return ' PM';
            return '';
        };

        var normalize = function(time) {
            var digits = time.match(/\d+/g);

            if (digits === null) {
                return '';
            }

            digits = digits.join('').substring(0, 4);

            switch(digits.length) {
                case 0:
                    return '';
                case 1:
                    return '0' + digits + ':00';
                case 2:
                    return digits + ':00';
                case 3:
                    return [
                        '0' + digits.substring(0, 1),
                        digits.substring(1, 3)
                    ].join(':');
                default:
                    return [
                        digits.substring(0, 2),
                        digits.substring(2, 4)
                    ].join(':');
            }
        };

        var limit = function(time) {
            if (time.length === 0) {
                return '';
            }

            var components = time.split(':');
            var hour = parseInt(components[0], 10),
                minute = parseInt(components[1], 10);

            hour = hour > 23 ? 23 : hour;
            minute = minute > 59 ? 59 : minute;

            return pad(hour, 2) + ':' + pad(minute, 2);
        };

        return limit(normalize(time)) + twelve_hour_suffix(time);
    };

    var fix_time_inputs = function(e) {
        var input = $(this);
        input.val(force_valid_time(input.val()));
    };

    var sync_field = function(origin) {
        var changed = $(origin);

        _.each(kept_in_sync, function(pair) {
            if (changed.is($(pair[0]))) {
                $(pair[1]).val(changed.val());
                return;
            }

            if (changed.is($(pair[1]))) {
                $(pair[0]).val(changed.val());
                return;
            }
        });
    };

    var sync_fields = function(e) {
        var date_type = $(this).val();
        var origin_index = date_type == 'date' ? 1 : 0;

        _.each(kept_in_sync, function(pair) {
            sync_field(pair[origin_index]);
        });

        autoselect_days();
    };

    var locality = function(e) {
        var street = $(locality_fields[0]).val();
        var number = $(locality_fields[1]).val();
        var zip = $(locality_fields[2]).val();
        var town = $(locality_fields[3]).val();

        var locality = street;
        if (street && number) {
            locality += ' ' + number;
        }
        if (locality) {
            locality += ', ';
        }
        locality += zip;
        if (zip && town) {
            locality += ' ';
        }
        locality += town;

        return locality;
    };

    var update_map_widget = function(e) {
        var loc = locality();
        $(locality_search_field).val(loc);
    };

    $(document).ready(function() {
        $(submission_input).change(update_submission_fields);
        $(wholeday_field).change(update_submission_fields);
        update_submission_fields();

        _.each(time_fields, function(field) {
            var $field = $(field);

            $field.attr('placeholder', 'hh:mm');
            $field.change(fix_time_inputs);
        });

        $(date_type_field).change(sync_fields);

        $([range_start_date, range_end_date].join(', ')).change(function() {
            _.defer(autoselect_days);
        });

        _.each(locality_fields, function(field) {
            $(field).change(update_map_widget);
        });
        update_map_widget();
    });
});