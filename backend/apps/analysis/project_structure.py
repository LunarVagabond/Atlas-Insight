import collections
import re
from datetime import datetime, timezone
from pathlib import Path

from git import Repo

EXT_LANG: dict[str, str] = {
    '.py': 'Python', '.pyw': 'Python',
    '.js': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript', '.jsx': 'JavaScript',
    '.go': 'Go',
    '.rs': 'Rust',
    '.java': 'Java',
    '.kt': 'Kotlin', '.kts': 'Kotlin',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.cs': 'C#',
    '.cpp': 'C++', '.cxx': 'C++', '.cc': 'C++',
    '.c': 'C',
    '.h': 'C/C++ Header', '.hpp': 'C++ Header',
    '.swift': 'Swift',
    '.scala': 'Scala',
    '.vue': 'Vue',
    '.svelte': 'Svelte',
    '.dart': 'Dart',
    '.r': 'R',
    '.sh': 'Shell', '.bash': 'Shell', '.zsh': 'Shell',
    '.html': 'HTML', '.htm': 'HTML',
    '.css': 'CSS', '.scss': 'SCSS', '.sass': 'SASS', '.less': 'Less',
    '.sql': 'SQL',
    '.tf': 'Terraform', '.hcl': 'Terraform',
    '.proto': 'Protobuf',
    '.lua': 'Lua',
    '.ex': 'Elixir', '.exs': 'Elixir',
    '.clj': 'Clojure',
    '.hs': 'Haskell',
    '.elm': 'Elm',
    '.gleam': 'Gleam',
    '.zig': 'Zig',
}

SKIP_DIRS = {
    '.git', 'node_modules', '.venv', 'venv', 'env', '__pycache__',
    '.mypy_cache', '.pytest_cache', 'dist', 'build', '.next', '.nuxt',
    'target', 'vendor', '.cargo', '.gradle', 'coverage', '.nyc_output',
    '.tox', 'htmlcov', '.eggs', '*.egg-info',
}

NON_SOURCE_LANGS = {'YAML', 'JSON', 'HTML', 'CSS', 'SCSS', 'SASS', 'Less', 'Shell', 'SQL'}

CI_PATHS: dict[str, str] = {
    '.github/workflows': 'GitHub Actions',
    '.travis.yml': 'Travis CI',
    '.circleci': 'CircleCI',
    'Jenkinsfile': 'Jenkins',
    '.gitlab-ci.yml': 'GitLab CI',
    'bitbucket-pipelines.yml': 'Bitbucket Pipelines',
    'azure-pipelines.yml': 'Azure Pipelines',
    '.drone.yml': 'Drone CI',
    'circle.yml': 'CircleCI',
    '.buildkite': 'Buildkite',
    'Makefile': None,  # presence alone doesn't mean CI
}

LINT_FILES = {
    '.eslintrc', '.eslintrc.js', '.eslintrc.json', '.eslintrc.yml', '.eslintrc.yaml',
    'ruff.toml', '.flake8', '.pylintrc', 'golangci.yml', '.golangci.yml',
    '.rubocop.yml', 'checkstyle.xml', '.scalafmt.conf', '.stylelintrc',
    'biome.json', '.prettier.config.js',
}

CONTRIBUTING_PATHS = [
    'CONTRIBUTING.md', 'CONTRIBUTING.rst', 'CONTRIBUTING.txt', 'CONTRIBUTING',
    '.github/CONTRIBUTING.md', 'docs/CONTRIBUTING.md', 'docs/contributing.md',
]

LICENSE_PATHS = [
    'LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENSE.rst',
    'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-Apache',
    'COPYING', 'COPYING.md', 'COPYING.txt',
    'license', 'license.md', 'license.txt',
]

COC_PATHS = [
    'CODE_OF_CONDUCT.md', '.github/CODE_OF_CONDUCT.md', 'docs/CODE_OF_CONDUCT.md',
]

SECURITY_POLICY_PATHS = [
    'SECURITY.md', '.github/SECURITY.md', 'docs/SECURITY.md',
]

CHANGELOG_PATHS = [
    'CHANGELOG.md', 'CHANGELOG.rst', 'CHANGELOG.txt', 'CHANGELOG',
    'CHANGES.md', 'CHANGES.rst', 'CHANGES', 'HISTORY.md', 'HISTORY.rst',
    'RELEASES.md', 'RELEASE_NOTES.md',
]


