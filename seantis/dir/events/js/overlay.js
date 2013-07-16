load_libraries(['jQuery'], function($) {
    $(document).ready(function() {
        $('.event-image a').prepOverlay({
             subtype: 'image'
        });
        $('#formfield-form-widgets-agreed .formHelp a').prepOverlay({
             subtype: 'ajax',
             filter: '#content > *',
             cssclass: 'event-terms'
        });
    });
});