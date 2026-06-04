import json
import re
import tomllib
from pathlib import Path

DEPRECATED_DOCKER_BASES = [
    r'ubuntu:1[46]\.04',
    r'ubuntu:18\.04',
    r'ubuntu:20\.04',
    r'python:3\.[0-6]\b',
    r'node:1[0-4]\b',
    r'debian:(jessie|stretch|buster)',
]

SKIP_DIRS = {'node_modules', '.git', '.venv', 'venv', 'env', '__pycache__', 'dist', 'build'}


def _should_skip(path: Path, base: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.relative_to(base).parts)


def _parse_requirements_txt(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        m = re.match(r'^([A-Za-z0-9_.-]+)\s*([><=!~].*)?$', line)
        if m:
            deps.append({
                'name': m.group(1),
                'version_spec': (m.group(2) or '').strip(),
                'source': path.name,
            })
    return deps


def _parse_package_json(path: Path) -> list[dict]:
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


def _parse_go_mod(path: Path) -> list[dict]:
    deps = []
    in_require = False
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('require ('):
            in_require = True
            continue
        if in_require and line == ')':
            in_require = False
            continue
        if in_require or line.startswith('require '):
            line = line.removeprefix('require ').strip()
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith('//'):
                deps.append({'name': parts[0], 'version_spec': parts[1], 'source': 'go.mod'})
    return deps


def _parse_cargo_toml(path: Path) -> list[dict]:
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


def _parse_pyproject_toml(path: Path) -> list[dict]:
    try:
        data = tomllib.loads(path.read_text())
    except Exception:
        return []
    deps = []
    project_deps = data.get('project', {}).get('dependencies', [])
    for dep in project_deps:
        m = re.match(r'^([A-Za-z0-9_.-]+)\s*(.*)$', dep.strip())
        if m:
            deps.append({'name': m.group(1), 'version_spec': m.group(2).strip(), 'source': 'pyproject.toml'})
    # poetry style
    for name, val in data.get('tool', {}).get('poetry', {}).get('dependencies', {}).items():
        if name == 'python':
            continue
        ver = val if isinstance(val, str) else val.get('version', '')
        deps.append({'name': name, 'version_spec': ver, 'source': 'pyproject.toml'})
    return deps


def _parse_gemfile(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        m = re.match(r"^gem\s+['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?", line)
        if m:
            deps.append({'name': m.group(1), 'version_spec': m.group(2) or '', 'source': 'Gemfile'})
    return deps


def _parse_composer_json(path: Path) -> list[dict]:
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


def _parse_build_gradle(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        m = re.search(r"""(?:implementation|api|compile|testImplementation|runtimeOnly)\s+['"]([^'"]+)['"]""", line)
        if m:
            coords = m.group(1)
            parts = coords.split(':')
            if len(parts) >= 2:
                name = f'{parts[0]}/{parts[1]}'
                deps.append({'name': name, 'version_spec': parts[2] if len(parts) > 2 else '', 'source': path.name})
    return deps


def _parse_pom_xml(path: Path) -> list[dict]:
    deps = []
    try:
        content = path.read_text(errors='ignore')
        for m in re.finditer(r'<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>(?:\s*<version>([^<]+)</version>)?', content):
            name = f'{m.group(1).strip()}/{m.group(2).strip()}'
            deps.append({'name': name, 'version_spec': (m.group(3) or '').strip(), 'source': 'pom.xml'})
    except Exception:
        pass
    return deps


def _scan_dockerfiles(repo_dir: str) -> list[dict]:
    issues = []
    for p in Path(repo_dir).rglob('Dockerfile*'):
        if _should_skip(p, Path(repo_dir)):
            continue
        try:
            content = p.read_text(errors='ignore')
        except Exception:
            continue
        for pattern in DEPRECATED_DOCKER_BASES:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                issues.append({
                    'file': str(p.relative_to(repo_dir)),
                    'issue': f'Deprecated base image: {m.group(0)}',
                })
    return issues


def analyze_dependencies(repo_dir: str) -> dict:
    base = Path(repo_dir)
    all_deps: list[dict] = []
    seen_sources: set[str] = set()

    for req in base.rglob('requirements*.txt'):
        if not _should_skip(req, base):
            all_deps.extend(_parse_requirements_txt(req))

    for pkg in base.rglob('package.json'):
        if not _should_skip(pkg, base) and pkg not in seen_sources:
            seen_sources.add(str(pkg))
            all_deps.extend(_parse_package_json(pkg))

    go_mod = base / 'go.mod'
    if go_mod.exists():
        all_deps.extend(_parse_go_mod(go_mod))

    for cargo in [base / 'Cargo.toml', base / 'src-tauri' / 'Cargo.toml']:
        if cargo.exists():
            all_deps.extend(_parse_cargo_toml(cargo))

    pyproject = base / 'pyproject.toml'
    if pyproject.exists():
        all_deps.extend(_parse_pyproject_toml(pyproject))

    gemfile = base / 'Gemfile'
    if gemfile.exists():
        all_deps.extend(_parse_gemfile(gemfile))

    composer = base / 'composer.json'
    if composer.exists():
        all_deps.extend(_parse_composer_json(composer))

    pom = base / 'pom.xml'
    if pom.exists():
        all_deps.extend(_parse_pom_xml(pom))

    for gradle in base.rglob('build.gradle'):
        if not _should_skip(gradle, base):
            all_deps.extend(_parse_build_gradle(gradle))
            break  # root only

    docker_issues = _scan_dockerfiles(repo_dir)

    missing_lockfile = []
    if (base / 'requirements.txt').exists():
        if not any((base / f).exists() for f in ('Pipfile.lock', 'poetry.lock', 'uv.lock')):
            missing_lockfile.append('Python lockfile missing (consider pip-tools, poetry, or uv)')
    if (base / 'package.json').exists():
        if not any((base / f).exists() for f in ('package-lock.json', 'yarn.lock', 'pnpm-lock.yaml')):
            missing_lockfile.append('Node lockfile missing (package-lock.json, yarn.lock, or pnpm-lock.yaml)')

    unpinned_count = sum(
        1 for d in all_deps
        if not d.get('version_spec', '').strip() or d.get('version_spec', '').strip() == '*'
    )
    exact_pinned_count = sum(
        1 for d in all_deps
        if re.match(r'^[=~^v]?\d+\.\d+', d.get('version_spec', '').strip())
    )

    return {
        'dependencies': all_deps,
        'dependency_count': len(all_deps),
        'docker_issues': docker_issues,
        'missing_lockfile_warnings': missing_lockfile,
        'unpinned_count': unpinned_count,
        'exact_pinned_count': exact_pinned_count,
    }
