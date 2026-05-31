import os
import re
import sys
from pathlib import Path

PYTHON_IMPORT = re.compile(
    r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))', re.MULTILINE
)
JS_IMPORT = re.compile(
    r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))"""
)
GO_IMPORT = re.compile(r'"([^"]+)"')

MAX_FILE_SIZE = 500_000  # 500KB

SKIP_DIRS = {'.git', 'node_modules', '.venv', '__pycache__', 'vendor', 'dist'}

# Python stdlib filter
_PY_STDLIB: frozenset[str] = (
    frozenset(sys.stdlib_module_names)  # type: ignore[attr-defined]
    if hasattr(sys, 'stdlib_module_names')
    else frozenset({
        'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio',
        'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii',
        'binhex', 'bisect', 'builtins', 'bz2', 'calendar', 'cgi', 'cgitb',
        'chunk', 'cmath', 'cmd', 'code', 'codecs', 'codeop', 'collections',
        'colorsys', 'compileall', 'concurrent', 'configparser', 'contextlib',
        'contextvars', 'copy', 'copyreg', 'cProfile', 'csv', 'ctypes',
        'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
        'dis', 'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
        'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'fractions', 'ftplib',
        'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'grp',
        'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'idlelib',
        'imaplib', 'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress',
        'itertools', 'json', 'keyword', 'lib2to3', 'linecache', 'locale',
        'logging', 'lzma', 'mailbox', 'math', 'mimetypes', 'mmap',
        'modulefinder', 'multiprocessing', 'netrc', 'nis', 'nntplib',
        'numbers', 'operator', 'optparse', 'os', 'ossaudiodev', 'pathlib',
        'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform',
        'plistlib', 'poplib', 'posix', 'pprint', 'profile', 'pstats',
        'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri',
        'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
        'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve',
        'shlex', 'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr',
        'socket', 'socketserver', 'spwd', 'sqlite3', 'sre_compile',
        'sre_constants', 'sre_parse', 'ssl', 'stat', 'statistics', 'string',
        'stringprep', 'struct', 'subprocess', 'sunau', 'symtable', 'sys',
        'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile',
        'termios', 'test', 'textwrap', 'threading', 'time', 'timeit',
        'tkinter', 'token', 'tokenize', 'tomllib', 'trace', 'traceback',
        'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types', 'typing',
        'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv',
        'warnings', 'wave', 'weakref', 'webbrowser', 'wsgiref', 'xdrlib',
        'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib', 'zoneinfo',
        '_thread', '__future__',
    })
)

# Go: known external/stdlib prefixes to skip
_GO_EXTERNAL_PREFIXES = ('golang.org/', 'google.golang.org/', 'gopkg.in/')


def _read_go_module_path(base: str) -> str | None:
    gomod = os.path.join(base, 'go.mod')
    try:
        with open(gomod, encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('module '):
                    return line[7:].strip()
    except Exception:
        pass
    return None


def _is_external_python(dep: str) -> bool:
    return dep.split('.')[0] in _PY_STDLIB


def _is_external_js(dep: str) -> bool:
    return not dep.startswith('.')


def _is_external_go(dep: str, module_path: str | None) -> bool:
    # stdlib: single segment, no slash
    if '/' not in dep:
        return True
    if dep.startswith(_GO_EXTERNAL_PREFIXES):
        return True
    # if module path known, only keep imports that start with it
    if module_path and not dep.startswith(module_path):
        return True
    return False


def _rel(base: str, path: str) -> str:
    return os.path.relpath(path, base)


def parse_imports(repo_dir: str) -> list[dict]:
    edges = []
    base = repo_dir
    go_module_path = _read_go_module_path(base)
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                fsize = os.path.getsize(fpath)
            except OSError:
                continue
            if fsize > MAX_FILE_SIZE:
                continue
            ext = Path(fname).suffix.lower()
            source = _rel(base, fpath)
            try:
                content = open(fpath, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            if ext == '.py':
                for m in PYTHON_IMPORT.finditer(content):
                    dep = m.group(1) or m.group(2)
                    if dep:
                        for d in dep.split(','):
                            parts = d.strip().split()
                            if parts and not parts[0].startswith('.') and not _is_external_python(parts[0]):
                                edges.append(
                                    {'source': source, 'target': parts[0], 'lang': 'python'}
                                )
            elif ext in {'.js', '.ts', '.jsx', '.tsx', '.mjs'}:
                for m in JS_IMPORT.finditer(content):
                    dep = m.group(1) or m.group(2)
                    # "." / ".." are directory-index imports, not graph nodes
                    if dep and dep not in {'.', '..'} and not _is_external_js(dep):
                        edges.append({'source': source, 'target': dep, 'lang': 'js'})
            elif ext == '.go':
                in_block = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('import ('):
                        in_block = True
                        continue
                    if in_block:
                        if stripped == ')':
                            in_block = False
                            continue
                        m = GO_IMPORT.search(stripped)
                        if m and not _is_external_go(m.group(1), go_module_path):
                            edges.append({'source': source, 'target': m.group(1), 'lang': 'go'})
                    elif stripped.startswith('import '):
                        m = GO_IMPORT.search(stripped)
                        if m and not _is_external_go(m.group(1), go_module_path):
                            edges.append({'source': source, 'target': m.group(1), 'lang': 'go'})
    return edges
