"""PR Impact Preview — complexity estimation and reviewer suggestions for a GitHub PR."""
import logging

logger = logging.getLogger(__name__)

def _build_dep_filenames() -> frozenset[str]:
    from .languages import all_manifest_filenames
    # Include lock files and extras not tracked as manifest_filenames
    extras = frozenset({
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'requirements.in', 'Pipfile', 'Pipfile.lock',
        'setup.cfg', 'setup.py', 'go.sum',
        'Cargo.lock', 'Gemfile.lock', 'composer.lock',
        'build.gradle',
    })
    return all_manifest_filenames() | extras

_DEP_FILENAMES = _build_dep_filenames()


def _file_basename(path: str) -> str:
    return path.rsplit('/', 1)[-1] if '/' in path else path


def affected_subsystems(changed_files: list[str], result: dict) -> list[dict]:
    """Map PR changed files to known subsystems from run.result['ownership']."""
    subsystems: list[dict] = (result.get('ownership') or {}).get('subsystems') or []
    if not subsystems or not changed_files:
        return []

    changed_set = set(changed_files)
    out = []
    for sub in subsystems:
        sub_dir = sub['id'].replace('_', '/')
        prefix = sub_dir + '/'
        matched = [f for f in changed_set if f == sub_dir or f.startswith(prefix)]
        if matched:
            out.append({
                'id': sub['id'],
                'name': sub['name'],
                'subsystem_type': sub.get('subsystem_type', 'other'),
                'activity_score': sub.get('activity_score', 0.0),
                'has_god_modules': bool(sub.get('god_modules')),
                'matched_files': len(matched),
            })

    return sorted(out, key=lambda s: -s['matched_files'])


def suggest_reviewers(
    changed_files: list[str],
    hit_subsystems: list[dict],
    result: dict,
    author_pr_files: dict | None = None,
    author_names: dict | None = None,
) -> list[dict]:
    """Suggest reviewers based on who has committed to the actual PR files.

    Primary: use per-file commit history (author_pr_files) — ranks by how many
    files in *this PR* each author has touched. Falls back to subsystem-match
    against top_contributors when file history is unavailable.
    """
    # Primary: file-history-based (most accurate)
    if author_pr_files:
        ranked = sorted(author_pr_files.items(), key=lambda kv: -len(kv[1]))
        names = author_names or {}
        return [
            {
                'author': names.get(email, email),
                'email': email,
                'pr_files_touched': len(files),
                'match_reason': 'file_history',
            }
            for email, files in ranked[:5]
        ]

    # Fallback: subsystem-activity-weighted top contributors
    top_contributors: list[dict] = (result.get('ownership') or {}).get('top_contributors') or []
    if not top_contributors:
        top_contributors = (result.get('structure') or {}).get('top_contributors') or []

    if not top_contributors:
        return []

    hit_types = {s['subsystem_type'] for s in hit_subsystems}
    hit_ids = {s['id'] for s in hit_subsystems}
    subsystems: list[dict] = (result.get('ownership') or {}).get('subsystems') or []

    sub_by_id = {s['id']: s for s in subsystems}
    sub_by_type: dict[str, list[dict]] = {}
    for s in subsystems:
        sub_by_type.setdefault(s.get('subsystem_type', 'other'), []).append(s)

    reviewer_scores: dict[str, float] = {}
    for c in top_contributors:
        author = c.get('author', '') or c.get('email', '')
        if not author:
            continue
        score = 0.0
        for sid in hit_ids:
            sub = sub_by_id.get(sid)
            if sub:
                score += sub.get('activity_score', 0.0) * c.get('files_touched', 1)
        if score == 0.0 and hit_types:
            for stype in hit_types:
                for sub in sub_by_type.get(stype, []):
                    score += sub.get('activity_score', 0.0) * c.get('files_touched', 1) * 0.5
        reviewer_scores[author] = reviewer_scores.get(author, 0.0) + score

    if not any(v > 0 for v in reviewer_scores.values()):
        return [
            {
                'author': c.get('author', c.get('email', '')),
                'email': c.get('email', ''),
                'pr_files_touched': 0,
                'match_reason': 'top_contributor',
            }
            for c in top_contributors[:5]
            if c.get('author') or c.get('email')
        ]

    sorted_authors = sorted(reviewer_scores, key=lambda a: -reviewer_scores[a])
    author_map = {c.get('author', c.get('email', '')): c for c in top_contributors}

    return [
        {
            'author': a,
            'email': author_map.get(a, {}).get('email', ''),
            'pr_files_touched': 0,
            'match_reason': 'subsystem_match',
        }
        for a in sorted_authors[:5]
        if a
    ]


def compute_complexity(
    pr_additions: int,
    pr_deletions: int,
    changed_files: list[str],
    hit_subsystems: list[dict],
    result: dict,
) -> dict:
    """Return complexity score (0–100), label, and human-readable notes."""
    notes: list[str] = []

    file_count = len(changed_files)
    subsystem_count = len(hit_subsystems)
    line_delta = pr_additions + pr_deletions

    touches_deps = any(_file_basename(f) in _DEP_FILENAMES for f in changed_files)
    touches_god = any(s['has_god_modules'] for s in hit_subsystems)

    score = 0

    # Files changed (0–30)
    if file_count >= 30:
        score += 30
        notes.append(f'{file_count} files changed — large surface area')
    elif file_count >= 15:
        score += 20
        notes.append(f'{file_count} files changed')
    elif file_count >= 5:
        score += 10
    else:
        score += 3

    # Line delta (0–25)
    if line_delta >= 1000:
        score += 25
        notes.append(f'{pr_additions:+} / -{pr_deletions} lines — very large diff')
    elif line_delta >= 400:
        score += 15
        notes.append(f'{pr_additions:+} / -{pr_deletions} lines')
    elif line_delta >= 150:
        score += 8
    else:
        score += 2

    # Subsystems crossed (0–25)
    if subsystem_count >= 4:
        score += 25
        notes.append(f'Touches {subsystem_count} subsystems — cross-cutting change')
    elif subsystem_count >= 2:
        score += 15
        notes.append(f'Touches {subsystem_count} subsystems')
    elif subsystem_count == 1:
        score += 5

    # God module (0–10)
    if touches_god:
        score += 10
        notes.append('Modifies a highly-imported module')

    # Dependency files (0–10)
    if touches_deps:
        score += 10
        notes.append('Dependency manifest changed')

    score = min(score, 100)

    if score >= 60:
        label = 'high'
    elif score >= 30:
        label = 'medium'
    else:
        label = 'low'

    return {
        'score': score,
        'label': label,
        'touches_god_module': touches_god,
        'touches_deps': touches_deps,
        'notes': notes,
    }
