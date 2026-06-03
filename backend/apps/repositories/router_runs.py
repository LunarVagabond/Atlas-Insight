"""Run management: analyze, list, get, retry, delete, timeline, by-slug."""
import ipaddress
import logging
import re
import socket
import uuid
from typing import Optional
from urllib.parse import urlparse as _urlparse

from django.db.models import Q
from django_ratelimit.decorators import ratelimit
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.analysis.github_meta import fetch_latest_sha
from apps.analysis.tasks import analyze_repository

from .models import AnalysisRun, Repository, UserFavorite

logger = logging.getLogger(__name__)
router = Router()


def _assert_not_limited(request):
    if getattr(request, 'limited', False):
        raise HttpError(429, 'Rate limit exceeded. Please try again later.')


def _resolve_api_token_user(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None
    from django.utils import timezone
    from apps.users.models import APIToken
    raw = auth_header[7:]
    token_hash = APIToken.hash_token(raw)
    try:
        api_token = APIToken.objects.select_related('user').get(
            token_hash=token_hash,
            revoked_at__isnull=True,
        )
    except APIToken.DoesNotExist:
        return None
    api_token.last_used_at = timezone.now()
    api_token.save(update_fields=['last_used_at'])
    return api_token.user


GITHUB_URL_RE = re.compile(
    r'^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$'
)

_SSRF_BLOCKED = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
]


def _validate_webhook_url(url: str) -> None:
    parsed = _urlparse(url)
    if parsed.scheme != 'https':
        raise HttpError(422, 'webhook_url must use https')
    host = parsed.hostname or ''
    if not host:
        raise HttpError(422, 'webhook_url has no hostname')
    try:
        addrs = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise HttpError(422, 'webhook_url hostname could not be resolved')
    for *_, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        if any(ip in net for net in _SSRF_BLOCKED):
            raise HttpError(422, 'webhook_url targets a private or internal address')


RERUN_COOLDOWN_HOURS = 4


def _cooldown_until(repo) -> Optional[str]:
    from datetime import timedelta
    if not repo.last_analyzed_at:
        return None
    from django.utils import timezone
    cutoff = repo.last_analyzed_at + timedelta(hours=RERUN_COOLDOWN_HOURS)
    if timezone.now() < cutoff:
        return cutoff.isoformat()
    return None


def _resolve_token(request, pat: Optional[str]) -> Optional[str]:
    if pat:
        return pat
    if request.user.is_authenticated:
        from allauth.socialaccount.models import SocialToken
        social = SocialToken.objects.filter(
            account__user=request.user,
            account__provider='github',
        ).first()
        if social:
            token = social.token
            if not token.startswith('ghu_') and not _token_has_repo_scope(token):
                raise HttpError(
                    403,
                    'Your GitHub authorization is missing the "repo" scope required to '
                    'access private repositories. Please disconnect and reconnect your '
                    'GitHub account to re-authorize with the correct permissions.',
                )
            return token
    return None


def _token_has_repo_scope(token: str) -> bool:
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


def _user_can_access_repo(user, owner: str, name: str) -> bool:
    from django.core.cache import cache
    cache_key = f'repo_access_{user.pk}_{owner}_{name}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from allauth.socialaccount.models import SocialToken
        import requests as _requests
        social = SocialToken.objects.filter(
            account__user=user,
            account__provider='github',
        ).first()
        if not social:
            cache.set(cache_key, False, 900)
            return False
        r = _requests.get(
            f'https://api.github.com/repos/{owner}/{name}',
            headers={
                'Authorization': f'Bearer {social.token}',
                'Accept': 'application/vnd.github+json',
            },
            timeout=5,
        )
        result = r.status_code == 200
    except Exception:
        result = False

    cache.set(cache_key, result, 900)
    return result


class AnalyzeRequest(Schema):
    url: str
    pat: Optional[str] = None
    webhook_url: Optional[str] = None
    notification_email: Optional[str] = None


class AnalyzeResponse(Schema):
    run_id: uuid.UUID
    status: str
    cached: bool


class RunStatusSchema(Schema):
    id: uuid.UUID
    status: str
    progress_step: str = ''
    triggered_at: str
    completed_at: Optional[str]
    result: Optional[dict]
    repo_url: str
    repo_owner: str
    repo_name: str
    is_stale: bool
    is_private: bool
    last_fetched_at: Optional[str]
    auth_token_warning: str
    cooldown_until: Optional[str] = None


class RunListItemSchema(Schema):
    id: uuid.UUID
    repo_id: uuid.UUID
    status: str
    triggered_at: str
    completed_at: Optional[str]
    repo_url: str
    repo_owner: str
    repo_name: str
    is_stale: bool
    is_private: bool
    is_favorited: bool = False
    last_fetched_at: Optional[str]
    tags: list[str] = []
    has_previous_run: bool = False
    primary_language: Optional[str] = None


