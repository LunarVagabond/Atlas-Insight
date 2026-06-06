import re

_IMPORT_RE = re.compile(r'^\s*import\s+([\w.]+)', re.MULTILINE)

_STDLIB_PREFIXES = ('scala.', 'java.', 'javax.', 'sun.', 'com.sun.')


def _is_external(dep: str) -> bool:
    return any(dep.startswith(p) for p in _STDLIB_PREFIXES)


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))]
