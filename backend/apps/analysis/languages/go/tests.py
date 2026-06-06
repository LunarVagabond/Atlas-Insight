import re

_TEST_RE = re.compile(r'"([a-zA-Z0-9_./-]{4,})"')


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    return {m.group(1) for m in _TEST_RE.finditer(content) if '/' in m.group(1)}
