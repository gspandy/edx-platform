(function(define) {
    'use strict';

    define([
        'jquery',
        'course_bookmarks/js/views/bookmarks_list_button'
    ],
        function($, BookmarksListButton) {
            return function(options) {  // eslint-disable-line
                new BookmarksListButton();  // eslint-disable-line no-new
            };
        }
    );
}).call(this, define || RequireJS.define);
