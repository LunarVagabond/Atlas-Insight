from __future__ import annotations

_BEGINNER_LABELS = frozenset({'good first issue', 'hacktoberfest', 'up for grabs'})
_FEATURE_LABELS = frozenset({
    'enhancement', 'feature', 'feature request', 'feature-request',
    'type: enhancement', 'type: feature', 'type:enhancement', 'type:feature',
})


def score_issue_readiness(issue: dict, pr_refs: set) -> tuple[int, str]:
    score = 50
    labels_set = set(issue.get('labels', []))
    if labels_set & _BEGINNER_LABELS:
        score += 35
    elif labels_set & _FEATURE_LABELS:
        score += 10
    body = issue.get('body_excerpt', '') or ''
    if len(body) > 200:
        score += 15
    elif len(body) > 50:
        score += 5
    if issue.get('number') in pr_refs:
        score -= 25
    score = max(0, min(100, score))
    if score >= 75:
        label = 'Ready'
    elif score >= 50:
        label = 'Approachable'
    else:
        label = 'Complex'
    return score, label


def generate_issue_opportunities(contribution_data: dict) -> list[dict]:
    pr_refs = set(contribution_data.get('pr_issue_refs', []))
    opps: list[dict] = []
    for issue in contribution_data.get('issues', []):
        labels_set = set(issue['labels'])
        is_beginner = bool(labels_set & _BEGINNER_LABELS)
        is_feature = bool(labels_set & _FEATURE_LABELS)

        category = 'feature' if is_feature else 'github-issue'
        difficulty = 'beginner' if is_beginner else 'intermediate'
        risk = 'low' if is_beginner else 'medium'

        readiness_score, readiness_label = score_issue_readiness(issue, pr_refs)

        opps.append({
            'id': f'issue_{issue["number"]}',
            'title': issue['title'],
            'description': issue['body_excerpt'] or f'Open GitHub issue #{issue["number"]}',
            'difficulty': difficulty,
            'risk': risk,
            'category': category,
            'issue_url': issue['url'],
            'issue_number': issue['number'],
            'has_open_pr': issue['number'] in pr_refs,
            'labels': issue['labels'],
            'readiness_score': readiness_score,
            'readiness_label': readiness_label,
            'hints': [
                'Read the full issue description and all comments on GitHub to understand exactly what is being asked for',
                'Search the codebase for the function, file, or keyword mentioned in the issue before writing any code',
                'Leave a comment on the issue saying you would like to work on it — maintainers appreciate knowing someone is on it',
            ],
        })
    return opps
