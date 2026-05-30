import os
import re
import shutil
from typing import Optional

import git
from django.conf import settings
from django.utils import timezone

# Override git config via env to disable any system credential helper
# (VSCode, GNOME keyring, etc.) for every git operation we run.
# GIT_CONFIG_COUNT / KEY / VALUE syntax requires git 2.32+ (2021).
# DISPLAY/WAYLAND_DISPLAY cleared so no GUI dialog can spawn from the worker.
_GIT_ENV = {
    'GIT_TERMINAL_PROMPT': '0',       # never block waiting for a terminal prompt
    'GIT_CONFIG_COUNT': '1',
    'GIT_CONFIG_KEY_0': 'credential.helper',
    'GIT_CONFIG_VALUE_0': '',          # empty = disabled
    'DISPLAY': '',                     # no X11 GUI dialogs from Celery worker
    'WAYLAND_DISPLAY': '',             # no Wayland GUI dialogs
    'DBUS_SESSION_BUS_ADDRESS': '',    # no desktop session bus (keyring, VSCode)
    # GitPython merges os.environ then updates with this dict, so inherited
    # VS Code credential-helper vars must be explicitly cleared here.
    'GIT_ASKPASS': '',
    'SSH_ASKPASS': '',
    'SSH_ASKPASS_REQUIRE': 'never',
    'VSCODE_GIT_ASKPASS_NODE': '',
    'VSCODE_GIT_ASKPASS_MAIN': '',
    'VSCODE_GIT_ASKPASS_PIPE': '',
}


def get_cache_path(url: str) -> str:
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if not match:
        raise ValueError(f'Invalid GitHub URL: {url}')
    owner, name = match.group(1), match.group(2)
    cache_dir = settings.REPO_CACHE_DIR / f'{owner}_{name}'
    return str(cache_dir)


def _inject_pat(url: str, pat: str) -> str:
    return url.replace('https://', f'https://{pat}@', 1)


def _is_auth_error(exc: git.GitCommandError) -> bool:
    msg = str(exc).lower()
    return any(p in msg for p in (
        'terminal prompts disabled',
        'authentication failed',
        'could not read username',
        'access denied',
        'repository not found',
        'write access to repository not granted',
        'remote: write access',
    ))


def clone_or_fetch(url: str, pat: Optional[str] = None) -> tuple:
    cache_path = get_cache_path(url)
    clone_url = _inject_pat(url, pat) if pat else url

    if os.path.exists(cache_path):
        try:
            repo = git.Repo(cache_path)
        except git.InvalidGitRepositoryError:
            # Previous clone failed and left a broken dir — wipe and re-clone
            shutil.rmtree(cache_path)
        else:
            if pat:
                repo.remotes.origin.set_url(clone_url)
            repo.git.update_environment(**_GIT_ENV)
            try:
                repo.remotes.origin.fetch()
            except git.GitCommandError as exc:
                if pat:
                    repo.remotes.origin.set_url(url)
                if _is_auth_error(exc):
                    raise PermissionError(
                        'Repository is private or inaccessible. '
                        'Connect your GitHub account to analyze private repositories.'
                    ) from None
                raise
            if pat:
                repo.remotes.origin.set_url(url)
            sha = repo.head.commit.hexsha
            return repo, sha, timezone.now()

    # Fresh clone (or after wipe above)
    g = git.Git()
    g.update_environment(**_GIT_ENV)
    try:
        repo = git.Repo.clone_from(clone_url, cache_path, env=_GIT_ENV)
    except git.GitCommandError as exc:
        # Remove partial clone dir so the next attempt starts clean
        if os.path.exists(cache_path):
            shutil.rmtree(cache_path)
        if _is_auth_error(exc):
            raise PermissionError(
                'Repository is private or inaccessible. '
                'Connect your GitHub account to analyze private repositories.'
            ) from None
        raise
    if pat:
        repo.remotes.origin.set_url(url)

    return repo, repo.head.commit.hexsha, timezone.now()
