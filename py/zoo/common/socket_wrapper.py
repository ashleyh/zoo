# socket_wrapper.py - add some useful methods to socket objects
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

import struct

class SocketWrapper(object):
    STRUCT_FORMAT = '!H'
    def __init__(self, socket):
        self.socket = socket
    def send_string(self, string):
        header = struct.pack(SocketWrapper.STRUCT_FORMAT, len(string))
        self.socket.send(header)
        self.socket.send(string)
    def send_pb(self, pb):
        string = pb.SerializeToString()
        self.send_string(string)
    def recv_string(self):
        header_size = struct.calcsize(SocketWrapper.STRUCT_FORMAT)
        header = self.socket.recv(header_size)
        (string_len,) = struct.unpack(SocketWrapper.STRUCT_FORMAT, header)
        string = self.socket.recv(string_len)
        return string
    def recv_pb(self, klass):
        string = self.recv_string()
        instance = klass()
        instance.ParseFromString(string)
        return instance

