# portman.py - automate the process of building nacl ports
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

import hashlib
import os
import tarfile
import shutil
from contextlib import contextmanager
import re
import glob
import subprocess
import sys
import urllib

def debug(fmt, *args, **kwargs):
    if False:
        print 'debug:', fmt.format(*args, **kwargs)

def info(fmt, *args, **kwargs):
    print 'info:', fmt.format(*args, **kwargs)

def warn(fmt, *args, **kwargs):
    print 'warning:', fmt.format(*args, **kwargs)

def get_hash(algorithm, path):
    """get a `.hexdigest` of `algorithm` applied to the file at `path"""
    debug('hashing {0} with {1}', path, algorithm)
    hasher = hashlib.new(algorithm)
    size = hasher.block_size
    with open(path, 'rb') as in_file:
        data = in_file.read(size)
        while len(data) > 0:
            hasher.update(data)
            data = in_file.read(size)
    return hasher.hexdigest()

def check_hash(hash, path):
    algorithm, want_hash = hash.split(':', 2)
    got_hash = get_hash(algorithm, path)

    if got_hash == want_hash:
        info('hash {0} checks out', hash)
        return True
    else:
        warn('wanted hash {0} got {1}', hash, got_hash)
        return False


class LineWrapper(object):
    def __init__(self, mangler, index):
        self.mangler = mangler
        self.index = index

    def comment_out(self, prefix):
        return self.mangler._comment_out(self, prefix)

    def insert_line_before(self, line):
        return self.mangler._insert_line_before(self, line)

    def insert_line_after(self, line):
        return self.mangler._insert_line_after(self, line)

class LineMangler(object):
    def __init__(self, lines):
        self.lines = lines
        self._available = True

    @contextmanager
    def find_line(self, regexp):
        assert self._available, 'another line mangling operation is in progress'
        regexp = re.compile(regexp)
        for i, line in enumerate(self.lines):
            if regexp.match(line):
                self._available = False
                try:
                    yield LineWrapper(self, i)
                    return
                finally:
                    self._available = True
        warn('didn\'t find matching line')
    
    def _comment_out(self, w, prefix):
        self.lines[w.index] = prefix + self.lines[w.index]
        debug('changed line {0}', w.index)

    def _insert_line_before(self, w, line):
        self.lines.insert(w.index, line + '\n')
        debug('inserted line {0}', w.index)
        w.index += 1

    def _insert_line_after(self, w, line):
        self.lines.insert(w.index+1, line + '\n')



class FileWrapper(object):
    """
    convenience wrapper around a path. `self.path` may or may
    not actually refer to an extant file or directory.
    """

    def __init__(self, path):
        self.path = os.path.abspath(path)

    @property
    def parent(self):
        return FileWrapper(os.path.dirname(self.path))

    def extract(self, where):
        """if `self.path` is some kind of archive file, extract it."""    
        if tarfile.is_tarfile(self.path):
            with tarfile.open(self.path) as tar:
                info('extracting {0}', self.path)
                # check for no nasty names
                for tarinfo in tar:
                    path = os.path.normpath(tarinfo.name)
                    if path.startswith('/') or path.startswith('..'):
                        raise Exception('nasty path...')
                debug('extracting {0} to {1}', self.path, where.path)
                tar.extractall(where.path)
        else:
            raise Exception('unsupported archive format')
 
    def add(self, what, rel_path=None):
        """
        if `self.path`/`rel_path` is a directory, copy `what`
        under it
        """
        if rel_path is None:
            rel_path = what.basename
        out_path = self.get(rel_path)
        what.copy_to(out_path)

    def add_from(self, what):
        """
        if `what` is a directory, add all the files from it to myself
        """
        assert what.is_dir()
        for child in what.glob():
            self.add(child)

    def copy_to(self, where):
        """
        move myself to `where`
        """
        info('copy {0} -> {1}', self.path, where.path)
        if not where.parent.exists():
            where.parent.make_dirs()
        if self.is_dir():
            shutil.copytree(self.path, where.path)
        else:
            shutil.copy2(self.path, where.path)

    @property
    def basename(self):
        return os.path.basename(self.path)

    @contextmanager
    def line_mangler(self):
        info('line-mangling {0}', self.path)
        with open(self.path, 'r') as in_file:
            lines = in_file.readlines()
        yield LineMangler(lines)
        debug('writing {0}', self.path)
        with open(self.path, 'w') as out_file:
            out_file.writelines(lines)

    def glob(self, spec='*'):
        assert self.is_dir()
        for result in glob.glob(os.path.join(self.path, spec)):
            yield FileWrapper(result)
    
    def get(self, *args, **kwargs):
        """get a relative path or glob"""
        if 'glob' in kwargs:
            glob_spec = os.path.join(self.path, kwargs['glob'])
            paths = list(self.glob(glob_spec))
            if len(paths) == 1:
                return paths[0]
            else:
                raise Exception()
        else:
            return FileWrapper(os.path.join(self.path, args[0]))
    
    def exists(self):
        """does `self.path` refer to a real file/dir?"""
        return os.path.exists(self.path)

    def make_dirs(self):
        """if `self.path` doesn't exist, create it as a directory"""
        return os.makedirs(self.path)

    def is_dir(self):
        return os.path.isdir(self.path)

    def symlink_to(self, target):
        os.symlink(target.path, self.path)

