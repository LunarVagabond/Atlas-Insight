import collections
from pathlib import Path

from git import Repo

from .branch_detection import detect_stale_branches
from .community import (
    CHANGELOG_PATHS,
    COC_PATHS,
    CONTRIBUTING_PATHS,
    LICENSE_PATHS,
    SECURITY_POLICY_PATHS,
    detect_license_type,
    parse_roadmap_file,
    read_community_files,
)
from .file_tree import EXT_LANG, NON_SOURCE_LANGS, SKIP_DIRS, find_file, is_test_file, walk_files
from .git_stats import compute_bus_factor, get_hot_files, get_releases, get_repo_age
from .tech_stack import CI_PATHS, LINT_FILES, detect_tech_stack

_DOCS_DIRS = ['docs', 'doc', 'documentation', 'website/docs', 'site/docs', '.docs']


def analyze_structure(repo_obj: Repo, repo_dir: str, deps: dict | None = None) -> dict:
    base = Path(repo_dir)

    lang_files: dict[str, int] = collections.defaultdict(int)
    lang_lines: dict[str, int] = collections.defaultdict(int)
    total_files = 0
    test_files = 0
    file_count_limit = 25000

    all_file_paths: list[str] = []
    for path in walk_files(base, file_count_limit):
        total_files += 1
        if len(all_file_paths) < 5000:
            all_file_paths.append(str(path.relative_to(base)))
        ext = path.suffix.lower()
        lang = EXT_LANG.get(ext)
        is_test = is_test_file(path, base)
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

    has_docker = any(
        (base / f).exists()
        for f in ('Dockerfile', 'docker-compose.yml', 'docker-compose.yaml')
    )

    docs_dir = next(
        (d for d in _DOCS_DIRS if (base / d).is_dir()),
        None,
    )

    has_contributing = find_file(base, CONTRIBUTING_PATHS)
    license_file = find_file(base, LICENSE_PATHS)
    coc_file = find_file(base, COC_PATHS)
    security_policy_file = find_file(base, SECURITY_POLICY_PATHS)
    changelog_file = find_file(base, CHANGELOG_PATHS)
    roadmap_file = find_file(base, [
        'ROADMAP.md', 'ROADMAP.rst', 'ROADMAP.txt', 'ROADMAP',
        'roadmap.md', 'roadmap.rst', 'TODO.md', 'todo.md',
        'docs/ROADMAP.md', 'docs/roadmap.md',
    ])

    license_type = None
    if license_file:
        license_type = detect_license_type(base / license_file)

    community_files_content = read_community_files(
        base,
        contributing=has_contributing,
        license_f=license_file,
        coc=coc_file,
        security=security_policy_file,
        changelog=changelog_file,
    )

    release_count, releases = get_releases(repo_obj)
    repo_age_days = get_repo_age(repo_obj)
    bus_factor, top_contributors = compute_bus_factor(repo_obj)
    hot_files = get_hot_files(repo_obj)

    dep_list = deps.get('dependencies', []) if deps else []
    tech_stack = detect_tech_stack(repo_dir, dep_list)

    source_files = sum(
        v for lang, v in lang_files.items() if lang not in NON_SOURCE_LANGS
    )
    test_ratio = round(test_files / max(source_files, 1), 3)

    stale_branches, stale_branch_count = detect_stale_branches(repo_obj)

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
        'has_coc': bool(coc_file),
        'coc_file': coc_file,
        'has_security_policy': bool(security_policy_file),
        'security_policy_file': security_policy_file,
        'has_changelog': bool(changelog_file),
        'changelog_file': changelog_file,
        'roadmap_file': roadmap_file,
        'roadmap_parsed': parse_roadmap_file(base, roadmap_file),
        'community_files_content': community_files_content,
        'releases': releases,
        'release_count': release_count,
        'last_release': releases[0] if releases else None,
        'repo_age_days': repo_age_days,
        'bus_factor': bus_factor,
        'top_contributors': top_contributors,
        'hot_files': hot_files,
        'tech_stack': tech_stack,
        'all_files': all_file_paths,
        'stale_branches': stale_branches,
        'stale_branch_count': stale_branch_count,
        'docs_dir': docs_dir,
    }
