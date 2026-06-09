from __future__ import annotations

from .readme_quality import score_readme_quality

_FILE_DEFS = (
    ('license', 'License', 'license_file', 'license_type'),
    ('contributing', 'Contributing Guide', 'has_contributing', 'contributing_file'),
    ('changelog', 'Changelog', 'has_changelog', 'changelog_file'),
    ('coc', 'Code of Conduct', 'has_coc', 'coc_file'),
    ('security', 'Security Policy', 'has_security_policy', 'security_policy_file'),
)

_WEIGHTS_OSS = {
    'readme': 0.25,
    'license': 0.20,
    'contributing': 0.18,
    'security': 0.15,
    'coc': 0.10,
    'changelog': 0.12,
}

_WEIGHTS_CLOSED = {
    'readme': 0.35,
    'license': 0.20,
    'contributing': 0.15,
    'security': 0.15,
    'coc': 0.08,
    'changelog': 0.07,
}


def score_community_files(
    readme: dict | None,
    structure: dict | None,
    scoring_mode: str = 'oss',
    readme_quality_score: float | None = None,
) -> dict:
    readme = readme or {}
    structure = structure or {}
    oss_mode = scoring_mode == 'oss'
    weights = _WEIGHTS_OSS if oss_mode else _WEIGHTS_CLOSED

    files: list[dict] = []
    recommendations: list[dict] = []
    weighted_sum = 0.0
    weight_total = 0.0

    readme_present = bool(readme.get('found'))
    readme_score = _readme_file_score(
        readme, structure, scoring_mode, readme_quality_score,
    )
    if not readme_present and oss_mode:
        recommendations.append({
            'id': 'community_readme_missing',
            'file': 'readme',
            'status': 'missing',
            'title': 'Add a README',
            'description': 'No README file was found in the repository root.',
            'score_gain': round(_WEIGHTS_OSS['readme'] * 100, 1),
            'hints': ['Create README.md with overview, install steps, and examples'],
        })
    files.append(_file_entry(
        'readme', 'README', readme_present, readme_score, weights['readme'],
        oss_mode, readme_present,
    ))
    if readme_present or oss_mode:
        weighted_sum += files[-1]['weighted_score']
        weight_total += weights['readme']

    for key, label, flag_key, path_key in _FILE_DEFS:
        present = bool(structure.get(flag_key) or structure.get(path_key))
        if key == 'license':
            present = present or bool(structure.get('license_type'))
        file_score, recs = _score_file(key, label, present, structure, oss_mode, weights[key])
        recommendations.extend(recs)
        entry = _file_entry(key, label, present, file_score, weights[key], oss_mode, present)
        files.append(entry)
        if present or oss_mode:
            weighted_sum += entry['weighted_score']
            weight_total += weights[key]

    score = round(weighted_sum / weight_total, 1) if weight_total else 0.0
    potential = score
    for rec in recommendations:
        potential += rec.get('score_gain', 0)
    potential = round(min(100.0, potential), 1)

    breakdown = sorted(
        [f for f in files if f['gap'] > 0],
        key=lambda f: f['gap'],
        reverse=True,
    )

    return {
        'score': score,
        'potential_score': potential,
        'files': files,
        'breakdown': breakdown,
        'recommendations': recommendations,
    }


def _file_entry(
    key: str,
    label: str,
    present: bool,
    file_score: float,
    weight: float,
    oss_mode: bool,
    counts: bool,
) -> dict:
    weighted = round(file_score * weight, 1) if counts or oss_mode else 0.0
    gap = round(weight * (100.0 - file_score), 1) if (counts or oss_mode) else 0.0
    return {
        'key': key,
        'label': label,
        'present': present,
        'score': round(file_score, 1),
        'weight': weight,
        'weighted_score': weighted,
        'gap': gap,
    }


def _readme_file_score(
    readme: dict,
    structure: dict,
    scoring_mode: str,
    readme_quality_score: float | None,
) -> float:
    if not readme.get('found'):
        return 0.0
    if readme_quality_score is not None:
        return float(readme_quality_score)
    return score_readme_quality(readme, structure, scoring_mode=scoring_mode)['score']


def _score_file(
    key: str,
    label: str,
    present: bool,
    structure: dict,
    oss_mode: bool,
    weight: float,
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
                'score_gain': round(weight * 100, 1),
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
            'score_gain': round(weight * 45, 1),
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
            'score_gain': round(weight * 25, 1),
            'hints': [],
        })
        score = 75.0

    return score, recs
