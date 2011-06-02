what
====

an attempt to automate building things under nacl

why
===

* nacl is a good sandbox
* building things under nacl is painful

how
===

at the moment, do something like

    python portman.py py27

to build python-2.7 under nacl. if it fails the first time you're probably going to need to do 
    
    rm build/* out/*

before trying again.

directory layout
================

* `ports/{name}` -- stuff required to build `{name}`
  * `ports/{name}/go` -- build script in our funny pythonish DSL
  * `ports/{name}/*` -- other stuff needed for this build
* `tools/{name}` -- stuff required to fetch `{tool}`
  * `tools/{name}/init` -- this is run if the tool doesn't seem to be installed yet
  * `tools/{name}/provide` -- this is run when the tool is used to set up the environment variables and things.
* `downloads` (created on first run) -- where tarballs and things are cached
* `build` (created on first run) -- used as a working directory
* `out` (created on first run) -- where things get installed to after building

tools?
======

you know, things that are required to build the ports but are probably not there on a vanilla system, like the nacl sdk.

funny DSL?
==========

it's python with some handy extra globals like download(). look at the existing scripts for examples

what on earth is a line_mangler?
--------------------------------

it's an attempt to provide a vaguely systematic means of applying the inevitable tweaks and things that are needed to get things to build. i suppose a diff could be used instead...

