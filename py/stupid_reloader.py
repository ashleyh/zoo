import werkzeug.serving
from zoo.webapp import run

werkzeug.serving.run_with_reloader(run)