@contextmanager
def urlopen(url):
    f = urllib.urlopen(url)
    yield f
    f.close()

class ScriptRunner(object):
    def __init__(self):
        self.globals = {
            'download': self.download,
            'require_tool': self.require_tool,
            'require_port': self.require_port,
            'get_inst_dir': get_inst_dir,
            'get_tool_dir': get_tool_dir,
            'info': info,
            'run': self.run_cmd,
            'provide': self.provide,
        }
        self.locals = {}

    def run(self, script_path):
        """run a script in this context"""
        execfile(script_path, self.globals, self.locals)
        debug('globals {0!s}', self.globals.keys())
        debug('locals {0!s}', self.locals.keys())

    
    def add_globals(self, globals):
        self.globals.update(globals)

    def download(self, name, url, hash):
        info('downloading {0} to {1}', url, name)
        out_path = os.path.join('downloads', name)
        if not os.path.exists(out_path):
            with urlopen(url) as in_file:
                with open(out_path, 'w') as out_file:
                    out_file.write(in_file.read())

        if check_hash(hash, out_path):
            # cool!
            return FileWrapper(out_path)
        else:
            warn(
                'hash mismatch: expected {0}, got {1}',
                hash, got_hash
            )
            # boo!
            pass

    def run_cmd(self, *args, **kwargs):
        """run an external executable"""
        env = self.globals.get('env', {}).copy()
        paths = self.globals.get('path', [])
        env['PATH'] = ":".join([x.path for x in paths])
        cwd = kwargs.get('cwd', None)
        quiet = kwargs.get('quiet', False)

        if cwd is not None:
            if not isinstance(cwd, FileWrapper):
                cwd = FileWrapper(cwd)
            if not cwd.exists():
                cwd.make_dirs()
            cwd = cwd.path
            
        
        if isinstance(args[0], FileWrapper):
            args = (args[0].path,) + args[1:]

        info('running {0}', args[0])
        debug('environment is {0!s}', env)

        if quiet:
            fd_type=subprocess.PIPE
        else:
            fd_type=None

        p = subprocess.Popen(
            args,
            stdin=fd_type,
            stdout=fd_type,
            stderr=fd_type,
            cwd=cwd,
            env=env
        )

        class RunResult(object):
            pass

        result = RunResult()
        if quiet:
            result.stdout, result.stderr = p.communicate()
        else:
            p.wait()
        result.exit_code = p.returncode
        result.success = (result.exit_code == 0)

        if not result.success:
            if quiet:
                warn('command failed, output follows')
                sys.stdout.write(result.stdout)
                sys.stderr.write(result.stderr)
            else:
                warn('command failed')

        return result

    def provide_tool(self, name):
        execfile(
            os.path.join('tools', name, 'provide'),
            self.globals
        )

    def require_tool(self, name):
        info('getting tool {0}', name)
        install_tool(name)
        self.provide_tool(name)
    
    def require_port(self, name):
        info('getting port {0}', name)
        install_port(name)

    def provide(self, name, what):
        self.globals[name] = what


def install_tool(name):
    inst_dir = get_inst_dir(name)
    if inst_dir.exists():
        info('assuming {0} already installed', name)
    else:
        run_build_script(name, os.path.join('tools', name, 'init'))

def install_port(name, toplevel=False):
    inst_dir = get_inst_dir(name)
    if inst_dir.exists():
        info('assuming {0} already installed', name)
    else:
        run_build_script(name, os.path.join('ports', name, 'go'))

def check_working_dir(path):
    if not path.exists():
        path.make_dirs()

def get_port_dir(name):
    return FileWrapper(os.path.join('ports', name))

def get_inst_dir(name):
    return FileWrapper(os.path.join('out', name))

def get_work_dir(name):
    return FileWrapper(os.path.join('build', name))

def get_tool_dir(name):
    return FileWrapper(os.path.join('tools', name))

def run_build_script(name, path):
    runner = ScriptRunner()
    new_globals = {
        'port_dir': get_port_dir(name),
        'work_dir': get_work_dir(name),
        'inst_dir': get_inst_dir(name),
        'tool_dir': get_tool_dir(name),
        'path': [FileWrapper(x) for x in os.getenv('PATH', '').split(':')],
        'env': {},
    }
    runner.add_globals(new_globals)
    #check_working_dir(new_globals['work_dir'])
    #check_working_dir(new_globals['inst_dir'])
    runner.run(path)


if __name__=='__main__':
    install_port(sys.argv[1], toplevel=True)
