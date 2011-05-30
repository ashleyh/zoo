# cg.py -- get a callgraph of a C project to help with porting
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

import glob
from collections import namedtuple

try:
    from clang import cindex
except OSError as e:
    print 'you probably need to set (DY)LD_LIBRARY_PATH'
    raise e

def severity_name(code):
    for name in ('Ignored', 'Note', 'Warning', 'Error', 'Fatal'):
        if getattr(cindex.Diagnostic, name) == code:
            return name
    raise KeyError(code)

def show_cursor(cursor, depth = 0):
#    defn = cursor.get_definition()
    defn = cindex.Cursor_ref(cursor)
    defn = defn.get_usr() if defn else None
    print ' '*depth, cursor.kind.name, cursor.get_usr(), defn
    for child in cursor.get_children():
        show_cursor(child, depth + 1)

def walk_cursor(cursor, visitor, *args):
    for child in cursor.get_children():
        ret = visitor(child, *args)
        if ret == 0: break
        elif ret == 1: continue
        elif ret == 2: walk_cursor(child, visitor, *args)
        else: raise ValueError()


Function = namedtuple('Function', 'name usr')

class DirectedGraph(object):
    def __init__(self):
        self.nodes = set()
        self.edges = set()
    def add_edge(self, a, b):
        self.nodes.add(a)
        self.nodes.add(b)
        self.edges.add((a,b))
    def left_closure(self, closure):
        while True:
            old_size = len(closure)
            closure |= self.left_nbd(closure)
            new_size = len(closure)
            print 'old_size', old_size, 'new_size', new_size
            if old_size == new_size:
                return closure
    def left_nbd(self, nodes):
        nbd = set()
        #XXX couldn't be much slower
        for left, right in self.edges:
            if right in nodes:
                nbd.add(left)
        return nbd
    def restrict(self, nodes):
        new_graph = DirectedGraph()
        for left, right in self.edges:
            if left in nodes and right in nodes:
                new_graph.add_edge(left, right)
        return new_graph
            

def find_function(call_graph, name):
    for function in call_graph.nodes:
        if function.name == name: return function

def examine_tu(tu, call_graph):
    def add_call(caller, callee):
        call_graph.add_edge(
            Function(name=caller.spelling, usr=caller.get_usr()),
            Function(name=callee.spelling, usr=callee.get_usr())
        )
            
    def call_visitor(cursor, function_cursor):
        if cursor.kind == cindex.CursorKind.CALL_EXPR:
            callee = cindex.Cursor_ref(cursor)
            if callee is None:
                print 'unknown call in', function_cursor.spelling, cursor.extent   #XXX
            else:
                add_call(function_cursor, callee)
            return 1
        else:
            return 2
    def function_visitor(cursor):
        if cursor.kind == cindex.CursorKind.FUNCTION_DECL:
            walk_cursor(cursor, call_visitor, cursor)
            return 1
        else:
            return 2
    walk_cursor(tu.cursor, function_visitor)

index = cindex.Index.create()

cflags = [
    '-I/home/ashley/ext_code/Python-2.7.1/Include',
    # for pyconfig.h:
    '-I/home/ashley/ext_code/Python-2.7.1/Python-2.7.1-build/',
    # for asm/errno.h:
    '-I/usr/include/x86_64-linux-gnu/',
    ]

parse_options = 1 # include preprocessor info

files_not_loaded = set()
translation_units = []

for path in glob.glob('/home/ashley/ext_code/Python-2.7.1/Python/*.c'):
    print path
    tu = index.parse(path, cflags, options = parse_options)
    print 'Diagnostics:'
    fatal = False
    for diag in tu.diagnostics:
        severity = severity_name(diag.severity)
        print severity, diag.spelling    
        if severity == 'Fatal':
            fatal = True
    if fatal:
        files_not_loaded.add(path)
    else:
        translation_units.append(tu)

print 'The following files were not loaded:'

for path in files_not_loaded:
    print path

call_graph = DirectedGraph()
for tu in translation_units:
    examine_tu(tu, call_graph)
    print len(call_graph.nodes), 'functions', len(call_graph.edges), 'calls'

function = find_function(call_graph, 'fopen')
closure = call_graph.left_closure(set([function]))
call_graph = call_graph.restrict(closure)

with open('graph.dot', 'w') as out_file:
    print >>out_file, 'digraph callgraph {'
    for function in call_graph.nodes:
        print >>out_file, '"{0}" [label="{1}"];'.format(function.usr, function.name)
    for caller, callee in call_graph.edges:
        print >>out_file, '"{0}" -> "{1}";'.format(caller.usr, callee.usr)
    print >>out_file, "}"


