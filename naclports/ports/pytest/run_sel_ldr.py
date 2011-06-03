#!/usr/bin/python

# Copyright (c) 2011 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess
import struct
import sys
import naclimc
from signal import signal, SIGCHLD

def decode_path(path):
    #XXX this is not secure
    path = path[:path.index('\0')]
    if path.startswith("/"): path = "." + path
    #print path
    return os.path.join("fakefs", path)


def serve_one(socket):
    message, [response_ch] = socket.imc_recvmsg(1024)
    kind, rest = message[:4], message[4:]
    fds = tuple() # note: can't send fds back over this channel
    if kind == "stat":
        path, = struct.unpack("256s", rest)
        path = decode_path(path)
        try:
            stat = os.stat(path)
        except OSError as e:
            response = struct.pack("=III", e.errno, 0, 0)
        else:
            response = struct.pack("=III", 0, stat.st_mode, stat.st_size)
        response_ch.imc_sendmsg(response, fds)
    elif kind == "open":
        path, flags = struct.unpack("=256si", rest)
        path = decode_path(path)
        try:
            if os.path.isdir(path):
                if (flags & os.O_WRONLY) or (flags & os.O_RDWR):
                    err = errno.EISDIR
                    raise IOError(err, os.strerror(err))
                else:
                    content = '\0'.join(os.listdir(path)) + '\0'
                    #print 'dir: sending', repr(content)
            else:
                with open(path, 'r') as in_file:
                    content = in_file.read()
        except IOError as e:
            #print 'problem:', e
            response = struct.pack("=II", e.errno, 0)
            response_ch.imc_sendmsg(response, fds)
        else:
            response = struct.pack("=II", 0, len(content))
            response_ch.imc_sendmsg(response, fds)
            format = "=IB"
            block_size = 256 - struct.calcsize(format)
            for i in range(0, len(content), block_size):
                block = content[i:i+block_size]
                block = struct.pack(format, i, len(block)) + block
                response_ch.imc_sendmsg(block, tuple())                    
            fds = tuple()
    else:
        raise NotImplementedError(kind)

def serve(socket):
    while True:
        try:
            serve_one(socket)
        except Exception as e:
            print 'uncaught exception:', type(e), e

def Main(args):
    child_fd, parent_fd = naclimc.os_socketpair()
    socket = naclimc.from_os_socket(parent_fd)
    child = subprocess.Popen(
        ['nacl64-sel_ldr', '-i', '3:'+str(child_fd), '--', 'test']
    )
    def handler(signum, frame):
        print 'Caught SIGCHLD'
        raise KeyboardInterrupt
    signal(SIGCHLD, handler)
    try:
        serve(socket)
        sys.exit(child.wait())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    Main(sys.argv[1:]) 
