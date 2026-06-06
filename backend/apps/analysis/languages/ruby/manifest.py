import re
from pathlib import Path


def parse_manifest(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        m = re.match(r"^gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?", line)
        if m:
            deps.append({'name': m.group(1), 'version_spec': m.group(2) or '', 'source': 'Gemfile'})
    return deps
