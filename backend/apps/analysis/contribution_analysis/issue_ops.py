from __future__ import annotations

from datetime import datetime, timezone

_BEGINNER_LABELS = frozenset({'good first issue', 'hacktoberfest', 'up for grabs'})
_FEATURE_LABELS = frozenset({
    'enhancement', 'feature', 'feature request', 'feature-request',
    'type: enhancement', 'type: feature', 'type:enhancement', 'type:feature',
})


def _days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - dt).days
    except ValueError:
        return None


def _has_acceptance_criteria(body: str) -> bool:
    return '- [ ]' in body or '- [x]' in body or '\n1.' in body


def _spec_clarity_signals(issue: dict, pr_refs: set) -> list[str]:
    signals: list[str] = []
    body = (issue.get('body_excerpt') or '').strip()
    body_len = len(body)
    title_len = len((issue.get('title') or '').strip())
    comments = issue.get('comments', 0) or 0
    days_stale = _days_since(issue.get('updated_at'))
    has_pr = issue.get('number') in pr_refs

    if has_pr:
        signals.append('Open PR already in progress')
    if body_len > 200:
        signals.append('Detailed description')
    elif body_len > 80:
        signals.append('Moderate description')
    elif body_len > 0:
        signals.append('Brief description')
    else:
        signals.append('No description provided')

    if _has_acceptance_criteria(body):
        signals.append('Includes acceptance criteria or steps')

    if title_len < 15:
        signals.append('Vague title')

    if 1 <= comments <= 8:
        signals.append('Some maintainer discussion')
    elif comments > 20:
        signals.append('Long comment thread')

    if days_stale is not None:
        if days_stale <= 30:
            signals.append('Recently updated')
        elif days_stale > 365:
            signals.append('Not updated in over a year')
        elif days_stale > 180:
            signals.append('Not updated in 6+ months')

    return signals


def score_issue_readiness(issue: dict, pr_refs: set) -> tuple[int, str, list[str]]:
    score = 15
    body = (issue.get('body_excerpt') or '').strip()
    body_len = len(body)

    if body_len > 250:
        score += 25
    elif body_len > 120:
        score += 18
    elif body_len > 40:
        score += 8
    elif body_len > 0:
        score += 2
    else:
        score -= 15

    if _has_acceptance_criteria(body):
        score += 15

    title_len = len((issue.get('title') or '').strip())
    if title_len < 15:
        score -= 10

    comments = issue.get('comments', 0) or 0
    if 1 <= comments <= 8:
        score += 8
    elif comments > 20:
        score -= 10

    days_stale = _days_since(issue.get('updated_at'))
    if days_stale is not None:
        if days_stale <= 30:
            score += 6
        elif days_stale > 365:
            score -= 18
        elif days_stale > 180:
            score -= 10

    if issue.get('number') in pr_refs:
        score -= 35

    score = max(0, min(100, score))
    if score >= 60:
        label = 'Clear'
    elif score >= 30:
        label = 'Partial'
    else:
        label = 'Vague'

    return score, label, _spec_clarity_signals(issue, pr_refs)


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

        readiness_score, readiness_label, readiness_signals = score_issue_readiness(issue, pr_refs)

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
            'readiness_signals': readiness_signals,
            'hints': [
                'Read the full issue description and all comments on GitHub to understand exactly what is being asked for',
                'Search the codebase for the function, file, or keyword mentioned in the issue before writing any code',
                'Leave a comment on the issue saying you would like to work on it — maintainers appreciate knowing someone is on it',
            ],
        })
    return opps