class RunListSchema(Schema):
    items: list[RunListItemSchema]
    total: int
    page: int
    per_page: int


class SlugRunSchema(Schema):
    run_id: uuid.UUID
    status: str


@router.post('/analyze', response=AnalyzeResponse)
@ratelimit(key='user_or_ip', rate='10/h', method='POST', block=False)
def analyze(request, payload: AnalyzeRequest):
    if getattr(request, 'limited', False):
        raise HttpError(429, 'Rate limit exceeded — max 10 analyses per hour. Please wait before submitting another.')
    match = GITHUB_URL_RE.match(payload.url.strip())
    if not match:
        raise HttpError(422, 'Invalid GitHub repository URL')
    owner, name = match.group(1), match.group(2)

    repo, _ = Repository.objects.get_or_create(
        url=payload.url.rstrip('/'),
        defaults={'owner': owner, 'name': name},
    )
    if not repo.owner:
        repo.owner = owner
        repo.name = name
        repo.save(update_fields=['owner', 'name'])

    if payload.webhook_url:
        _validate_webhook_url(payload.webhook_url)

    token = _resolve_token(request, payload.pat) or repo.auth_token or None
    if token and token != repo.auth_token:
        repo.auth_token = token
        repo.save(update_fields=['auth_token'])

    latest_sha = fetch_latest_sha(owner, name, token=token)

    if latest_sha and latest_sha == repo.last_commit_sha:
        latest_run = repo.runs.order_by('-triggered_at').first()
        if latest_run and latest_run.status == 'completed':
            return AnalyzeResponse(run_id=latest_run.id, status='completed', cached=True)

    user = request.user if request.user.is_authenticated else _resolve_api_token_user(request)

    notification_email = ''
    if payload.notification_email:
        if not request.user.is_authenticated:
            raise HttpError(403, 'notification_email requires authentication')
        if payload.notification_email != request.user.email:
            raise HttpError(422, 'notification_email must match your account email')
        notification_email = payload.notification_email

    run = AnalysisRun.objects.create(
        repo=repo, status='pending', user=user,
        webhook_url=payload.webhook_url or '',
        notification_email=notification_email,
    )
    task = analyze_repository.delay(str(run.id))
    run.celery_task_id = task.id
    run.save(update_fields=['celery_task_id'])

    return AnalyzeResponse(run_id=run.id, status='pending', cached=False)


