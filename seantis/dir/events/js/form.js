(function($){

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
            '#formfield-form-widgets-submission_range_end_time'
        ]
    };

    var time_fields = [
        '#formfield-form-widgets-submission_start_time input',
        '#formfield-form-widgets-submission_end_time input',
        '#formfield-form-widgets-submission_range_start_time input',
        '#formfield-form-widgets-submission_range_end_time input'
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
                        digits.substring(0, 2),
                        digits.substring(2, 3) + '0'
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

        return limit(normalize(time));
    };

    var fix_time_inputs = function(e) {
        var input = $(this);
        input.val(force_valid_time(input.val()));
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
    });
})(jQuery);