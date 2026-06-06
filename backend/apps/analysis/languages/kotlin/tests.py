import re

from .edges import _is_external

_TEST_RE = re.compile(r'^import\s+([\w.]+)', re.MULTILINE)


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    return {m.group(1).replace('.', '/') for m in _TEST_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))}
