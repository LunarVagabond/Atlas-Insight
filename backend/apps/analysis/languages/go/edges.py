import functools
import os
import re

_IMPORT_RE = re.compile(r'"([^"]+)"')
_EXTERNAL_PREFIXES = ('golang.org/', 'google.golang.org/', 'gopkg.in/')


@functools.lru_cache(maxsize=128)
def _read_module_path(repo_dir: str) -> str | None:
    gomod = os.path.join(repo_dir, 'go.mod')
    try:
        with open(gomod, encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('module '):
                    return line[7:].strip()
    except Exception:
        pass
    return None


def _is_external(dep: str, module_path: str | None) -> bool:
    if '/' not in dep:
        return True
    if dep.startswith(_EXTERNAL_PREFIXES):
        return True
    if module_path and not dep.startswith(module_path):
        return True
    return False


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    module_path = _read_module_path(repo_dir)
    deps = []
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
            m = _IMPORT_RE.search(stripped)
            if m and not _is_external(m.group(1), module_path):
                deps.append(m.group(1))
        elif stripped.startswith('import '):
            m = _IMPORT_RE.search(stripped)
            if m and not _is_external(m.group(1), module_path):
                deps.append(m.group(1))
    return deps
