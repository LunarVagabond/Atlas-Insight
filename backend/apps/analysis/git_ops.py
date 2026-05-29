import os
import re

import git
from django.conf import settings


def get_cache_path(url: str) -> str:
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if not match:
        raise ValueError(f'Invalid GitHub URL: {url}')
    owner, name = match.group(1), match.group(2)
    cache_dir = settings.REPO_CACHE_DIR / f'{owner}_{name}'
    return str(cache_dir)


def clone_or_fetch(url: str) -> tuple:
    cache_path = get_cache_path(url)
    if os.path.exists(cache_path):
        repo = git.Repo(cache_path)
        repo.remotes.origin.fetch()
    else:
        os.makedirs(cache_path, exist_ok=True)
        repo = git.Repo.clone_from(url, cache_path)
    sha = repo.head.commit.hexsha
    return repo, sha
