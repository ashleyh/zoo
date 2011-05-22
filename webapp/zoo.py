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
# along with Compiler Zoo.  If not, see <http:#www.gnu.org/licenses/>.

from flask import Flask, render_template, request, g
import urllib
import hashlib, base64
import pymongo
import simplejson
from timenonsense import now
import random
import collections

BASE64_ALTCHARS='_-'

app = Flask(__name__)

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

@app.before_request
def cheddar():
    con = pymongo.Connection()
    g.db = con.zoo

@app.route('/new/<language>')
def hello_world(language):
    return render_template(
        'edit.html',
        defaultLanguage=language,
        defaultDriver='',
        source='',
        currentID=''
        )



@app.route('/fork/<id>')
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
            defaultDriver='',
            source=blob['data'],
            currentID=id
            )
 
@app.route('/treeoflife')
def treeoflife():
    tree = collections.defaultdict(list)
    for snippet in g.db.snippets.find():
        tree[snippet['predecessor']].append(str(snippet['_id']))
    def show(root):
        result = '<a href="/fork/{0}">{0}</a>'.format(root)
        result += '<ul>'
        for child in tree[root]:
            result += '<li>' + show(child) + '</li>'
        result += '</ul>'
        return result
    return show('')


@app.route('/history/<id>')
def history(id):
    out = '<ul>'
    while id != '':
        out += '<li><a href="/fork/{0}">{0}</a></li>'.format(id)
        snippet_doc = g.db.snippets.find_one({'_id': id})
        if snippet_doc is None:
            break
        else:
            id = snippet_doc['predecessor']
    out += '</ul>'
    return out

@app.route('/save', methods=['POST'])
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

@app.route('/compile', methods=['POST'])
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
    
    form_data = urllib.urlencode(
        {
            'source': blob['data'],
            'driver': snippet['driver']
        }
    )

    compiled = simplejson.load(
        urllib.urlopen('http://localhost:7777/', form_data)
    )

    response = {
        'result': compiled['Result']
    }

    return simplejson.dumps(response)

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0")
