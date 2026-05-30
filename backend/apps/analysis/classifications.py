"""
Deterministic repo classification — contribution difficulty, project health,
and badge/tag assignment. All scores 0-100 where higher = worse/harder.
"""

CONTRIBUTION_THRESHOLDS = [
    (20, 'very_easy', 'Very Easy'),
    (40, 'easy', 'Easy'),
    (60, 'moderate', 'Moderate'),
    (80, 'hard', 'Hard'),
    (101, 'very_hard', 'Very Hard'),
]

HEALTH_THRESHOLDS = [
    (20, 'thriving', 'Thriving'),
    (40, 'active', 'Active'),
    (60, 'stable', 'Stable'),
    (80, 'declining', 'Declining'),
    (101, 'abandoned', 'Abandoned'),
]

COMPLEXITY_THRESHOLDS = [
    (20, 'simple', 'Simple'),
    (40, 'moderate', 'Moderate'),
    (60, 'complex', 'Complex'),
    (101, 'very_complex', 'Very Complex'),
]

DOC_THRESHOLDS = [
    (15, 'excellent', 'Excellent'),
    (30, 'good', 'Good'),
    (50, 'fair', 'Fair'),
    (75, 'poor', 'Poor'),
    (101, 'missing', 'Not Found'),
]


def classify_repo(
    commits: dict,
    graph: dict,
    deps: dict,
    readme: dict | None,
    structure: dict | None,
    security: dict | None,
    github_meta: dict | None,
) -> dict:
    contrib_score = _contribution_difficulty_score(commits, readme, structure, graph)
    health_score = _health_score(commits, github_meta)
    complexity_score = _complexity_score(graph, structure)
    doc_score = _documentation_score(readme, structure)

    tags = _compute_tags(
        commits, graph, deps, readme, structure, security, github_meta,
        health_score, complexity_score, doc_score,
    )

    return {
        'contribution_difficulty': _threshold_label(contrib_score, CONTRIBUTION_THRESHOLDS),
        'contribution_difficulty_score': contrib_score,
        'project_health': _threshold_label(health_score, HEALTH_THRESHOLDS),
        'project_health_score': health_score,
        'code_complexity': _threshold_label(complexity_score, COMPLEXITY_THRESHOLDS),
        'code_complexity_score': complexity_score,
        'documentation_grade': _threshold_label(doc_score, DOC_THRESHOLDS),
        'documentation_grade_score': doc_score,
        'tags': tags,
    }


def _contribution_difficulty_score(
    commits: dict, readme: dict | None, structure: dict | None, graph: dict
) -> int:
    score = 0

    # Documentation (0-30)
    if readme:
        if not readme.get('found'):
            score += 25
        else:
            wc = readme.get('word_count', 0)
            if wc < 100:
                score += 20
            elif wc < 300:
                score += 10
            if not readme.get('has_installation'):
                score += 5
            if not readme.get('has_usage'):
                score += 3
    if structure:
        if not structure.get('has_contributing'):
            score += 7

    # CI / testing (0-25)
    if structure:
        if not structure.get('has_ci'):
            score += 15
        test_ratio = structure.get('test_ratio', 0)
        if test_ratio < 0.05:
            score += 10
        elif test_ratio < 0.15:
            score += 5
        if not structure.get('has_lint_config'):
            score += 5

    # Activity (0-25)
    days_silent = commits.get('days_since_last_commit') or 0
    if commits.get('abandoned'):
        score += 25
    elif days_silent > 365:
        score += 20
    elif days_silent > 180:
        score += 10
    elif days_silent > 60:
        score += 3
    decay = commits.get('activity_decay_ratio', 1.0)
    if decay < 0.2:
        score += 5

    # Code complexity (0-20)
    god_count = len(graph.get('god_modules', []))
    cycle_count = graph.get('cycle_count', 0)
    score += min(10, god_count * 2)
    score += min(10, cycle_count * 2)

    return min(100, score)


