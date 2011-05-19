#!/bin/bash
export GOROOT=$HOME/ext_code/go
export GOBIN=$GOROOT/bin
export PATH=$GOBIN:$PATH
6g server.go
6l -o server server.6

