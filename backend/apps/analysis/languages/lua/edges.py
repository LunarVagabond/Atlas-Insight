import re

_IMPORT_RE = re.compile(
    r"""^\s*(?:local\s+\w+\s*=\s*)?require\s*[(\s]['"]([^'"]+)['"]""", re.MULTILINE
)


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content) if m.group(1)]
