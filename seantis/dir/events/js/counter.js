var inputtext_countdown = function($, input, label, template, maxlength) {
    
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

    $input.keypress(function() {
        $label.text(gettext(getlength()));
    });
}

jQuery(document).ready(function() {
    inputtext_countdown($,
        '#formfield-form-widgets-short_description textarea',
        '#formfield-form-widgets-short_description span.formHelp',
        '${chars} Zeichen verbleibend',
        140
    ); 
});