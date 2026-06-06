import re

_TEST_RE = re.compile(r'^\s*(?:from|import)\s+([\w.]+)', re.MULTILINE)


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    return {m.group(1).replace('.', '/') for m in _TEST_RE.finditer(content) if m.group(1)}
