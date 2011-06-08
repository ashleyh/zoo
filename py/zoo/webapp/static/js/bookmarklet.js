(function() {
    var getText = function(selector, exclude) {
        return selector.contents().map(function (i, elt) {
            if (elt == exclude) {
                return ''
            } else if (elt.nodeType == Node.TEXT_NODE) {
                return elt.nodeValue
            } else if (elt.tagName == 'BR') {
                return '\n' // sigh
            } else {
                return getText($(elt))
            }
        }).get().join('')
    }            

    var main = function($) {
        // inject css
        $('head').append(
            $('<link/>').attr({
                rel: 'stylesheet',
                type: 'text/css',
                href: window.zooRoot + '/static/css/bookmarklet.css?' + Math.random()
            })
        )

        // add hover handler
        var name = 'zooLink' // where we store the new element
        $('pre').hover(
            function() {
                console.log('hover-in')
                if (name in this) {
                    // this shouldn't happen...
                    console.log('problem...', this)
                } else {
                    var that = this
                    this[name] = $('<a/>')
                        .text('foo')
                        .addClass('zoo-bookmarklet-link')
                        .appendTo($(this))
                        .fadeIn('fast')
                        .position({
                            my: 'right top',
                            at: 'right top',
                            of: $(this)
                        })
                        .text('run in zoo')
                        .click(function() {
                            console.log(getText($(that), this))
                        })
                }                
            },
            function() {
                console.log('hover-out')
                if (name in this) {
                    this[name].fadeOut('fast').remove()
                    delete this[name]
                } else {
                    // this shouldn't happen...
                    console.log('problem...', this)
                }
            }
        )
    }

    var addScript = function(url, callback) {
        var e = document.createElement('script')
        e.setAttribute('src', url)
        document.body.appendChild(e)
        e.onreadystatechange = function() {
            if (e.readyState == 'complete') {
                callback(e)
            }
        }
        e.onload = function() {
            callback(e)
        }
    }
            
    var addScripts = function(urls, callback) {
        if (urls.length == 0) {
            callback()
        } else {
            addScript(
                urls[0],
                function() { addScripts(urls.slice(1), callback); }
            )
        }
    }

    // XXX does injecting jquery break sites that depend on
    // a different version of jquery?
    addScripts(
        [
            'http://code.jquery.com/jquery-1.6.1.min.js',
            'http://code.jquery.com/ui/1.8.13/jquery-ui.min.js'
        ],
        function() {
            main(jQuery)
        }
    )
})();
