console.log "ohai from coffeescript"
$ ->
    $('body').bind 'dragenter', (e) ->
        console.log 'event:', e
    $('body').bind 'drop', (e) ->
        console.log 'event:', e


