# testclient.py - client for testing compd
# 
# Copyright 2011 Ashley Hewson
# 
# This file is part of Compiler Zoo.
# 
# Compiler Zoo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Compiler Zoo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Compiler Zoo.  If not, see <http://www.gnu.org/licenses/>.

import socket

from zoo.common.socket_wrapper import SocketWrapper
from zoo.common.proto.zoo_pb2 import CompileRequest, CompileResponse


s = socket.socket()
s.connect(('localhost', 7777))
w = SocketWrapper(s)
request = CompileRequest()
request.driver = 'dummy'
request.source = 'gub'
w.send_pb(request)
response = w.recv_pb(CompileResponse)
print response
