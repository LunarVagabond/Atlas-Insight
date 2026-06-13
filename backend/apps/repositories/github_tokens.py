from typing import Optional

from django.contrib.auth.models import AbstractBaseUser


class MissingRepoScopeError(Exception):
    pass


def token_has_repo_scope(token: str) -> bool:
    try:
        import requests as _requests
        r = _requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github+json',
            },
            timeout=5,
        )
        scopes = r.headers.get('X-OAuth-Scopes', '')
        return 'repo' in [s.strip() for s in scopes.split(',')]
    except Exception:
        return True


def _fetch_social_github_token(user: AbstractBaseUser) -> Optional[str]:
    from allauth.socialaccount.models import SocialToken

    social = SocialToken.objects.filter(
        account__user=user,
        account__provider='github',
    ).first()
    return social.token if social else None


def get_github_oauth_token(user) -> Optional[str]:
    if not user:
        return None
    token = _fetch_social_github_token(user)
    if not token:
        return None
    if token.startswith('ghu_') or token_has_repo_scope(token):
        return token
    return None


def require_github_oauth_token(user) -> Optional[str]:
    if not user:
        return None
    token = _fetch_social_github_token(user)
    if not token:
        return None
    if not token.startswith('ghu_') and not token_has_repo_scope(token):
        raise MissingRepoScopeError(
            'Your GitHub authorization is missing the "repo" scope required to '
            'access private repositories. Please disconnect and reconnect your '
            'GitHub account to re-authorize with the correct permissions.'
        )
    return token


def resolve_analysis_token(repo, user=None) -> Optional[str]:
    if repo.auth_token:
        return repo.auth_token
    return get_github_oauth_token(user)
