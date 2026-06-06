import logging
import re
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _rate_limited(resp) -> bool:
    """True if the response indicates GitHub rate limit exhaustion."""
    if resp.status_code == 429:
        return True
    if resp.status_code == 403:
        remaining = resp.headers.get('X-RateLimit-Remaining', '1')
        try:
            return int(remaining) == 0
        except ValueError:
            pass
    return False


def fetch_latest_sha(
    owner: str, name: str, token: Optional[str] = None, branch: str = ''
) -> Optional[str]:
    headers = {'Accept': 'application/vnd.github.v3+json'}
    effective_token = token or getattr(settings, 'GITHUB_TOKEN', '')
    if effective_token:
        headers['Authorization'] = f'Bearer {effective_token}'
    params: dict = {'per_page': 1}
    if branch:
        params['sha'] = branch
    try:
        resp = requests.get(
            f'https://api.github.com/repos/{owner}/{name}/commits',
            params=params,
            headers=headers,
            timeout=10,
        )
        if _rate_limited(resp):
            logger.warning('GitHub rate limit hit fetching SHA for %s/%s', owner, name)
            return None
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]['sha']
    except Exception:
        logger.warning('Failed to fetch latest SHA for %s/%s', owner, name)
    return None


def _fetch_contributors(owner: str, name: str, headers: dict) -> list[dict]:
    try:
        r = requests.get(
            f'https://api.github.com/repos/{owner}/{name}/contributors',
            params={'per_page': 30, 'anon': 0},
            headers=headers,
            timeout=15,
        )
        if _rate_limited(r):
            logger.warning('GitHub rate limit hit fetching contributors for %s/%s', owner, name)
            return []
        if r.status_code != 200:
            return []
        return [
            {
                'login': c.get('login', ''),
                'avatar_url': c.get('avatar_url', ''),
                'html_url': c.get('html_url', ''),
                'contributions': c.get('contributions', 0),
            }
            for c in r.json()
            if c.get('type') not in ('Anonymous', 'Bot')
            and '[bot]' not in (c.get('login') or '').lower()
        ]
    except Exception:
        return []


def _fetch_github_meta_rest(owner: str, name: str, headers: dict) -> dict:
    """REST fallback for fetch_github_meta(). Called only when GraphQL fails."""
    base_url = f'https://api.github.com/repos/{owner}/{name}'
    try:
        r = requests.get(base_url, headers=headers, timeout=15)
        if _rate_limited(r):
            reset = r.headers.get('X-RateLimit-Reset', '?')
            logger.warning('GitHub rate limit hit for %s/%s (resets %s)', owner, name, reset)
            return {}
        if r.status_code != 200:
            logger.warning('GitHub API returned %s for %s/%s', r.status_code, owner, name)
            return {}
        data = r.json()
    except Exception as exc:
        logger.warning('GitHub REST fetch failed for %s/%s: %s', owner, name, exc)
        return {}

    open_prs: int | None = None
    try:
        pr_r = requests.get(
            f'{base_url}/pulls',
            params={'state': 'open', 'per_page': 1},
            headers=headers,
            timeout=10,
        )
        if pr_r.status_code == 200:
            link = pr_r.headers.get('Link', '')
            m = re.search(r'page=(\d+)>; rel="last"', link)
            open_prs = int(m.group(1)) if m else len(pr_r.json())
    except Exception:
        pass

    license_info = data.get('license') or {}
    releases_meta = _fetch_releases_meta(owner, name, headers)
    github_languages = _fetch_languages(owner, name, headers)

    return {
        'html_url': data.get('html_url'),
        'stars': data.get('stargazers_count', 0),
        'forks': data.get('forks_count', 0),
        'open_issues': data.get('open_issues_count', 0),
        'open_prs': open_prs,
        'watchers': data.get('subscribers_count', 0),
        'primary_language': data.get('language'),
        'topics': data.get('topics', []),
        'license_spdx': license_info.get('spdx_id'),
        'license_name': license_info.get('name'),
        'github_description': data.get('description'),
        'size_kb': data.get('size', 0),
        'default_branch': data.get('default_branch', 'main'),
        'has_wiki': data.get('has_wiki', False),
        'has_discussions': data.get('has_discussions', False),
        'archived': data.get('archived', False),
        'is_fork': data.get('fork', False),
        'is_private': data.get('private', False),
        'created_at': data.get('created_at'),
        'pushed_at': data.get('pushed_at'),
        'homepage': data.get('homepage') or None,
        'releases_meta': releases_meta,
        'github_languages': github_languages,
    }


def fetch_github_meta(owner: str, name: str, token: Optional[str] = None) -> dict:
    from apps.analysis.github_graphql import fetch_repo_meta_graphql

    effective_token = token or getattr(settings, 'GITHUB_TOKEN', '') or None
    headers: dict[str, str] = {'Accept': 'application/vnd.github+json'}
    if effective_token:
        headers['Authorization'] = f'Bearer {effective_token}'

    try:
        gql_meta = fetch_repo_meta_graphql(owner, name, token=effective_token)
    except Exception as exc:
        logger.warning('GraphQL fetch failed for %s/%s (%s), falling back to REST', owner, name, exc)  # noqa: E501
        gql_meta = _fetch_github_meta_rest(owner, name, headers)
        if not gql_meta:
            return {}

    contributors = _fetch_contributors(owner, name, headers)
    contribution_data = fetch_contribution_data(owner, name, headers)

    return {
        **gql_meta,
        'contributors': contributors,
        'contribution_data': contribution_data,
    }


