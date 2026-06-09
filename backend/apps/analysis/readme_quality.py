from __future__ import annotations

_CATEGORY_WEIGHTS_OSS = {
    'presence': 0.20,
    'getting_started': 0.25,
    'examples': 0.15,
    'discoverability': 0.15,
    'community': 0.15,
    'engagement': 0.10,
}

_CATEGORY_WEIGHTS_CLOSED = {
    'presence': 0.25,
    'getting_started': 0.30,
    'examples': 0.20,
    'discoverability': 0.15,
    'community': 0.0,
    'engagement': 0.10,
}


def score_readme_quality(
    readme: dict | None,
    structure: dict | None,
    scoring_mode: str = 'oss',
) -> dict:
    readme = readme or {}
    structure = structure or {}
    weights = _CATEGORY_WEIGHTS_OSS if scoring_mode == 'oss' else _CATEGORY_WEIGHTS_CLOSED

    categories: list[dict] = []
    recommendations: list[dict] = []

    cat_scores = {
        'presence': _score_presence(readme, recommendations),
        'getting_started': _score_getting_started(readme, recommendations),
        'examples': _score_examples(readme, recommendations),
        'discoverability': _score_discoverability(readme, recommendations),
        'community': _score_community(readme, structure, recommendations, scoring_mode),
        'engagement': _score_engagement(readme, recommendations),
    }

    total_weight = sum(weights.values()) or 1.0
    score = round(
        sum(cat_scores[k] * weights[k] for k in weights) / total_weight,
        1,
    )

    potential = score
    for rec in recommendations:
        potential += rec.get('score_gain', 0)
    potential = round(min(100.0, potential), 1)

    for key, weight in weights.items():
        if weight <= 0:
            continue
        cat_score = cat_scores[key]
        categories.append({
            'key': key,
            'weight': weight,
            'score': cat_score,
            'weighted_score': round(cat_score * weight, 1),
        })

    return {
        'score': score,
        'potential_score': potential,
        'categories': categories,
        'recommendations': recommendations,
    }


def _add_rec(
    recs: list[dict],
    *,
    rec_id: str,
    category: str,
    status: str,
    title: str,
    description: str,
    score_gain: float,
    hints: list[str] | None = None,
) -> None:
    if any(r['id'] == rec_id for r in recs):
        return
    recs.append({
        'id': rec_id,
        'category': category,
        'status': status,
        'title': title,
        'description': description,
        'score_gain': round(score_gain, 1),
        'hints': hints or [],
    })


def _score_presence(readme: dict, recs: list[dict]) -> float:
    if not readme.get('found'):
        _add_rec(
            recs,
            rec_id='readme_missing',
            category='presence',
            status='missing',
            title='Add a README',
            description='No README file was found in the repository root.',
            score_gain=18.0,
            hints=[
                'Create README.md in the repository root',
                'Include a one-line summary, install steps, and a usage example',
            ],
        )
        return 0.0

    score = 100.0
    wc = readme.get('word_count', 0)
    if wc < 50:
        _add_rec(
            recs,
            rec_id='readme_very_short',
            category='presence',
            status='needs_improvement',
            title='Expand the README overview',
            description=f'README is only {wc} words — too short to orient new readers.',
            score_gain=8.0,
        )
        score -= 35
    elif wc < 150:
        _add_rec(
            recs,
            rec_id='readme_short',
            category='presence',
            status='needs_improvement',
            title='Add more project context',
            description=f'README is {wc} words; aim for at least 150 for a solid overview.',
            score_gain=4.0,
        )
        score -= 15

    if not readme.get('description'):
        _add_rec(
            recs,
            rec_id='readme_no_description',
            category='presence',
            status='needs_improvement',
            title='Add an opening description',
            description='No introductory paragraph detected near the top of the README.',
            score_gain=3.0,
        )
        score -= 10

    return max(0.0, score)


