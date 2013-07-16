load_libraries(['jQuery'], function($) {
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

    var submission_type = function(shown) {
        if (shown) {
            return $(submission_input + ':checked').val();
        } else {
            return $(submission_input + ':not(:checked)').val();
        }
    };

    var toggle_fields = function(fields, show) {
        for (var i=0; i<fields.length; i++) {
            $(fields[i]).toggle(show);
        }
    };

    var enable_fields = function(fields, enable) {
        for (var i=0; i<fields.length; i++) {
            $(fields[i]).prop('disabled', !enable);
        }
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

        for (var i=0; i < kept_in_sync.length; i++) {
            var pair = kept_in_sync[i];

            if (changed.is($(pair[0]))) {
                $(pair[1]).val(changed.val());
                continue;
            }

            if (changed.is($(pair[1]))) {
                $(pair[0]).val(changed.val());
                continue;
            }
        }
    };

    var sync_fields = function(e) {
        var date_type = $(this).val();
        var origin_index = date_type == 'date' ? 1 : 0;

        for (var i=0; i < kept_in_sync.length; i++) {
            sync_field(kept_in_sync[i][origin_index]);
        }
    };

    $(document).ready(function() {
        $(submission_input).change(update_submission_fields);
        $(wholeday_field).change(update_submission_fields);
        update_submission_fields();

        for (var i=0; i < time_fields.length; i++) {
            var field = $(time_fields[i]);

            field.attr('placeholder', 'hh:mm');
            field.change(fix_time_inputs);
        }

        $(date_type_field).change(sync_fields);
    });
});