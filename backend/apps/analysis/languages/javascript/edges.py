import re

_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))"""
)
_VUE_SCRIPT = re.compile(r'<script\b[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)


def _is_external(dep: str) -> bool:
    return not dep.startswith('.')


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    scan = content
    if fpath.endswith('.vue'):
        m = _VUE_SCRIPT.search(content)
        scan = m.group(1) if m else ''
    deps = []
    for m in _IMPORT_RE.finditer(scan):
        dep = m.group(1) or m.group(2)
        if dep and dep not in {'.', '..'} and not _is_external(dep):
            deps.append(dep)
    return deps
