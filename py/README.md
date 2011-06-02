the servery things are written in python. it lives in this funny separate directory because `zoo` is a proper python package; that is, you can do things like `import zoo` from this directory.

directory layout
================
* `zoo` -- package `zoo`
  * `zoo/compd` -- package `zoo.compd`, the compile daemon
  * `zoo/webapp` -- package `zoo.webapp`, the webapp server
  * `zoo/common` -- package `zoo.common`, mostly protobuf-related stuff used by both servers
* `stupid_reloader.py` -- run this if you want to run the webapp server with an automatic reloader. you can run it without the reloader using `python -m zoo.webapp`; for some reason the reloader doesn't like that invocation.
   
