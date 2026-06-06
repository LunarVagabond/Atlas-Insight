import os
import re

_TEST_USE = re.compile(r'^use\s+([\w\\]+)\s*;', re.MULTILINE)
_TEST_INC = re.compile(r"""(?:require|include)(?:_once)?\s+['"]([^'"]+)['"]""")


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    refs: set[str] = set()
    for m in _TEST_USE.finditer(content):
        refs.add(m.group(1).replace('\\', '/'))
    for m in _TEST_INC.finditer(content):
        imp = m.group(1)
        if imp.startswith('.'):
            resolved = os.path.normpath(os.path.join(test_dir, imp))
            refs.add(re.sub(r'\.php$', '', resolved))
    return refs
