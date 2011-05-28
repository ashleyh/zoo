from zoo.webapp import my_flask
from zoo import config

#XXX the reloader doesn't work.
# i have absolutely no idea why.
my_flask.run(
    debug=True,
    use_reloader=False,
    host=config.ZOO_WEBAPP_HOST,
    port=config.ZOO_WEBAPP_PORT
    )