def analyze_structure(repo_obj: Repo, repo_dir: str) -> dict:
    base = Path(repo_dir)

    # Language breakdown and file stats
    lang_files: dict[str, int] = collections.defaultdict(int)
    lang_lines: dict[str, int] = collections.defaultdict(int)
    total_files = 0
    test_files = 0
    file_count_limit = 25000

    for path in _walk_files(base, file_count_limit):
        total_files += 1
        ext = path.suffix.lower()
        lang = EXT_LANG.get(ext)
        is_test = _is_test_file(path, base)
        if is_test:
            test_files += 1
        if lang:
            lang_files[lang] += 1
            if path.stat().st_size < 512_000:
                try:
                    lines = path.read_text(errors='ignore').count('\n')
                    lang_lines[lang] += lines
                except Exception:
                    pass

    total_lines = sum(lang_lines.values())
    languages = sorted(
        [
            {
                'name': lang,
                'files': lang_files[lang],
                'lines': lang_lines.get(lang, 0),
                'pct': round(lang_lines.get(lang, 0) / max(total_lines, 1) * 100, 1),
            }
            for lang in lang_files
        ],
        key=lambda x: -x['lines'],
    )[:15]

    # CI systems
    ci_systems = [
        name
        for path_str, name in CI_PATHS.items()
        if name and (base / path_str).exists()
    ]
    gh_wf_dir = base / '.github' / 'workflows'
    gh_workflow_count = (
        len(list(gh_wf_dir.glob('*.yml')) + list(gh_wf_dir.glob('*.yaml')))
        if gh_wf_dir.is_dir()
        else 0
    )

    # Lint config
    has_lint = any((base / f).exists() for f in LINT_FILES)
    if not has_lint:
        ppt = base / 'pyproject.toml'
        if ppt.exists():
            try:
                c = ppt.read_text(errors='ignore')
                has_lint = any(
                    tag in c for tag in ('[tool.ruff]', '[tool.flake8]', '[tool.pylint]')
                )
            except Exception:
                pass

    # Docker
    has_docker = any(
        (base / f).exists()
        for f in ('Dockerfile', 'docker-compose.yml', 'docker-compose.yaml')
    )

    # Community health files
    has_contributing = _find_file(base, CONTRIBUTING_PATHS)
    license_file = _find_file(base, LICENSE_PATHS)
    has_coc = _find_file(base, COC_PATHS)
    has_security_policy = _find_file(base, SECURITY_POLICY_PATHS)
    has_changelog = _find_file(base, CHANGELOG_PATHS)

    # License detection from file content
    license_type = None
    if license_file:
        license_type = _detect_license_type(base / license_file)

    # Releases / tags
    releases = _get_releases(repo_obj)

    # Repo age from first commit
    repo_age_days = _get_repo_age(repo_obj)

    # Bus factor
    bus_factor, top_contributors = _compute_bus_factor(repo_obj)

    source_files = sum(
        v for lang, v in lang_files.items() if lang not in NON_SOURCE_LANGS
    )
    test_ratio = round(test_files / max(source_files, 1), 3)

    return {
        'total_files': total_files,
        'total_lines': total_lines,
        'languages': languages,
        'test_files': test_files,
        'test_ratio': test_ratio,
        'has_ci': bool(ci_systems),
        'ci_systems': ci_systems,
        'gh_workflow_count': gh_workflow_count,
        'has_docker': has_docker,
        'has_lint_config': has_lint,
        'has_contributing': bool(has_contributing),
        'contributing_file': has_contributing,
        'license_file': license_file,
        'license_type': license_type,
        'has_coc': bool(has_coc),
        'has_security_policy': bool(has_security_policy),
        'has_changelog': bool(has_changelog),
        'releases': releases,
        'release_count': len(releases),
        'last_release': releases[0] if releases else None,
        'repo_age_days': repo_age_days,
        'bus_factor': bus_factor,
        'top_contributors': top_contributors,
    }


def _walk_files(base: Path, max_files: int = 25000):
    count = 0
    for path in base.rglob('*'):
        if count >= max_files:
            break
        if path.is_file():
            rel = path.relative_to(base)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            count += 1
            yield path


def _is_test_file(path: Path, base: Path) -> bool:
    rel = path.relative_to(base)
    name = path.stem.lower()
    parts_lower = [p.lower() for p in rel.parts]
    if any(p in ('test', 'tests', '__tests__', 'spec', 'specs', 'e2e') for p in parts_lower):
        return True
    return (
        name.startswith('test_')
        or name.endswith('_test')
        or name.endswith('.test')
        or name.endswith('.spec')
        or name.endswith('_spec')
        or name.startswith('spec_')
    )


