import re

_IMPORT_RE = re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"]+)['"]""", re.MULTILINE)

_STDLIB = frozenset({
    'abbrev', 'base64', 'benchmark', 'bigdecimal', 'cgi', 'cmath', 'complex',
    'csv', 'date', 'dbm', 'debug', 'delegate', 'digest', 'dl', 'drb', 'e2mmap',
    'English', 'erb', 'etc', 'expect', 'fcntl', 'fiber', 'fileutils', 'find',
    'forwardable', 'gdbm', 'getoptlong', 'io', 'ipaddr', 'irb', 'json', 'logger',
    'matrix', 'minitest', 'monitor', 'mutex_m', 'net', 'nkf', 'observer', 'open-uri',
    'open3', 'openssl', 'optparse', 'ostruct', 'pathname', 'pp', 'prettyprint',
    'prime', 'profiler', 'pstore', 'psych', 'pty', 'rake', 'rational', 'rbconfig',
    'readline', 'resolv', 'rexml', 'rinda', 'ripper', 'rss', 'rubygems', 'scanf',
    'sdbm', 'set', 'shell', 'shellwords', 'singleton', 'socket', 'stringio',
    'strscan', 'sync', 'syslog', 'tempfile', 'test', 'thread', 'thwait', 'time',
    'timeout', 'tmpdir', 'tracer', 'tsort', 'un', 'unicode_normalize', 'uri',
    'weakref', 'webrick', 'win32ole', 'yaml', 'zlib',
})


def _is_external(dep: str) -> bool:
    return dep.split('/')[0] in _STDLIB


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))]
