import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def fetch_github_meta(owner: str, name: str) -> dict:
    headers: dict[str, str] = {'Accept': 'application/vnd.github+json'}
    token = getattr(settings, 'GITHUB_TOKEN', '')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    base_url = f'https://api.github.com/repos/{owner}/{name}'

    try:
        r = requests.get(base_url, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning('GitHub API returned %s for %s/%s', r.status_code, owner, name)
            return {}
        data = r.json()
    except Exception as exc:
        logger.warning('GitHub API fetch failed for %s/%s: %s', owner, name, exc)
        return {}

    # Open PR count via pulls endpoint + Link header pagination
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

    return {
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
        'created_at': data.get('created_at'),
        'pushed_at': data.get('pushed_at'),
        'homepage': data.get('homepage') or None,
    }
