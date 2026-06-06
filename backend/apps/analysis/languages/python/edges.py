import re
import sys

_IMPORT_RE = re.compile(
    r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))', re.MULTILINE
)

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


def _is_external(dep: str) -> bool:
    return dep.split('.')[0] in _PY_STDLIB


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    deps = []
    for m in _IMPORT_RE.finditer(content):
        raw = m.group(1) or m.group(2)
        if not raw:
            continue
        for part in raw.split(','):
            token = part.strip().split()[0] if part.strip().split() else ''
            if token and not token.startswith('.') and not _is_external(token):
                deps.append(token)
    return deps
