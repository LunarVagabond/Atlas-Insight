import re

# Only local includes (double-quoted) are intra-project; angle-bracket includes are system.
_TEST_RE = re.compile(r'^#include\s+"([^"]+)"', re.MULTILINE)


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    return {re.sub(r'\.[ch](pp)?$', '', m.group(1)) for m in _TEST_RE.finditer(content) if m.group(1)}