def _score_getting_started(readme: dict, recs: list[dict]) -> float:
    if not readme.get('found'):
        return 0.0

    score = 100.0
    shallow = set(readme.get('shallow_sections') or [])

    if not readme.get('has_installation'):
        _add_rec(
            recs,
            rec_id='readme_installation',
            category='getting_started',
            status='missing',
            title='Add installation instructions',
            description='No installation or setup section detected in the README.',
            score_gain=12.0,
            hints=['Add a ## Installation section with prerequisites and setup commands'],
        )
        score -= 45
    elif any('install' in s.lower() for s in shallow):
        _add_rec(
            recs,
            rec_id='readme_installation_shallow',
            category='getting_started',
            status='needs_improvement',
            title='Expand installation section',
            description='Installation section exists but is very brief.',
            score_gain=4.0,
        )
        score -= 15

    if not readme.get('has_usage'):
        _add_rec(
            recs,
            rec_id='readme_usage',
            category='getting_started',
            status='missing',
            title='Add usage examples',
            description='No usage or getting-started section detected in the README.',
            score_gain=10.0,
            hints=['Add a ## Usage section with a minimal working example'],
        )
        score -= 40
    elif any('usage' in s.lower() or 'example' in s.lower() for s in shallow):
        _add_rec(
            recs,
            rec_id='readme_usage_shallow',
            category='getting_started',
            status='needs_improvement',
            title='Expand usage examples',
            description='Usage section exists but lacks substantive examples.',
            score_gain=3.0,
        )
        score -= 10

    return max(0.0, score)


def _score_examples(readme: dict, recs: list[dict]) -> float:
    if not readme.get('found'):
        return 0.0

    score = 100.0
    code_blocks = readme.get('code_block_count', 0)
    shallow_count = len(readme.get('shallow_sections') or [])

    if code_blocks == 0 and readme.get('word_count', 0) < 400:
        _add_rec(
            recs,
            rec_id='readme_no_code',
            category='examples',
            status='missing',
            title='Add code examples',
            description='No fenced code blocks found in the README.',
            score_gain=8.0,
        )
        score -= 30

    if shallow_count >= 3:
        _add_rec(
            recs,
            rec_id='readme_shallow_sections',
            category='examples',
            status='needs_improvement',
            title='Flesh out shallow sections',
            description=f'{shallow_count} headings have fewer than 20 words of content.',
            score_gain=5.0,
        )
        score -= min(40, shallow_count * 8)

    return max(0.0, score)


def _score_discoverability(readme: dict, recs: list[dict]) -> float:
    if not readme.get('found'):
        return 0.0

    score = 100.0
    has_docs = bool(readme.get('docs_links')) or readme.get('has_external_links')
    has_api = readme.get('has_api_docs')

    if not has_docs and not has_api:
        _add_rec(
            recs,
            rec_id='readme_no_docs_links',
            category='discoverability',
            status='missing',
            title='Link to documentation',
            description='No external documentation links or API section detected.',
            score_gain=7.0,
        )
        score -= 35
    elif not has_api:
        _add_rec(
            recs,
            rec_id='readme_no_api',
            category='discoverability',
            status='needs_improvement',
            title='Document API or reference material',
            description='Consider linking hosted docs or adding an API reference section.',
            score_gain=3.0,
        )
        score -= 10

    return max(0.0, score)


def _score_community(
    readme: dict,
    structure: dict,
    recs: list[dict],
    scoring_mode: str,
) -> float:
    if scoring_mode != 'oss':
        return 100.0
    if not readme.get('found'):
        return 0.0

    score = 100.0
    if not readme.get('has_contributing') and not structure.get('has_contributing'):
        _add_rec(
            recs,
            rec_id='readme_contributing',
            category='community',
            status='missing',
            title='Add contributing guidance',
            description='No CONTRIBUTING section in README or CONTRIBUTING.md file.',
            score_gain=6.0,
        )
        score -= 30
    if not readme.get('has_changelog') and not structure.get('has_changelog'):
        _add_rec(
            recs,
            rec_id='readme_changelog',
            category='community',
            status='missing',
            title='Reference a changelog',
            description='No changelog section or CHANGELOG file detected.',
            score_gain=4.0,
        )
        score -= 20
    if not readme.get('has_license') and not structure.get('license_type'):
        _add_rec(
            recs,
            rec_id='readme_license',
            category='community',
            status='missing',
            title='Document the license',
            description='License is not referenced in README and no LICENSE file was detected.',
            score_gain=5.0,
        )
        score -= 25

    return max(0.0, score)


def _score_engagement(readme: dict, recs: list[dict]) -> float:
    if not readme.get('found'):
        return 50.0

    if readme.get('social_links'):
        return 100.0

    _add_rec(
        recs,
        rec_id='readme_social',
        category='engagement',
        status='needs_improvement',
        title='Add community links (optional)',
        description='No chat or social links detected — helpful for open community projects.',
        score_gain=2.0,
    )
    return 70.0
