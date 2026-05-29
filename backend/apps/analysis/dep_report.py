import json
import re
from pathlib import Path

DEPRECATED_DOCKER_BASES = [
    r'ubuntu:1[46]\.04',
    r'ubuntu:18\.04',
    r'ubuntu:20\.04',
    r'python:3\.[0-6]\b',
    r'node:1[0-4]\b',
    r'debian:(jessie|stretch|buster)',
]


def _parse_requirements_txt(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'^([A-Za-z0-9_.-]+)\s*([><=!~].*)?$', line)
        if m:
            deps.append(
                {
                    'name': m.group(1),
                    'version_spec': (m.group(2) or '').strip(),
                    'source': str(path.name),
                }
            )
    return deps


def _parse_package_json(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return []
    deps = []
    for section in ('dependencies', 'devDependencies'):
        for name, ver in data.get(section, {}).items():
            deps.append(
                {
                    'name': name,
                    'version_spec': ver,
                    'source': 'package.json',
                    'dev': section == 'devDependencies',
                }
            )
    return deps


def _scan_dockerfiles(repo_dir: str) -> list[dict]:
    issues = []
    for p in Path(repo_dir).rglob('Dockerfile*'):
        try:
            content = p.read_text(errors='ignore')
        except Exception:
            continue
        for pattern in DEPRECATED_DOCKER_BASES:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                issues.append(
                    {
                        'file': str(p.relative_to(repo_dir)),
                        'issue': f'Deprecated base image: {m.group(0)}',
                    }
                )
    return issues


def analyze_dependencies(repo_dir: str) -> dict:
    base = Path(repo_dir)
    all_deps = []

    for req in base.rglob('requirements*.txt'):
        all_deps.extend(_parse_requirements_txt(req))

    pkg = base / 'package.json'
    if pkg.exists():
        all_deps.extend(_parse_package_json(pkg))

    docker_issues = _scan_dockerfiles(repo_dir)

    missing_lockfile = []
    if (base / 'requirements.txt').exists() and not (base / 'requirements-dev.txt').exists():
        if not (base / 'Pipfile.lock').exists() and not (base / 'poetry.lock').exists():
            missing_lockfile.append(
                'Python lockfile missing (consider pip-tools, poetry, or pipenv)'
            )
    if (base / 'package.json').exists() and not (base / 'package-lock.json').exists() and not (
        base / 'yarn.lock'
    ).exists():
        missing_lockfile.append('Node lockfile missing (package-lock.json or yarn.lock)')

    return {
        'dependencies': all_deps,
        'dependency_count': len(all_deps),
        'docker_issues': docker_issues,
        'missing_lockfile_warnings': missing_lockfile,
    }
