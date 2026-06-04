from pathlib import Path

from .todo_scan import MAX_FILE_BYTES, SCAN_EXTS, SKIP_DIRS

_THRESHOLD = 500
_COMMENT_PREFIXES = ('#', '//', '*', '/*', '*/', '<!--', '-->')
_TEST_INDICATORS = {'test_', '_test', 'spec_', '_spec', '.test.', '.spec.', 'tests/', '__tests__/'}


def _is_test_file(path_str: str) -> bool:
    lower = path_str.lower()
    return any(ind in lower for ind in _TEST_INDICATORS)


def _has_adjacent_test(rel_path: str, all_source_files: set[str]) -> bool:
    p = Path(rel_path)
    stem = p.stem
    parent = str(p.parent)
    for candidate in (
        f'{parent}/test_{stem}{p.suffix}',
        f'{parent}/{stem}_test{p.suffix}',
        f'{parent}/{stem}.test{p.suffix}',
        f'{parent}/{stem}.spec{p.suffix}',
        f'{parent}/tests/{stem}{p.suffix}',
        f'tests/{stem}{p.suffix}',
        f'test/{stem}{p.suffix}',
    ):
        if candidate in all_source_files:
            return True
    return False


def _count_loc(path: Path) -> int:
    loc = 0
    try:
        with open(path, errors='ignore') as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                if any(stripped.startswith(p) for p in _COMMENT_PREFIXES):
                    continue
                loc += 1
    except OSError:
        pass
    return loc


def analyze_complexity(repo_dir: str, structure: dict) -> dict:
    root = Path(repo_dir)
    all_files: set[str] = set(structure.get('all_files', []))

    file_locs: list[tuple[str, int]] = []  # (rel_path, loc)

    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix not in SCAN_EXTS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue

        rel = str(path.relative_to(root))
        if _is_test_file(rel):
            continue

        loc = _count_loc(path)
        if loc > 0:
            file_locs.append((rel, loc))

    if not file_locs:
        return {
            'hotspots': [],
            'avg_file_loc': 0.0,
            'files_over_threshold': 0,
            'threshold': _THRESHOLD,
            'distribution': {'0-100': 0, '100-300': 0, '300-500': 0, '500+': 0},
            'score': 0,
        }

    dist = {'0-100': 0, '100-300': 0, '300-500': 0, '500+': 0}
    hotspots = []
    total_loc = 0

    for rel, loc in file_locs:
        total_loc += loc
        if loc <= 100:
            dist['0-100'] += 1
        elif loc <= 300:
            dist['100-300'] += 1
        elif loc <= _THRESHOLD:
            dist['300-500'] += 1
        else:
            dist['500+'] += 1
            has_test = _has_adjacent_test(rel, all_files)
            hotspots.append({'file': rel, 'loc': loc, 'has_adjacent_test': has_test})

    hotspots.sort(key=lambda h: h['loc'], reverse=True)
    hotspots = hotspots[:50]

    avg_loc = total_loc / len(file_locs)
    files_over = dist['500+']
    total_files = len(file_locs)

    untested_over_threshold = sum(1 for h in hotspots if not h['has_adjacent_test'])
    over_ratio = files_over / max(total_files, 1)
    untested_ratio = untested_over_threshold / max(files_over, 1) if files_over else 0
    score = min(100, int((over_ratio * 50) + (untested_ratio * 50)))

    return {
        'hotspots': hotspots,
        'avg_file_loc': round(avg_loc, 1),
        'files_over_threshold': files_over,
        'threshold': _THRESHOLD,
        'distribution': dist,
        'score': score,
    }
