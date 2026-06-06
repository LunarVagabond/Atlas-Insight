import os
import re

_TEST_REL = re.compile(r"""require_relative\s+['"]([^'"]+)['"]""")
_TEST_ABS = re.compile(r"""require\s+['"]([^'"]+)['"]""")


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    refs: set[str] = set()
    for m in _TEST_REL.finditer(content):
        resolved = os.path.normpath(os.path.join(test_dir, m.group(1)))
        refs.add(re.sub(r'\.rb$', '', resolved))
    for m in _TEST_ABS.finditer(content):
        refs.add(re.sub(r'\.rb$', '', m.group(1)))
    return refs
