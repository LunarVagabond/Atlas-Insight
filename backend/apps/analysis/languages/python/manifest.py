import re
import tomllib
from pathlib import Path


def parse_manifest(path: Path) -> list[dict]:
    if path.name == 'pyproject.toml':
        return _parse_pyproject(path)
    return _parse_requirements(path)


def _parse_requirements(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        m = re.match(r'^([A-Za-z0-9_.-]+)\s*([><=!~].*)?$', line)
        if m:
            deps.append({'name': m.group(1), 'version_spec': (m.group(2) or '').strip(), 'source': path.name})
    return deps


def _parse_pyproject(path: Path) -> list[dict]:
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps = []
    for dep in data.get('project', {}).get('dependencies', []):
        m = re.match(r'^([A-Za-z0-9_.-]+)\s*(.*)$', dep.strip())
        if m:
            deps.append({'name': m.group(1), 'version_spec': m.group(2).strip(), 'source': 'pyproject.toml'})
    for name, val in data.get('tool', {}).get('poetry', {}).get('dependencies', {}).items():
        if name == 'python':
            continue
        ver = val if isinstance(val, str) else val.get('version', '')
        deps.append({'name': name, 'version_spec': ver, 'source': 'pyproject.toml'})
    return deps