def _find_file(base: Path, candidates: list[str]) -> str | None:
    for name in candidates:
        if (base / name).exists():
            return name
    return None


def _detect_license_type(path: Path) -> str | None:
    try:
        content = path.read_text(errors='ignore').lower()[:2000]
    except Exception:
        return None
    if 'mit license' in content or 'permission is hereby granted' in content:
        return 'MIT'
    if 'apache license' in content and '2.0' in content:
        return 'Apache-2.0'
    if 'gnu general public license' in content:
        if 'version 3' in content:
            return 'GPL-3.0'
        if 'version 2' in content:
            return 'GPL-2.0'
        return 'GPL'
    if 'gnu lesser general public license' in content:
        return 'LGPL'
    if 'mozilla public license' in content:
        return 'MPL-2.0'
    if 'bsd 2-clause' in content or 'redistribution and use in source' in content:
        if 'neither the name' not in content:
            return 'BSD-2-Clause'
        return 'BSD-3-Clause'
    if 'the unlicense' in content or 'this is free and unencumbered software' in content:
        return 'Unlicense'
    if 'isc license' in content:
        return 'ISC'
    return 'Other'


def _get_releases(repo_obj: Repo) -> list[dict]:
    try:
        tags = sorted(repo_obj.tags, key=lambda t: t.commit.committed_date, reverse=True)
        return [
            {
                'name': t.name,
                'date': datetime.fromtimestamp(
                    t.commit.committed_date, tz=timezone.utc
                ).isoformat(),
            }
            for t in tags[:20]
        ]
    except Exception:
        return []


def _get_repo_age(repo_obj: Repo) -> int | None:
    try:
        count_str = repo_obj.git.rev_list('HEAD', '--count', '--first-parent')
        total = int(count_str.strip())
        skip = max(0, total - 1)
        ts_str = repo_obj.git.log(f'--skip={skip}', '-1', '--format=%ct', 'HEAD', '--first-parent')
        if ts_str.strip():
            first_date = datetime.fromtimestamp(int(ts_str.strip()), tz=timezone.utc)
            return (datetime.now(timezone.utc) - first_date).days
    except Exception:
        pass
    return None


def _compute_bus_factor(repo_obj: Repo) -> tuple[int, list[dict]]:
    author_files: dict[str, set] = collections.defaultdict(set)
    try:
        output = repo_obj.git.log('--format=%ae', '--name-only', '-300', 'HEAD')
        current_author: str | None = None
        for line in output.splitlines():
            line = line.strip()
            if not line:
                current_author = None
            elif current_author is None:
                current_author = line
            else:
                author_files[current_author].add(line)
    except Exception:
        return 1, []

    if not author_files:
        return 1, []

    all_files: set[str] = set()
    for files in author_files.values():
        all_files.update(files)

    sorted_authors = sorted(author_files.items(), key=lambda x: -len(x[1]))
    top_contributors = [
        {'author': a, 'files_touched': len(f)} for a, f in sorted_authors[:10]
    ]

    target = len(all_files) * 0.8
    covered: set[str] = set()
    bus_factor = 0
    for author, files in sorted_authors:
        covered.update(files)
        bus_factor += 1
        if len(covered) >= target:
            break

    return max(1, bus_factor), top_contributors


def _parse_license_spdx_from_content(content: str) -> str | None:
    """Detect SPDX identifier from license file content."""
    spdx_map = {
        'MIT': r'mit license|permission is hereby granted',
        'Apache-2.0': r'apache license.*2\.0',
        'GPL-3.0': r'gnu general public license.*version 3',
        'GPL-2.0': r'gnu general public license.*version 2',
        'BSD-3-Clause': r'neither the name.*nor the names',
        'BSD-2-Clause': r'redistribution and use in source.*neither',
        'ISC': r'isc license',
        'MPL-2.0': r'mozilla public license.*2\.0',
        'LGPL-2.1': r'gnu lesser general public license.*2\.1',
        'LGPL-3.0': r'gnu lesser general public license.*3',
        'Unlicense': r'this is free and unencumbered',
        'CC0-1.0': r'creative commons.*cc0',
    }
    lower = content.lower()
    for spdx, pattern in spdx_map.items():
        if re.search(pattern, lower):
            return spdx
    return None
