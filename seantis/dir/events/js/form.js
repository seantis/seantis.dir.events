(function($){

    var submission_input = 'input[name="form.widgets.submission_date_type"]';

    var submission_type_groups = {
        'date': [
            '#formfield-form-widgets-date',
            '#formfield-form-widgets-start_time',
            '#formfield-form-widgets-end_time',
            '#formfield-form-widgets-recurrence'
        ],
        'range': [
            '#formfield-form-widgets-range_start_date',
            '#formfield-form-widgets-range_end_date',
            '#formfield-form-widgets-range_start_time',
            '#formfield-form-widgets-range_end_time'
        ]
    };

    var time_fields = [
        '#formfield-form-widgets-start_time input',
        '#formfield-form-widgets-end_time input',
        '#formfield-form-widgets-range_start_time input',
        '#formfield-form-widgets-range_end_time input'
    ];

    var wholeday_field = '#formfield-form-widgets-whole_day input';

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

    $(document).ready(function() {
        $(submission_input).change(update_submission_fields);
        $(wholeday_field).change(update_submission_fields);
        update_submission_fields();

        $(time_fields.join(', ')).timePicker({
            separator: ':'
        });
    });
})(jQuery);