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
import os
import hashlib
import base64
import collections
import random       # to generate compile ids
import socket
import subprocess
import re
import zlib         # for adler32

from flask import render_template, request, g, redirect, url_for
import pymongo
import simplejson

from timenonsense import now
from zoo.common.socket_wrapper import SocketWrapper
from zoo.common.proto.zoo_pb2 import CompileRequest, CompileResponse
from zoo.common.pb_to_json import pb_to_json
from zoo.webapp import my_flask
from zoo import config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE64_ALTCHARS='_-'

def sha(s):
    """
    return the sha-256 hash of `s`, in a url-safe base-64 encoding
    """
    hasher = hashlib.sha256()
    hasher.update(s)
    digest = hasher.digest()
    b64 = base64.b64encode(digest, BASE64_ALTCHARS)
    return b64.rstrip('=')

def canonical_json(obj):
    """
    return a canonical representation of obj as a json string
    i.e. if `a == b` then `canonical_json(a) == canonical_json(b)`
    """
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
    try:
        con = pymongo.Connection()
        g.db = con.zoo
    except:
        g.db = None

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

def run_coffee(in_path, out_path):
    print 'running coffee' 
    # for some reason coffee wants an output dir
    out_dir = os.path.dirname(out_path)
    subprocess.call([config.ZOO_COFFEE_BIN, '-o', out_dir, '-c', in_path])

def run_scss(in_path, out_path):
    print 'running scss'
    subprocess.call([config.ZOO_SASS_BIN, in_path, out_path])

def get_mtime(path):
    if os.path.exists(path):
        return os.stat(path).st_mtime
    else:
        return None

#TODO: use If-Modified-Since and ETag
def dynamic_cache(in_name, out_name, transformer):
    in_path = os.path.join(SCRIPT_DIR, 'templates', in_name)
    out_path = os.path.join(SCRIPT_DIR, 'static', out_name)
    
    in_time = get_mtime(in_path)
    out_time = get_mtime(out_path)

    # make sure that the output dir exists
    # (it's probably initially empty after git clone)
    out_dir = os.path.dirname(out_path)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if (out_time is None) or (out_time < in_time):
        transformer(in_path, out_path)
        
    return redirect(url_for('static', filename=out_name))
        

@my_flask.route('/dynamic/scss/<name>.css')
def dynamic_css(name):
    return dynamic_cache(
        in_name = 'scss/{0}.scss'.format(name),
        out_name = 'scss/{0}.css'.format(name),
        transformer = run_scss
    )

@my_flask.route('/dynamic/coffee/<name>.js')
def dynamic_coffee(name):
    return dynamic_cache(
        in_name = 'coffee/{0}.coffee'.format(name),
        out_name = 'coffee/{0}.js'.format(name),
        transformer = run_coffee
    )



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

def make_bookmarklet(url):
    source = '''
        (function() {
            var e = document.createElement('script'),
                t = Math.random(), // try to override cache
                w = window;
            e.setAttribute('src', '{{url}}?' + t);
            w.zooBookmarkletVersion = {{version}};
            w.zooBookmarkletScript = e;
            w.zooRoot = '{{root}}';
            document.body.appendChild(e);
        })();
    '''

    # this is not intended to be secure or anything,
    # just stop mistakes...
    if ("'" in url) or ('"' in url) or ('\\' in url):
        raise ValueError("don't put \' \" \\ in the url...")
    
    # pseudo-minify
    source = re.sub('//.*', '', source)
    source = re.sub('\s+', ' ', source)
    source = source.strip()

    # .format() is a pain with a curly-bracket language like JS
    source = source.replace('{{url}}', url)
    source = source.replace('{{root}}', request.url_root)

    # try to detect when the user needs to update their bookmark
    version = hex(zlib.adler32(source) & 0xffffffff)
    source = source.replace('{{version}}', version)

    return 'javascript:' + source
                    

@my_flask.route("/")
def start():
    url = url_for('static', filename='js/bookmarklet.js', _external=True)
    return render_template(
        "start.html",
        bookmarklet=make_bookmarklet(url)
    )
