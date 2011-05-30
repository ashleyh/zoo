from zoo import config
from flask import Flask
my_flask = Flask(__name__)
import zoo.webapp.app # adds stuff to my_flask

def run():
    print 'starting webapp server on {0}:{1}'.format(
        config.ZOO_WEBAPP_HOST, config.ZOO_WEBAPP_PORT
    )

    #XXX the reloader doesn't work.
    # i have absolutely no idea why.
    # see stupid_reloader.py.
    my_flask.run(
        debug=True,
        use_reloader=False,
        host=config.ZOO_WEBAPP_HOST,
        port=config.ZOO_WEBAPP_PORT
        )
        
        
