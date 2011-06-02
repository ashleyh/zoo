what's this
===========

it tries to make callgraphs of C code, using clang.

how do i use it
===============

build clang from sources. run cg.py.
unfortunately the paths are hand-coded at the moment... it should produce a graphviz file at graph.dot.

'i might need to set (DY)LD_LIBRARY_PATH?'
==========================================

it needs to be able to find libclang.so (linux) / libclang.dyld (OSX). if you've installed clang locally you'll need to tell the dynamic linker where to find that. consult your operating system docs.

directory layout
================

* cg.py -- the thing that makes the callgraph
* clang -- python bindings to libclang, copied straight out of the clang distribution

external code
=============

some code borrowed from the clang distro. see their site for licensing details.
