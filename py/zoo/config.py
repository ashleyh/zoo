

def get_module_path(module_name):
    import inspect, os, sys
    __import__(module_name)
    module = sys.modules[module_name]
    filename = inspect.getfile(module)
    return os.path.abspath(filename)
    
def get_resource_path(module_name, resource):
    import os
    module_dir = os.path.dirname(get_module_path(module_name))
    return os.path.join(module_dir, resource)


ZOO_COMPD_HOST='127.0.0.1'
ZOO_COMPD_PORT=7777
ZOO_WEBAPP_HOST='' # make available externally
ZOO_WEBAPP_PORT=5000
ZOO_COFFEE_BIN="/usr/local/bin/coffee"
ZOO_SASS_BIN="/var/lib/gems/1.8/bin/sass"
ZOO_GUESSLANG_TRAIN_DIR=get_resource_path('zoo.guesslang', 'data')
ZOO_GUESSLANG_PICKLE_PATH=get_resource_path('zoo.guesslang', 'guesser.pickle')
