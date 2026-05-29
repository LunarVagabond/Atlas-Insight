import os
import re
from typing import Optional

import git
from django.conf import settings
from django.utils import timezone


def get_cache_path(url: str) -> str:
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if not match:
        raise ValueError(f'Invalid GitHub URL: {url}')
    owner, name = match.group(1), match.group(2)
    cache_dir = settings.REPO_CACHE_DIR / f'{owner}_{name}'
    return str(cache_dir)


def _inject_pat(url: str, pat: str) -> str:
    return url.replace('https://', f'https://{pat}@', 1)


def clone_or_fetch(url: str, pat: Optional[str] = None) -> tuple:
    cache_path = get_cache_path(url)
    clone_url = _inject_pat(url, pat) if pat else url
    if os.path.exists(cache_path):
        repo = git.Repo(cache_path)
        if pat:
            repo.remotes.origin.set_url(clone_url)
        repo.remotes.origin.fetch()
        if pat:
            # Strip PAT from stored remote immediately after fetch
            repo.remotes.origin.set_url(url)
    else:
        os.makedirs(cache_path, exist_ok=True)
        repo = git.Repo.clone_from(clone_url, cache_path)
        if pat:
            # Strip PAT from stored remote so it never persists on disk
            repo.remotes.origin.set_url(url)
    sha = repo.head.commit.hexsha
    fetched_at = timezone.now()
    return repo, sha, fetched_at
