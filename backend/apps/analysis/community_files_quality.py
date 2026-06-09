from __future__ import annotations

_FILE_DEFS = (
    ('license', 'License', 'license_file', 'license_type'),
    ('contributing', 'Contributing Guide', 'has_contributing', 'contributing_file'),
    ('changelog', 'Changelog', 'has_changelog', 'changelog_file'),
    ('coc', 'Code of Conduct', 'has_coc', 'coc_file'),
    ('security', 'Security Policy', 'has_security_policy', 'security_policy_file'),
)


def score_community_files(
    readme: dict | None,
    structure: dict | None,
    scoring_mode: str = 'oss',
) -> dict:
    readme = readme or {}
    structure = structure or {}
    oss_mode = scoring_mode == 'oss'

    files: list[dict] = []
    recommendations: list[dict] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for key, label, flag_key, path_key in _FILE_DEFS:
        present = bool(structure.get(flag_key) or structure.get(path_key))
        if key == 'license':
            present = present or bool(structure.get('license_type'))
        file_score, recs = _score_file(key, label, present, structure, oss_mode)
        recommendations.extend(recs)
        files.append({
            'key': key,
            'label': label,
            'present': present,
            'score': file_score,
        })
        if present or oss_mode:
            weighted_sum += file_score
            weight_total += 1.0

    score = round(weighted_sum / weight_total, 1) if weight_total else 0.0
    potential = score
    for rec in recommendations:
        potential += rec.get('score_gain', 0)
    potential = round(min(100.0, potential), 1)

    return {
        'score': score,
        'potential_score': potential,
        'files': files,
        'recommendations': recommendations,
    }


def _score_file(
    key: str,
    label: str,
    present: bool,
    structure: dict,
    oss_mode: bool,
) -> tuple[float, list[dict]]:
    recs: list[dict] = []
    if not present:
        if oss_mode:
            recs.append({
                'id': f'community_{key}_missing',
                'file': key,
                'status': 'missing',
                'title': f'Add {label}',
                'description': f'No {label.lower()} file detected in the repository.',
                'score_gain': 12.0,
                'hints': [],
            })
            return 0.0, recs
        return 0.0, recs

    content = (structure.get('community_files_content') or {}).get(key) or ''
    word_count = len(content.split()) if content else 0
    score = 100.0

    if word_count < 30:
        recs.append({
            'id': f'community_{key}_shallow',
            'file': key,
            'status': 'needs_improvement',
            'title': f'Expand {label}',
            'description': f'{label} exists but is very short ({word_count} words).',
            'score_gain': 5.0,
            'hints': [],
        })
        score = 55.0
    elif word_count < 80:
        recs.append({
            'id': f'community_{key}_thin',
            'file': key,
            'status': 'needs_improvement',
            'title': f'Add detail to {label}',
            'description': f'{label} could use more substantive guidance.',
            'score_gain': 3.0,
            'hints': [],
        })
        score = 75.0

    return score, recs
