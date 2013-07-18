var inputtext_countdown = function($, input, label, template, maxlength) {
    /*  Shows an input text countdown in a label and ensures that the
    max length is not overstepped.

    @$          instance of jQuery
    @input      jQuery instance or string selector for the input field
    @label      jQuery instance or string selector for the label where
                the countdown will be shown
    @template   jQuery template containing ${chars} where the count should
                be rendered
    @maxlength  the maximum length that should be enforced
    */

    // requires jquery.template to run
    if (typeof($.template) == "undefined") {
        return;
    }

    // ensure that the elements exist
    if ($(input).length === 0) return;
    if ($(label).length === 0) return;

    var $input = $(input);
    var $label = $(label);
    var initial_text = $label.text();

    $.template('counter-template', template);

    var getlength = function() {
        return $input.val().length;
    };

    var gettext = function(length) {
        if (length === 0) {
            return initial_text;
        } else {
            return $.tmpl('counter-template', {
                'chars': maxlength - length
            })[0].data;
        }
    };

    var update = function(e) {
        var length = getlength();

        if (length >= maxlength) {
            $input.val($input.val().substring(0, maxlength));
            length = maxlength;
        }

        $label.text(gettext(length));
    };

    var events = ['keydown', 'paste', 'cut'];
    var handler = function() {
        setTimeout(update, 25);
    };

    for (var i=0; i<events.length; i++) {
        $input.bind(events[i], handler);
    }

    update();
};

load_libraries(['jQuery'], function($) {
    $(document).ready(function() {
        var input = '#formfield-form-widgets-short_description textarea';
        var label = '#formfield-form-widgets-short_description span.formHelp';
        var template = $('.event-submit-form').attr('data-countdown-template');

        inputtext_countdown($, input, label, template, 140);
    });
});