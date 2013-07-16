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

    var libraries_loaded = function() {
        for (var i=0; i<libraries.length; i++) {
            if (typeof(libraries[i]) == 'string') {
                try {
                    var lib = eval(libraries[i]);
                    if (typeof(lib) === 'undefined') {
                        return false;
                    } else {
                        libraries[i] = lib;
                    }
                } catch (ReferenceError) {
                    return false;
                }
            }
        }

        return true;
    };

    limited_tries(function() {
        if (libraries_loaded()) {
            success.apply(window, libraries);
            return true;
        } else {
            return false;
        }
    }, 25, 1000);

};

var limited_tries = function(callback, timeout, max_tries) {
    var current_try = 0;

    var check = function() {
        current_try += 1;

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