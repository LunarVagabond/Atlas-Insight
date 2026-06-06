import json
from pathlib import Path


def parse_manifest(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return []
    deps = []
    for section in ('require', 'require-dev'):
        for name, ver in data.get(section, {}).items():
            if name == 'php' or name.startswith('ext-'):
                continue
            deps.append({
                'name': name,
                'version_spec': ver,
                'source': 'composer.json',
                'dev': section == 'require-dev',
            })
    return deps