def _fetch_languages(owner: str, name: str, headers: dict) -> list[dict]:
    """Fetch language breakdown from GitHub Linguist (byte counts, same as GitHub UI)."""
    try:
        r = requests.get(
            f'https://api.github.com/repos/{owner}/{name}/languages',
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200:
            return []
        raw = r.json()  # {"TypeScript": 123456, "Vue": 23456, ...}
        total_bytes = sum(raw.values()) or 1
        return sorted(
            [
                {
                    'name': lang,
                    'bytes': b,
                    'pct': round(b / total_bytes * 100, 1),
                }
                for lang, b in raw.items()
            ],
            key=lambda x: -x['bytes'],
        )
    except Exception:
        logger.warning('Failed to fetch languages for %s/%s', owner, name)
        return []


def _fetch_releases_meta(owner: str, name: str, headers: dict) -> dict | None:
    """Fetch release counts using GitHub's prerelease flag. Up to 2 pages (200 releases)."""
    base_url = f'https://api.github.com/repos/{owner}/{name}/releases'
    try:
        all_releases: list[dict] = []
        for page in range(1, 3):
            r = requests.get(
                base_url,
                params={'per_page': 100, 'page': page},
                headers=headers,
                timeout=10,
            )
            if r.status_code != 200:
                break
            batch = r.json()
            all_releases.extend(batch)
            if 'rel="next"' not in r.headers.get('Link', ''):
                break

        if not all_releases:
            return None

        stable = [r for r in all_releases if not r.get('prerelease') and not r.get('draft')]
        prereleases = [r for r in all_releases if r.get('prerelease') and not r.get('draft')]

        def _rel(r: dict) -> dict:
            return {'name': r.get('tag_name', ''), 'date': r.get('published_at', '')}

        return {
            'stable_count': len(stable),
            'prerelease_count': len(prereleases),
            'total_count': len(stable) + len(prereleases),
            'latest_stable': _rel(stable[0]) if stable else None,
            'latest_prerelease': _rel(prereleases[0]) if prereleases else None,
        }
    except Exception as exc:
        logger.warning('_fetch_releases_meta failed for %s/%s: %s', owner, name, exc)
        return None


_CONTRIBUTION_LABELS = frozenset({
    'good first issue', 'help wanted', 'hacktoberfest', 'up for grabs',
    'enhancement', 'feature', 'feature request', 'feature-request',
    'type: enhancement', 'type: feature', 'type:enhancement', 'type:feature',
})


_FEATURE_LABEL_CANDIDATES = [
    'enhancement', 'feature', 'feature request', 'feature-request',
    'type: enhancement', 'type: feature',
]


def _parse_issues(raw: list, seen: set[int]) -> list[dict]:
    results = []
    for issue in raw:
        if 'pull_request' in issue or issue['number'] in seen:
            continue
        issue_labels = {lbl['name'].lower() for lbl in issue.get('labels', [])}
        if not issue_labels & _CONTRIBUTION_LABELS:
            continue
        seen.add(issue['number'])
        results.append({
            'number': issue['number'],
            'title': issue['title'],
            'url': issue['html_url'],
            'labels': sorted(issue_labels),
            'body_excerpt': (issue.get('body') or '')[:300],
        })
    return results


def fetch_contribution_data(owner: str, name: str, headers: dict) -> dict | None:
    """Fetch relevant issues + open PRs for contribution analysis.
    3 API calls max: contribution issues, feature/enhancement issues, open PRs.
    Returns None on rate limit or error."""
    import re as _re
    base_url = f'https://api.github.com/repos/{owner}/{name}'
    try:
        seen: set[int] = set()
        issues: list[dict] = []

        # Call 1: recently-updated issues (catches good first issue, help wanted)
        r1 = requests.get(
            f'{base_url}/issues',
            params={'state': 'open', 'per_page': 100, 'sort': 'updated'},
            headers=headers,
            timeout=10,
        )
        if r1.status_code == 403:
            logger.warning('GitHub rate limit hit fetching contribution data for %s/%s', owner, name)
            return None
        if r1.status_code == 200:
            issues.extend(_parse_issues(r1.json(), seen))

        # Call 2: enhancement/feature labeled issues specifically
        # Try each candidate label until we find one that returns results
        for feature_label in _FEATURE_LABEL_CANDIDATES:
            r2 = requests.get(
                f'{base_url}/issues',
                params={'state': 'open', 'labels': feature_label, 'per_page': 50, 'sort': 'updated'},
                headers=headers,
                timeout=10,
            )
            if r2.status_code == 403:
                break
            if r2.status_code == 200 and r2.json():
                issues.extend(_parse_issues(r2.json(), seen))
                break  # found a working label, stop trying

        # Call 3: open PRs for cross-referencing
        pr_issue_refs: set[int] = set()
        r3 = requests.get(
            f'{base_url}/pulls',
            params={'state': 'open', 'per_page': 100},
            headers=headers,
            timeout=10,
        )
        if r3.status_code == 200:
            for pr in r3.json():
                text = f"{pr.get('title', '')} {pr.get('body') or ''}"
                for m in _re.finditer(r'#(\d+)', text):
                    pr_issue_refs.add(int(m.group(1)))

        return {'issues': issues, 'pr_issue_refs': list(pr_issue_refs)}
    except Exception as exc:
        logger.warning('fetch_contribution_data failed for %s/%s: %s', owner, name, exc)
        return None
