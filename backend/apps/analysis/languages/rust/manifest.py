import tomllib
from pathlib import Path


def parse_manifest(path: Path) -> list[dict]:
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps = []
    for section in ('dependencies', 'dev-dependencies', 'build-dependencies'):
        for name, val in data.get(section, {}).items():
            ver = val if isinstance(val, str) else val.get('version', '')
            deps.append({
                'name': name,
                'version_spec': ver,
                'source': 'Cargo.toml',
                'dev': section != 'dependencies',
            })
    return deps
