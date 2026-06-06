import json
from pathlib import Path


def parse_manifest(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return []
    deps = []
    for section in ('dependencies', 'devDependencies'):
        for name, ver in data.get(section, {}).items():
            deps.append({
                'name': name,
                'version_spec': ver,
                'source': 'package.json',
                'dev': section == 'devDependencies',
            })
    return deps
