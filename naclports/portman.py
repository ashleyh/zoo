import hashlib
import os
import tarfile
import shutil
from contextlib import contextmanager
import re
import glob
import subprocess
import sys

def debug(fmt, *args, **kwargs):
    if False:
        print 'debug:', fmt.format(*args, **kwargs)

def info(fmt, *args, **kwargs):
    print 'info:', fmt.format(*args, **kwargs)

def warn(fmt, *args, **kwargs):
    print 'warning:', fmt.format(*args, **kwargs)

def get_hash(algorithm, path):
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


class FileWrapper(object):
    def __init__(self, path):
        self.path = os.path.abspath(path)

    def extract(self, where):
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
        if rel_path is None:
            rel_path = what.basename()
        out_path = self.get(rel_path)
        what.copy_to(out_path)

    def add_from(self, what):
        assert what.is_dir()
        for child in what.glob():
            self.add(child)

    def copy_to(self, where):
        debug('copy {0} -> {1}', self.path, where.path)
        if self.is_dir():
            shutil.copytree(self.path, where.path)
        else:
            shutil.copy2(self.path, where.path)

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
        return os.path.exists(self.path)

    def make_dirs(self):
        return os.makedirs(self.path)

    def is_dir(self):
        return os.path.isdir(self.path)


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
        execfile(script_path, self.globals, self.locals)
        debug('globals {0!s}', self.globals.keys())
        debug('locals {0!s}', self.locals.keys())

    
    def add_globals(self, globals):
        self.globals.update(globals)

    def download(self, name, url, hash):
        info('downloading {0} to {1}', url, name)
        out_path = os.path.join('downloads', name)
        if os.path.exists(out_path):
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
        else:
            pass

    def run_cmd(self, *args, **kwargs):
        env = self.globals.get('env', {}).copy()
        paths = self.globals.get('path', [])
        env['PATH'] = ":".join([x.path for x in paths])
        cwd = kwargs.get('cwd', None)
        
        if cwd is not None:
            if isinstance(cwd, FileWrapper):
                cwd = cwd.path
        
        if isinstance(args[0], FileWrapper):
            args = (args[0].path,) + args[1:]

        info('running {0}', args[0])
        debug('environment is {0!s}', env)

        p = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env
        )

        class RunResult(object):
            pass

        result = RunResult()
        result.stdout, result.stderr = p.communicate()
        result.exit_code = p.returncode
        result.success = (result.exit_code == 0)

        if not result.success:
            warn('command failed, output follows')
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)

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

def install_port(name):
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
    check_working_dir(new_globals['work_dir'])
    check_working_dir(new_globals['inst_dir'])
    runner.run(path)


if __name__=='__main__':
    install_port('pytest')