(function($) {

    $(document).ready(function() {
        $(".event-navigation-filter > span").click(function() {
            var open = $(this).siblings('ul').is(":visible");
            $(".event-navigation-filter > ul").hide();
            if (!open) {
                $(this).siblings('ul').show();
            }
        });
    });
})( jQuery );
