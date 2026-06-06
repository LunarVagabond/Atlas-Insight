from pathlib import Path

from .todo_scan import SCAN_EXTS, SKIP_DIRS

_MIN_SOURCE_FILES_PER_DIR = 3
_TEST_FILE_PATTERNS = (
    'test_', '_test.', '.test.', '.spec.', '_spec.',
    'tests/', '__tests__/', 'test/', 'spec/',
    '_spec.lua', 'test_',
)
def _build_framework_signatures() -> dict[str, set[str]]:
    from .languages import all_plugins
    sigs: dict[str, set[str]] = {}
    for p in all_plugins():
        sigs.update(p.test_frameworks)
    return sigs

_FRAMEWORK_SIGNATURES = _build_framework_signatures()


def _is_test_file(name: str) -> bool:
    name_lower = name.lower()
    return any(p in name_lower for p in _TEST_FILE_PATTERNS)


def _detect_framework(repo_dir: str, tech_stack: list | None) -> str | None:
    root = Path(repo_dir)
    stack_names = set()
    for item in tech_stack or []:
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            name = str(item.get('name', ''))
        else:
            name = ''
        if name:
            stack_names.add(name.lower())

    for framework, signatures in _FRAMEWORK_SIGNATURES.items():
        for sig in signatures:
            if sig.startswith('#'):
                continue
            if '*' in sig:
                prefix, suffix = sig.split('*')
                for p in root.rglob('*'):
                    if p.name.startswith(prefix) and p.name.endswith(suffix):
                        return framework
            else:
                if (root / sig).exists():
                    return framework

    for name in stack_names:
        if 'pytest' in name:
            return 'pytest'
        if 'jest' in name or 'vitest' in name:
            return 'jest' if 'vitest' not in name else 'vitest'
        if 'rspec' in name:
            return 'rspec'

    return None


def analyze_test_coverage(repo_dir: str, structure: dict) -> dict:
    root = Path(repo_dir)
    tech_stack = structure.get('tech_stack', [])

    dir_source: dict[str, int] = {}
    dir_has_test: dict[str, bool] = {}
    source_file_count = 0
    test_file_count = 0

    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix not in SCAN_EXTS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue

        rel = str(path.relative_to(root))
        parent = str(Path(rel).parent)

        if _is_test_file(path.name) or _is_test_file(rel):
            test_file_count += 1
            # Mark parent dir and ancestors as having tests
            parts = Path(rel).parts
            for i in range(1, len(parts)):
                dir_key = str(Path(*parts[:i]))
                dir_has_test[dir_key] = True
        else:
            source_file_count += 1
            dir_source[parent] = dir_source.get(parent, 0) + 1
            dir_has_test.setdefault(parent, False)

    untested_dirs = []
    well_tested = 0
    for d, count in dir_source.items():
        if count < _MIN_SOURCE_FILES_PER_DIR:
            continue
        if dir_has_test.get(d, False):
            well_tested += 1
        else:
            untested_dirs.append({'path': d, 'source_files': count})

    untested_dirs.sort(key=lambda x: x['source_files'], reverse=True)
    untested_dirs = untested_dirs[:30]

    test_ratio = structure.get('test_ratio') or (
        test_file_count / max(source_file_count + test_file_count, 1)
    )

    if test_ratio < 0.05:
        score = 80
    elif test_ratio < 0.15:
        score = 55
    elif test_ratio < 0.25:
        score = 30
    elif test_ratio < 0.40:
        score = 10
    else:
        score = 0

    untested_penalty = min(20, len(untested_dirs) * 3)
    score = min(100, score + untested_penalty)

    framework = _detect_framework(repo_dir, tech_stack)

    return {
        'test_ratio': round(test_ratio, 4),
        'test_file_count': test_file_count,
        'source_file_count': source_file_count,
        'framework_detected': framework,
        'untested_dirs': untested_dirs,
        'well_tested_dirs': well_tested,
        'score': score,
    }