@router.get('/runs/', response=RunListSchema)
@ratelimit(key='user_or_ip', rate='120/h', method='GET', block=False)
def list_runs(
    request,
    q: str = '',
    sort: str = 'triggered_at',
    order: str = 'desc',
    page: int = 1,
    per_page: int = 25,
    mine: bool = False,
):
    _assert_not_limited(request)
    per_page = min(per_page, 25)
    from django.db.models import Exists, OuterRef, Subquery

    latest_per_repo = AnalysisRun.objects.filter(
        repo=OuterRef('pk'),
        status__in=['completed', 'pending', 'running'],
    ).order_by('-triggered_at').values('id')[:1]
    latest_ids = Repository.objects.annotate(
        latest_id=Subquery(latest_per_repo)
    ).exclude(latest_id=None).values('latest_id')

    qs = AnalysisRun.objects.filter(pk__in=latest_ids).select_related('repo', 'user')

    prev_run_exists = AnalysisRun.objects.filter(
        repo=OuterRef('repo'),
        status='completed',
        triggered_at__lt=OuterRef('triggered_at'),
    )
    qs = qs.annotate(has_previous_run=Exists(prev_run_exists))

    if request.user.is_authenticated:
        qs = qs.filter(
            Q(repo__is_private=False) |
            Q(repo__is_private=True, user=request.user)
        )
    else:
        qs = qs.filter(repo__is_private=False)

    if mine and request.user.is_authenticated:
        qs = qs.filter(user=request.user)

    if q:
        qs = qs.filter(
            Q(repo__url__icontains=q) | Q(repo__owner__icontains=q) | Q(repo__name__icontains=q)
        )

    allowed_sort = {'triggered_at', 'completed_at', 'status'}
    sort_field = sort if sort in allowed_sort else 'triggered_at'
    if order == 'asc':
        qs = qs.order_by(sort_field)
    else:
        qs = qs.order_by(f'-{sort_field}')

    total = qs.count()
    offset = (page - 1) * per_page
    runs = list(qs[offset: offset + per_page])

    fav_repo_ids: set = set()
    if request.user.is_authenticated:
        fav_repo_ids = set(
            UserFavorite.objects.filter(user=request.user).values_list('repo_id', flat=True)
        )

    return RunListSchema(
        items=[
            RunListItemSchema(
                id=r.id,
                repo_id=r.repo_id,
                status=r.status,
                triggered_at=r.triggered_at.isoformat(),
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
                repo_url=r.repo.url,
                repo_owner=r.repo.owner,
                repo_name=r.repo.name,
                is_stale=r.repo.is_stale,
                is_private=r.repo.is_private,
                is_favorited=r.repo_id in fav_repo_ids,
                last_fetched_at=r.repo.last_fetched_at.isoformat() if r.repo.last_fetched_at else None,
                tags=r.result.get('classification', {}).get('tags', []) if r.result else [],
                has_previous_run=getattr(r, 'has_previous_run', False),
                primary_language=r.result.get('github_meta', {}).get('primary_language') if r.result else None,
            )
            for r in runs
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get('/runs/{run_id}', response=RunStatusSchema)
@ratelimit(key='user_or_ip', rate='120/h', method='GET', block=False)
def get_run(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    from django.db.models import F
    try:
        run = AnalysisRun.objects.select_related('repo', 'user').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private:
        if not request.user.is_authenticated:
            raise HttpError(403, 'Access denied')
        if run.user != request.user:
            if not _user_can_access_repo(request.user, run.repo.owner, run.repo.name):
                raise HttpError(403, 'Access denied')
    if run.status == 'completed':
        Repository.objects.filter(pk=run.repo_id).update(view_count=F('view_count') + 1)
    return RunStatusSchema(
        id=run.id,
        status=run.status,
        progress_step=run.progress_step or '',
        triggered_at=run.triggered_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        result=run.result,
        repo_url=run.repo.url,
        repo_owner=run.repo.owner,
        repo_name=run.repo.name,
        is_stale=run.repo.is_stale,
        is_private=run.repo.is_private,
        last_fetched_at=run.repo.last_fetched_at.isoformat() if run.repo.last_fetched_at else None,
        auth_token_warning=run.repo.auth_token_warning,
        cooldown_until=_cooldown_until(run.repo),
    )


@router.post('/runs/{run_id}/retry', response=AnalyzeResponse)
@ratelimit(key='user_or_ip', rate='10/h', method='POST', block=False)
def retry_run(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        original = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if original.repo.is_private:
        if not request.user.is_authenticated or original.user != request.user:
            raise HttpError(403, 'Access denied')
    is_super = request.user.is_authenticated and request.user.is_superuser
    if not is_super:
        cooldown = _cooldown_until(original.repo)
        if cooldown:
            raise HttpError(
                429,
                f'This repository was analyzed recently. Re-analysis available after {cooldown}.',
            )
    user = request.user if request.user.is_authenticated else None
    run = AnalysisRun.objects.create(repo=original.repo, status='pending', user=user)
    task = analyze_repository.delay(str(run.id))
    run.celery_task_id = task.id
    run.save(update_fields=['celery_task_id'])
    return AnalyzeResponse(run_id=run.id, status='pending', cached=False)


@router.get('/runs/{run_id}/timeline')
def get_timeline(request, run_id: uuid.UUID):
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id, status='completed')
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found or not completed')
    if run.repo.is_private:
        if not request.user.is_authenticated or run.user != request.user:
            raise HttpError(403, 'Access denied')
    result = run.result or {}
    commits = result.get('commits', {})
    deps = result.get('dependencies', {})
    return {
        'commit_frequency': commits.get('weekly_frequency', []),
        'monthly_frequency': commits.get('monthly_frequency', []),
        'contributor_churn': commits.get('contributor_churn', []),
        'dependency_count': deps.get('dependency_count', 0),
    }


@router.delete('/runs/{run_id}', response={204: None})
def delete_run(request, run_id: uuid.UUID):
    if not request.user.is_authenticated:
        raise HttpError(403, 'Authentication required')
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if not run.repo.is_private:
        raise HttpError(403, 'Only private repository runs can be deleted')
    if run.user != request.user:
        raise HttpError(403, 'Access denied')
    repo = run.repo
    run.delete()
    if not repo.runs.exists():
        repo.delete()
    return None


@router.get('/by-slug/{owner}/{name}', response=SlugRunSchema)
def get_by_slug(request, owner: str, name: str):
    """Return the latest run for owner/name — used by permalink routes."""
    try:
        repo = Repository.objects.get(owner__iexact=owner, name__iexact=name)
    except Repository.DoesNotExist:
        raise HttpError(404, 'Repository not found')
    if repo.is_private:
        if not request.user.is_authenticated:
            raise HttpError(403, 'Access denied')
    run = repo.runs.select_related('user').order_by('-triggered_at').first()
    if not run:
        raise HttpError(404, 'No runs found for this repository')
    if repo.is_private and run.user != request.user:
        raise HttpError(403, 'Access denied')
    return SlugRunSchema(run_id=run.id, status=run.status)
