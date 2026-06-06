import re
from pathlib import Path

from .languages import all_plugins

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

    # Build manifest_name -> parse_fn from registry (first plugin wins per filename)
    manifest_map: dict[str, object] = {}
    for p in all_plugins():
        if p.parse_manifest is not None:
            for fname in p.manifest_filenames:
                manifest_map.setdefault(fname, p.parse_manifest)

    req_parser = manifest_map.get('requirements.txt')

    seen: set[str] = set()
    for path in base.rglob('*'):
        if not path.is_file() or _should_skip(path, base):
            continue
        key = str(path)
        if key in seen:
            continue
        fname = path.name
        # Handle requirements*.txt variants (requirements-dev.txt, requirements-test.txt, etc.)
        if req_parser and fname.startswith('requirements') and fname.endswith('.txt'):
            seen.add(key)
            try:
                all_deps.extend(req_parser(path))  # type: ignore[operator]
            except Exception:
                pass
            continue
        parser = manifest_map.get(fname)
        if parser is None:
            continue
        seen.add(key)
        try:
            all_deps.extend(parser(path))  # type: ignore[operator]
        except Exception:
            pass

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
