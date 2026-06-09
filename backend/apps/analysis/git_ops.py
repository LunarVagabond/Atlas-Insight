import logging
import os
import re
import shutil
import subprocess
from typing import Optional

import git
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Override git config via env to disable any system credential helper
# (VSCode, GNOME keyring, etc.) for every git operation we run.
# GIT_CONFIG_COUNT / KEY / VALUE syntax requires git 2.32+ (2021).
# DISPLAY/WAYLAND_DISPLAY cleared so no GUI dialog can spawn from the worker.
_FETCH_TIMEOUT = 300   # seconds — kills hung fetch
_CLONE_TIMEOUT = 600   # seconds — kills hung clone

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


def get_cache_path(url: str, branch: str = '') -> str:
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if not match:
        raise ValueError(f'Invalid GitHub URL: {url}')
    owner, name = match.group(1), match.group(2)
    suffix = f'__{branch}' if branch else ''
    cache_dir = settings.REPO_CACHE_DIR / f'{owner}_{name}{suffix}'
    return str(cache_dir)


def _inject_pat(url: str, pat: str) -> str:
    return url.replace('https://', f'https://{pat}@', 1)


def _parse_github_next_url(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for segment in link_header.split(','):
        if 'rel="next"' in segment:
            m = re.search(r'<([^>]+)>', segment)
            if m:
                return m.group(1)
    return None


def _list_branches_via_git(url: str, pat: Optional[str] = None) -> list[str]:
    clone_url = _inject_pat(url, pat) if pat else url
    try:
        proc = subprocess.run(
            ['git', 'ls-remote', '--heads', clone_url],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, **_GIT_ENV},
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning('git ls-remote failed for %s: %s', url, exc)
        return []
    if proc.returncode != 0:
        logger.warning(
            'git ls-remote returned %s for %s: %s',
            proc.returncode,
            url,
            (proc.stderr or '')[:200],
        )
        return []
    branches: list[str] = []
    for line in proc.stdout.splitlines():
        if '\t' not in line:
            continue
        _, ref = line.split('\t', 1)
        if ref.startswith('refs/heads/'):
            branches.append(ref.removeprefix('refs/heads/'))
    return sorted(branches)


def _github_api_branches(
    owner: str,
    name: str,
    pat: Optional[str] = None,
) -> list[str]:
    import requests as _requests
    from django.conf import settings as _s

    headers = {'Accept': 'application/vnd.github+json'}
    token = pat or getattr(_s, 'GITHUB_TOKEN', '') or None
    if token:
        headers['Authorization'] = f'Bearer {token}'

    branches: list[str] = []
    api_url = f'https://api.github.com/repos/{owner}/{name}/branches'
    params: dict | None = {'per_page': 100, 'page': 1}

    for _ in range(100):
        try:
            resp = _requests.get(api_url, params=params, headers=headers, timeout=15)
        except Exception as exc:
            logger.warning('GitHub branches API request failed for %s/%s: %s', owner, name, exc)
            break

        if resp.status_code != 200:
            logger.warning(
                'GitHub branches API returned %s for %s/%s',
                resp.status_code,
                owner,
                name,
            )
            break

        data = resp.json()
        if not data:
            break
        branches.extend(b['name'] for b in data if isinstance(b, dict) and b.get('name'))

        next_url = _parse_github_next_url(resp.headers.get('Link'))
        if not next_url or len(data) < 100:
            break
        api_url = next_url
        params = None

    return branches


def list_remote_branches(url: str, pat: Optional[str] = None) -> list[str]:
    """Return sorted branch names via GitHub API, falling back to git ls-remote."""
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if not match:
        return []
    owner, name = match.group(1), match.group(2)

    tokens_to_try: list[Optional[str]] = []
    if pat:
        tokens_to_try.append(pat)
    from django.conf import settings as _s
    gh_token = getattr(_s, 'GITHUB_TOKEN', '') or None
    if gh_token and gh_token not in tokens_to_try:
        tokens_to_try.append(gh_token)
    tokens_to_try.append(None)

    for token in tokens_to_try:
        branches = _github_api_branches(owner, name, token)
        if branches:
            return sorted(branches)

    logger.info('GitHub API returned no branches for %s/%s — trying git ls-remote', owner, name)
    for token in ([pat] if pat else []) + [None]:
        git_branches = _list_branches_via_git(url, token)
        if git_branches:
            return git_branches

    cached = _list_branches_from_cache(url)
    if cached:
        logger.info('Listed %d branches from local cache for %s/%s', len(cached), owner, name)
        return cached
    return []


def _refs_from_repo_path(cache_path: str) -> list[str]:
    git_dir = os.path.join(cache_path, '.git')
    if not os.path.isdir(git_dir):
        return []
    try:
        repo = git.Repo(cache_path)
        names: set[str] = set()
        for ref in repo.remote().refs:
            ref_name = ref.name
            if not ref_name.startswith('origin/'):
                continue
            short = ref_name.removeprefix('origin/')
            if short == 'HEAD':
                continue
            names.add(short)
        return sorted(names)
    except Exception as exc:
        logger.warning('Failed to read branch refs from cache %s: %s', cache_path, exc)
        return []


def _list_branches_from_cache(url: str) -> list[str]:
    match = re.match(r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$', url)
    if not match:
        return []
    owner, name = match.group(1), match.group(2)
    prefix = f'{owner}_{name}'
    cache_root = settings.REPO_CACHE_DIR
    all_names: set[str] = set()

    default_path = get_cache_path(url, '')
    all_names.update(_refs_from_repo_path(default_path))

    if cache_root.is_dir():
        for entry in cache_root.iterdir():
            if not entry.is_dir():
                continue
            entry_name = entry.name
            if entry_name == prefix:
                all_names.update(_refs_from_repo_path(str(entry)))
            elif entry_name.startswith(prefix + '__'):
                branch_suffix = entry_name[len(prefix + '__'):]
                if branch_suffix:
                    all_names.add(branch_suffix)
                all_names.update(_refs_from_repo_path(str(entry)))

    return sorted(all_names)


def _scrub(text: str | None, pat: str) -> str:
    return (text or '').replace(pat, '***')


def _sanitize_exc(exc: git.GitCommandError, pat: str) -> git.GitCommandError:
    cmd = [_scrub(c, pat) if isinstance(c, str) else c for c in (exc.command or [])]
    return git.GitCommandError(
        command=cmd, status=exc.status,
        stderr=_scrub(exc.stderr, pat),
        stdout=_scrub(exc.stdout, pat),
    )


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
        'returned error: 401',
        'returned error: 403',
        'returned error: 404',
        'http error',
    ))


