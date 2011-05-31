how to run it
=============

this works for me on a fresh ubuntu VM:

    # install some packaged deps

    sudo apt-get install \
        git \
        protobuf-compiler python-protobuf \
        python-flask python-twisted \
        python-pymongo mongodb \
        rubygems

    # install node

    sudo apt-get remove nodejs # the ubuntu version is too old
    git clone http://github.com/joyent/node.git
    cd node
    ./configure
    make # takes several minutes
    sudo checkinstall
    cd ..

    # install npm

    git clone http://github.com/isaacs/npm.git
    cd npm
    sudo make install # checkinstall doesn't work for some reason
    cd ..

    # install coffeescript

    sudo npm install -g coffee-script

    # install sass

    sudo gem install sass

    # install zoo

    git clone git://github.com/adgcfad/zoo.git
    cd zoo/py/zoo/common
    protoc --python_out proto zoo.proto
    cd ../..
    python -m zoo.compd &
    python -m zoo.webapp
    # or if you're fussy, cd py && python stupid_reloader.py

caveats
=======

1. **don't run this on a real machine!** even flask's debug mode allows arbitrary code execution.
2. it doesn't seem to work on py2.6.

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
      
