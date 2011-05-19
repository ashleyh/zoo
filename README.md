you will need
=============

* mongo on localhost, default port
* apparmor set up like the example compd/aa-example
* some compilers in compd/compilers
* some binaries in compd/dash/bin (copy them from your own distro or something)
* port 5000 open if you want other people to be able to use it
* python-flask (the web framework thingy)
* a go distro in `$HOME/ext_code/go`

then do this
============

* `cd compd/server; ./build.sh && ./server`
  this will run the compile daemon thingy on :7777
* `cd webapp; python zoo.py`
  this will run the web app thingy on :5000
* go to http://localhost:5000

gotchas
=======

* the drivers will probably fail to run if apparmor isn't active. this is by design. the idea is to stop you accidentally running it without a sandbox.

directory layout
================

the directory layout should look something like this:

* compd - compile daemon thingy
 * compilers - the compiler binaries, currently omitted here because they're enormous
  * llvm-2.9
  * mono-2.10.2
  * tcc-0.9.25
 * dash
  * bin
   * aa-check: used to check the sandbox
   * cat, dash, echo, env, mktemp, rm
 * drivers - these are dash scripts which read code from stdin, compile and run it and put the output on stdout
 * server - the server thingy, written in go
* webapp - the web app thingy
 * static - static content
  * js/ace - from ace.ajax.org
 * templates - jinja templates
 * tools - currently contains a thing for bundling together code skeletons into a json thing

license
=======

some parts of this distribution are externally maintained and covered
by their own licenses, for example ace and jquery. the original code is covered
by the following license.

Compiler Zoo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Compiler Zoo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Compiler Zoo.  If not, see <http://www.gnu.org/licenses/>.
      
