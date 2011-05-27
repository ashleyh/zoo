# zoo.py - http server for webapp, using flask
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
from flask import render_template, request, g
import urllib
import hashlib, base64
import pymongo
import simplejson
from timenonsense import now
import random
import collections
import socket
from zoo.common.socket_wrapper import SocketWrapper
from zoo.common.proto.zoo_pb2 import CompileRequest, CompileResponse
from zoo.common.pb_to_json import pb_to_json
from zoo.webapp import my_flask

BASE64_ALTCHARS='_-'

def sha(s):
    """return the sha-256 hash of s, in a url-safe base 64 encoding"""
    hasher = hashlib.sha256()
    hasher.update(s)
    digest = hasher.digest()
    b64 = base64.b64encode(digest, BASE64_ALTCHARS)
    return b64.rstrip('=')

def canonical_json(obj):
    """return a canonical representation of obj as a json string
    i.e. if a == b then canonical_json(a) == canonical_json(b)"""
    return simplejson.dumps(obj, sort_keys=True)

def int_to_b64(n):
    bytes = ""
    while n != 0:
        byte = n % 256
        n -= byte
        n >>= 8
        bytes += chr(byte)
    b64 = base64.b64encode(bytes, BASE64_ALTCHARS)
    return b64.rstrip('=')
        
def get_timestamp(when=None):
    if when is None:
        when = now()
    when = int(1000*1000*when)
    return int_to_b64(when)

@my_flask.before_request
def cheddar():
    con = pymongo.Connection()
    g.db = con.zoo

@my_flask.route('/new/<language>')
def hello_world(language):
    return render_template(
        'edit.html',
        defaultLanguage=language,
        defaultDriver='',
        source='',
        currentID=''
        )

def run_driver(driver, source):
    s = socket.socket()
    s.connect(('localhost', 7777))
    w = SocketWrapper(s)
    request = CompileRequest()
    request.driver = driver
    request.source = source
    w.send_pb(request)
    response = w.recv_pb(CompileResponse)
    return response


@my_flask.route('/fork/<id>')
def fork(id):
    snippet = g.db.snippets.find_one(id)
    if snippet is None:
        # blank
        return render_template(
            'edit.html',
            defaultLanguage='',
            defaultDriver='',
            source='',
            currentID=''
            )
    else:
        blob_id = snippet['blob_id']
        blob = g.db.blobs.find_one(blob_id)
        return render_template(
            'edit.html',
            defaultLanguage=snippet['language'],
            defaultDriver=snippet['driver'],
            source=blob['data'],
            currentID=id
            )
 
def get_excerpt(snippet_id):
    snippet = g.db.snippets.find_one(snippet_id)
    if snippet is None:
        return None
    else:
        blob = g.db.blobs.find_one(snippet['blob_id'])
        if blob is None:
            return None
        else:
            return blob['data'][:30].encode('utf-8').encode('string_escape')

@my_flask.route('/treeoflife')
def treeoflife():
    tree = collections.defaultdict(list)
    for snippet in g.db.snippets.find():
        tree[snippet['predecessor']].append(str(snippet['_id']))
    def show(root):
        if root == '':
            result = 'root'
        else:
            result = '<a href="/fork/{0}">{1}</a> {2}'.format(root, shortenid(root), get_excerpt(root))
        result += '<ul>'
        for child in tree[root]:
            result += '<li>' + show(child) + '</li>'
        result += '</ul>'
        return result
    return show('')

def shortenid(id):
    return id[:4] + ".." + id[-4:]


@my_flask.route('/history/<id>')
def history(id):
    out = '<ul>'
    while id != '':
        out += '<li><a href="/fork/{0}">{1}</a></li>'.format(id, shortenid(id))
        snippet_doc = g.db.snippets.find_one({'_id': id})
        if snippet_doc is None:
            break
        else:
            id = snippet_doc['predecessor']
    out += '</ul>'
    return out

@my_flask.route('/save', methods=['POST'])
def save():
    blob = {
        'data': request.form['source']
    }

    blob['_id'] = sha(blob['data'])

    snippet = {
        'blob_id': blob['_id'],
        'language': request.form['language'],
        'driver': request.form['driver'],
        'predecessor': request.form['predecessor'],
        'revision': now()
    }

    snippet['_id'] = sha(canonical_json(snippet))

    # silently ignore duplicate keys (assuming that
    # same hash => same object :/)

    g.db.blobs.insert(blob, safe=False)
    g.db.snippets.insert(snippet, safe=False)

    return simplejson.dumps(snippet)

@my_flask.route('/compile', methods=['POST'])
def compile():
    print 'compile', request.form['id']

    snippet = g.db.snippets.find_one(
        {'_id': request.form['id']}
    )

    if snippet is None:
        return simplejson.dumps(
            {'error':'error'}
        )

    blob = g.db.blobs.find_one(
        {'_id': snippet['blob_id']}
    )


    #TODO log compile in db
#    success = False
#
#    for retries in range(5):
#        compile['_id'] = get_timestamp()
#        g.db.compiles.insert(compile, safe=True)
#        #XXX check error
#        success = True
#        break
    
    response = run_driver(snippet['driver'], blob['data'])
    response_json = pb_to_json(response)

    return simplejson.dumps(response_json)

@my_flask.route("/")
def start():
    return render_template("start.html")
