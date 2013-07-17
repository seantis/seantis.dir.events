/*

    Plone doesn't have the ability to define multiple javascript-dependencies

    it can do this:

    +--------+   +------------+   +-----------+
    | jquery |-->| underscore |-->| my-script |
    +--------+   +------------+   +-----------+

    but not this:

    +--------+
    | jquery |------+
    +--------+      |  +-----------+
                    +->| my-script |
    +------------+  |  +-----------+
    | underscore |--+
    +------------+

    This is a problem, because a script like underscore is defined in an
    external package (collective.js.underscore) and should not depend
    on jquery.

    This script is a less than pretty way to ensure that the dependent scripts
    are loaded first.

    Call as follows:

    load_libraries(['_', 'jQuery'], function(_, $) {
        // _ and $ are ready to use
    });

*/

var load_libraries = function(libraries, success) {
    "use strict";

    var load_library = function(library) {
        if (!_.isString(library)) return library;

        try {
            var lib = eval(library);
            if (! _.isUndefined(lib)) {
                return lib;
            }
        } catch (ReferenceError) { /* pass */}

        return library; // keep as is
    };

    var load_libraries = function() {
        libraries = _.map(libraries, load_library);
    };

    var done_loading = function() {
        load_libraries();

        return _.every(libraries, function(lib) {
            return ! _.isString(lib);
        });
    };

    limited_tries(function() {
        if (done_loading()) {
            _.defer(function() {
                success.apply(window, libraries);
            });
            return true;
        } else {
            return false;
        }
    });

};

var limited_tries = function(callback) {
    "use strict";

    var timeout = 25;
    var max_tries = 500; // amounts to over a minute of trying
    var current_try = 0;

    var check = function() {
        current_try += 1;

        // get slower over time
        if (current_try % 50 === 0) {
            timeout = timeout * 2;
        }

        if (callback()) {
            return; // done
        } else {
            if (current_try <= max_tries) {
                setTimeout(check, timeout);
            }
        }
    };

    check();
};
