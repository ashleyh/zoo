# server.py - compd server
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

from twisted.protocols.basic import Int16StringReceiver
from twisted.internet import protocol, reactor
from zoo.common.proto import zoo_pb2
from zoo.common.proto.zoo_pb2 import CompileRequest, CompileResponse
import zoo.config

class DummyDriver(object):
    def __init__(self, driver):
        self.driver = driver

    def run(self, source):
        response = CompileResponse()
        response.compile_success = True
        response.run_success = True
        response.run_output = \
            'i would have run "{0}" on "{1}"'.format(
                self.driver, source
            )
        return response

drivers = {
    'dummy': DummyDriver('nothing'),
    'clang': DummyDriver('clang')
    }

def run_driver(request):
    driver = drivers.get(request.driver, None)
    if driver is None:
        response = CompileResponse()
        response.compile_success = False
        message = response.compile_messages.add()
        message.severity = zoo_pb2.ERROR
        message.message = 'unknown driver specified'
    else:
        response = driver.run(request.source)
    return response

class CompileServer(Int16StringReceiver):
    def stringReceived(self, string):
        request = CompileRequest()
        request.ParseFromString(string)
        response = run_driver(request)
        string = response.SerializeToString()
        self.sendString(string)

def main():
    factory = protocol.ServerFactory()
    factory.protocol = CompileServer
    reactor.listenTCP(zoo.config.ZOO_COMPD_PORT, factory)
    reactor.run()

