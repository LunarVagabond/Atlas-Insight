import re

_IMPORT_RE = re.compile(r"""^\s*import\s+['"]([^'"]+)['"]""", re.MULTILINE)


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    deps = []
    for m in _IMPORT_RE.finditer(content):
        dep = m.group(1)
        # keep package: imports only; dart: is stdlib, relative paths are intra-package
        if dep and dep.startswith('package:') and not dep.startswith('dart:'):
            pkg = dep[len('package:'):].split('/')[0]
            deps.append(pkg)
    return deps
