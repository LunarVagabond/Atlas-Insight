import os
import re

_TEST_FROM = re.compile(r"""from\s+['"](\.[^'"]+)['"]""")
_TEST_REQUIRE = re.compile(r"""require\s*\(\s*['"](\.[^'"]+)['"]\s*\)""")


def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    refs: set[str] = set()
    for pat in (_TEST_FROM, _TEST_REQUIRE):
        for m in pat.finditer(content):
            imp = m.group(1)
            resolved = os.path.normpath(os.path.join(test_dir, imp))
            refs.add(re.sub(r'\.[jt]sx?$', '', resolved))
    return refs
