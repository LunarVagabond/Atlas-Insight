import re
from pathlib import Path

from .gitignore_patterns import GITIGNORE_SHOULD_NOT_TRACK, path_matches_gitignore_pattern
from .security_scan import SAFE_PATTERNS

_MAX_RESULTS = 200

_CATEGORY_PRIORITY = {
    'os_junk': 0,
    'editor_swap': 1,
    'temp_file': 2,
    'log_file': 3,
    'build_artifact': 4,
    'gitignore_gap': 5,
    'ai_scratch': 6,
}

_CATEGORY_WEIGHT = {
    'os_junk': 8,
    'editor_swap': 6,
    'temp_file': 7,
    'log_file': 5,
    'build_artifact': 6,
    'gitignore_gap': 5,
    'ai_scratch': 3,
}

_CATEGORY_LABELS = {
    'os_junk': 'OS junk',
    'editor_swap': 'editor swap/backup',
    'temp_file': 'temp file',
    'log_file': 'log file',
    'build_artifact': 'build artifact',
    'gitignore_gap': 'gitignore gap',
    'ai_scratch': 'AI/scratch file',
}

_RULES: list[tuple[str, str, str, str]] = [
    (r'(^|/)\.ds_store$', 'os_junk', 'high', '.DS_Store committed'),
    (r'(^|/)thumbs\.db$', 'os_junk', 'high', 'Thumbs.db committed'),
    (r'(^|/)desktop\.ini$', 'os_junk', 'high', 'desktop.ini committed'),
    (r'(^|/)\._', 'os_junk', 'high', 'AppleDouble resource fork file'),
    (r'\.swp$', 'editor_swap', 'high', 'Vim swap file'),
    (r'\.swo$', 'editor_swap', 'high', 'Vim swap file'),
    (r'~$', 'editor_swap', 'high', 'Editor backup file'),
    (r'\.bak$', 'editor_swap', 'high', 'Backup file'),
    (r'\.orig$', 'editor_swap', 'high', 'Merge conflict backup'),
    (r'\.rej$', 'editor_swap', 'high', 'Patch reject file'),
    (
        r'(^|/)(tmp|temp|scratch|untitled)(\.|_|$|/)',
        'temp_file', 'high', 'Temporary/scratch filename',
    ),
    (r'copy of ', 'temp_file', 'high', 'Duplicate/copy filename'),
    (r'\.log$', 'log_file', 'high', 'Log file tracked in git'),
    (r'\.pyc$', 'build_artifact', 'high', 'Python bytecode file'),
    (r'\.pyo$', 'build_artifact', 'high', 'Python bytecode file'),
    (r'\.o$', 'build_artifact', 'high', 'Object file'),
    (r'\.class$', 'build_artifact', 'high', 'Java class file'),
    (r'\.exe$', 'build_artifact', 'high', 'Executable binary'),
    (r'\.dll$', 'build_artifact', 'high', 'Windows library binary'),
    (r'\.so$', 'build_artifact', 'high', 'Shared object binary'),
    (
        r'(^|/)(output|response|debug)\.(txt|md)$',
        'ai_scratch', 'medium', 'Likely AI/debug output file',
    ),
    (r'(^|/)draft', 'ai_scratch', 'medium', 'Draft file'),
    (r'(^|/)notes\.txt$', 'ai_scratch', 'medium', 'Scratch notes file'),
]

_GITIGNORE_GAP_SKIP = re.compile(
    r'\.(example|sample|template|test|stub|fake)$', re.IGNORECASE
)


def _match_rules(path: str) -> tuple[str, str, str] | None:
    path_lower = path.lower()
    if SAFE_PATTERNS.search(path_lower):
        return None
    for pattern, category, confidence, reason in _RULES:
        if re.search(pattern, path_lower, re.IGNORECASE):
            return category, confidence, reason
    return None


def _match_gitignore_gap(path: str) -> str | None:
    if _GITIGNORE_GAP_SKIP.search(path.lower()):
        return None
    for pattern in GITIGNORE_SHOULD_NOT_TRACK:
        if path_matches_gitignore_pattern(path, pattern):
            if pattern in ('.env', '*.pem', '*.key', 'id_rsa'):
                continue
            return f'Tracked file matches should-ignore pattern: {pattern}'
    return None


def _file_size(base: Path, rel_path: str) -> int | None:
    try:
        return (base / rel_path).stat().st_size
    except OSError:
        return None


def _compute_score(files: list[dict]) -> int:
    if not files:
        return 0
    raw = sum(_CATEGORY_WEIGHT.get(f['category'], 4) for f in files)
    high_count = sum(1 for f in files if f['confidence'] == 'high')
    raw += high_count * 2
    return min(100, raw)


def scan_junk_files(repo_obj, repo_dir: str, path_prefix: str | None = None) -> dict:
    base = Path(repo_dir)
    findings: list[dict] = []
    seen_paths: set[str] = set()

    try:
        tracked = repo_obj.git.ls_files().splitlines()
    except Exception:
        return {
            'files': [],
            'count': 0,
            'by_category': {},
            'total_bytes': 0,
            'score': 0,
            'note': 'Could not list tracked files',
        }

    if path_prefix:
        tracked = [f for f in tracked if f.startswith(path_prefix)]

    capped = False
    for rel_path in tracked:
        if rel_path in seen_paths:
            continue

        match = _match_rules(rel_path)
        if match:
            category, confidence, reason = match
            size_bytes = _file_size(base, rel_path)
            findings.append({
                'path': rel_path,
                'category': category,
                'reason': reason,
                'confidence': confidence,
                'size_bytes': size_bytes,
            })
            seen_paths.add(rel_path)
            if len(findings) >= _MAX_RESULTS:
                capped = True
                break
            continue

        gap_reason = _match_gitignore_gap(rel_path)
        if gap_reason:
            size_bytes = _file_size(base, rel_path)
            findings.append({
                'path': rel_path,
                'category': 'gitignore_gap',
                'reason': gap_reason,
                'confidence': 'high',
                'size_bytes': size_bytes,
            })
            seen_paths.add(rel_path)
            if len(findings) >= _MAX_RESULTS:
                capped = True
                break

    findings.sort(
        key=lambda f: (
            _CATEGORY_PRIORITY.get(f['category'], 99),
            f['path'].lower(),
        )
    )

    by_category: dict[str, int] = {}
    total_bytes = 0
    for f in findings:
        by_category[f['category']] = by_category.get(f['category'], 0) + 1
        if f.get('size_bytes'):
            total_bytes += f['size_bytes']

    note = None
    if capped:
        note = f'Results capped at {_MAX_RESULTS} files'

    return {
        'files': findings,
        'count': len(findings),
        'by_category': by_category,
        'total_bytes': total_bytes,
        'score': _compute_score(findings),
        'note': note,
    }


def format_category_summary(by_category: dict[str, int]) -> str:
    parts = []
    for cat, count in sorted(by_category.items(), key=lambda x: _CATEGORY_PRIORITY.get(x[0], 99)):
        label = _CATEGORY_LABELS.get(cat, cat)
        parts.append(f'{count} {label}')
    return ', '.join(parts)