def _health_score(commits: dict, github_meta: dict | None) -> int:
    score = 0

    # Activity decay (0-40)
    decay = commits.get('activity_decay_ratio', 1.0)
    score += int(max(0, 1 - decay) * 40)

    # Days since last commit (0-40)
    days = commits.get('days_since_last_commit') or 0
    if days > 730:
        score += 40
    elif days > 365:
        score += 30
    elif days > 180:
        score += 15
    elif days > 90:
        score += 5

    # Archived on GitHub (instant max)
    if github_meta and github_meta.get('archived'):
        score = 100

    return min(100, score)


def _complexity_score(graph: dict, structure: dict | None) -> int:
    score = 0
    god_count = len(graph.get('god_modules', []))
    cycle_count = graph.get('cycle_count', 0)
    node_count = graph.get('node_count', 0)

    score += min(40, god_count * 5)
    score += min(30, cycle_count * 3)
    if node_count > 500:
        score += 20
    elif node_count > 200:
        score += 10
    elif node_count > 50:
        score += 5

    if structure:
        total_lines = structure.get('total_lines', 0)
        if total_lines > 500_000:
            score += 20
        elif total_lines > 100_000:
            score += 10

    return min(100, score)


def _documentation_score(readme: dict | None, structure: dict | None) -> int:
    score = 0
    if not readme or not readme.get('found'):
        return 100

    wc = readme.get('word_count', 0)
    if wc < 50:
        score += 40
    elif wc < 200:
        score += 20
    elif wc < 500:
        score += 10

    if not readme.get('has_installation'):
        score += 10
    if not readme.get('has_usage'):
        score += 8
    if not readme.get('has_contributing'):
        score += 8
    if not readme.get('has_changelog'):
        score += 5
    if not readme.get('has_license'):
        score += 5

    if structure:
        if not structure.get('has_contributing'):
            score += 10
        if not structure.get('has_changelog'):
            score += 5
        if not structure.get('has_coc'):
            score += 3

    return min(100, score)


def _compute_tags(
    commits, graph, deps, readme, structure, security, github_meta,
    health_score, complexity_score, doc_score,
) -> list[str]:
    tags: list[str] = []

    # Activity / health
    if github_meta and github_meta.get('archived'):
        tags.append('archived')
    elif commits.get('abandoned'):
        tags.append('abandoned')
    elif health_score < 20:
        tags.append('actively-maintained')

    # Popularity
    stars = (github_meta or {}).get('stars', 0)
    if stars >= 50_000:
        tags.append('wildly-popular')
    elif stars >= 10_000:
        tags.append('popular')
    elif stars >= 1_000:
        tags.append('well-known')

    # Community
    contributors = commits.get('total_contributors', 0)
    if contributors >= 500:
        tags.append('large-community')
    elif contributors >= 100:
        tags.append('thriving-community')
    elif contributors <= 2:
        tags.append('solo-project')

    # Complexity
    if complexity_score >= 80:
        tags.append('highly-complex')
    elif complexity_score <= 20:
        tags.append('simple-codebase')

    # Documentation
    if doc_score <= 15:
        tags.append('well-documented')
    elif doc_score >= 75:
        tags.append('sparse-docs')

    # CI / testing
    if structure:
        if structure.get('has_ci') and structure.get('test_ratio', 0) >= 0.2:
            tags.append('well-tested')
        if not structure.get('has_ci'):
            tags.append('no-ci')
        if structure.get('release_count', 0) >= 10:
            tags.append('frequent-releases')
        license_type = structure.get('license_type')
        if license_type:
            tags.append(f'license:{license_type}')
        if structure.get('has_contributing'):
            tags.append('welcoming')

    # Security
    if security:
        if security.get('score', 0) == 0:
            tags.append('clean-secrets')
        elif security.get('score', 0) >= 35:
            tags.append('security-concerns')

    # Bus factor
    if structure:
        bf = structure.get('bus_factor', 1)
        if bf == 1:
            tags.append('single-maintainer')

    # Fork / origin
    if github_meta and github_meta.get('is_fork'):
        tags.append('fork')

    forks = (github_meta or {}).get('forks', 0)
    if forks >= 5_000:
        tags.append('highly-forked')

    return tags


def _threshold_label(score: int, thresholds: list[tuple]) -> dict:
    for limit, key, label in thresholds:
        if score < limit:
            return {'key': key, 'label': label, 'score': score}
    return {'key': thresholds[-1][1], 'label': thresholds[-1][2], 'score': score}