def _sync_to_origin_head(repo: git.Repo) -> str:
    """Make cached clone match origin's default branch and return checked-out SHA."""
    branch = None
    try:
        origin_head = repo.git.symbolic_ref('refs/remotes/origin/HEAD').strip()
        branch = origin_head.rsplit('/', 1)[-1]
    except git.GitCommandError:
        pass

    checked_out = False
    if branch:
        try:
            if branch in repo.heads:
                repo.git.checkout(branch)
            else:
                repo.git.checkout('-B', branch, f'origin/{branch}')
            repo.git.reset('--hard', f'origin/{branch}')
            checked_out = True
        except git.GitCommandError:
            pass

    if not checked_out:
        # origin/HEAD doesn't resolve cleanly (e.g. points to a tag, not a branch)
        # Fall back to FETCH_HEAD which is always set after a successful fetch.
        repo.git.reset('--hard', 'FETCH_HEAD')

    repo.git.clean('-fdx')
    return repo.head.commit.hexsha


def _checkout_branch(repo: git.Repo, branch: str) -> str:
    """Checkout a specific remote branch and return its HEAD SHA."""
    if branch in repo.heads:
        repo.git.checkout(branch)
    else:
        repo.git.checkout('-B', branch, f'origin/{branch}')
    repo.git.reset('--hard', f'origin/{branch}')
    repo.git.clean('-fdx')
    return repo.head.commit.hexsha


def clone_or_fetch(url: str, pat: Optional[str] = None, branch: str = '') -> tuple:
    cache_path = get_cache_path(url, branch)
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
                repo.remotes.origin.fetch(kill_after_timeout=_FETCH_TIMEOUT)
            except git.GitCommandError as exc:
                if pat:
                    repo.remotes.origin.set_url(url)
                if _is_auth_error(exc):
                    raise PermissionError(
                        'Repository is private or inaccessible. '
                        'Connect your GitHub account to analyze private repositories.'
                    ) from None
                shutil.rmtree(cache_path, ignore_errors=True)
                raise _sanitize_exc(exc, pat) if pat else exc
            if pat:
                repo.remotes.origin.set_url(url)
            sha = _checkout_branch(repo, branch) if branch else _sync_to_origin_head(repo)
            return repo, sha, timezone.now()

    # Fresh clone (or after wipe above)
    g = git.Git()
    g.update_environment(**_GIT_ENV)
    try:
        g.execute(['git', 'clone', clone_url, cache_path], kill_after_timeout=_CLONE_TIMEOUT)
        repo = git.Repo(cache_path)
    except git.GitCommandError as exc:
        # Remove partial clone dir so the next attempt starts clean
        if os.path.exists(cache_path):
            shutil.rmtree(cache_path)
        if _is_auth_error(exc):
            raise PermissionError(
                'Repository is private or inaccessible. '
                'Connect your GitHub account to analyze private repositories.'
            ) from None
        raise _sanitize_exc(exc, pat) if pat else exc
    if pat:
        repo.remotes.origin.set_url(url)

    if branch:
        sha = _checkout_branch(repo, branch)
    else:
        sha = repo.head.commit.hexsha
    return repo, sha, timezone.now()
