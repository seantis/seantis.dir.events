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
            return $.tmpl('counter-template', {'chars': 140 - length})[0].data;
        }
    };

    var update = function(e) {
        var length = getlength();
        
        if (length > maxlength) {
            $input.val($input.val().substring(0, maxlength));
        }
        
        $label.text(gettext(getlength()));
    };

    update();

    var events = ['keydown', 'paste', 'cut'];
    for (var i=0; i<events.length; i++) {
        $input.bind(events[0], function() {
            setTimeout(update, 25);
        });
    }

    $input.bind('keydown', update);
    $input.bind('paste', update);
    $input.bind('cut', update);
};

jQuery(document).ready(function() {
    inputtext_countdown($,
        '#formfield-form-widgets-short_description textarea',
        '#formfield-form-widgets-short_description span.formHelp',
        $('.event-submit-form').attr('data-countdown-template'),
        140);
});