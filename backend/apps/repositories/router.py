import logging
import re
import uuid
from typing import Optional

from django.db.models import Q
from django.http import HttpResponse
from django_ratelimit.decorators import ratelimit
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.analysis.github_meta import fetch_latest_sha
from apps.analysis.tasks import analyze_repository

from .models import AnalysisRun, Repository

logger = logging.getLogger(__name__)
router = Router(tags=['repositories'])

GITHUB_URL_RE = re.compile(
    r'^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$'
)


class AnalyzeRequest(Schema):
    url: str
    pat: Optional[str] = None
    webhook_url: Optional[str] = None


class RunStatusSchema(Schema):
    id: uuid.UUID
    status: str
    triggered_at: str
    completed_at: Optional[str]
    result: Optional[dict]
    repo_url: str
    repo_owner: str
    repo_name: str
    is_stale: bool
    last_fetched_at: Optional[str]
    auth_token_warning: str


class AnalyzeResponse(Schema):
    run_id: uuid.UUID
    status: str
    cached: bool


class RunListItemSchema(Schema):
    id: uuid.UUID
    status: str
    triggered_at: str
    completed_at: Optional[str]
    repo_url: str
    repo_owner: str
    repo_name: str
    is_stale: bool
    is_private: bool
    last_fetched_at: Optional[str]
    tags: list[str] = []


class RunListSchema(Schema):
    items: list[RunListItemSchema]
    total: int
    page: int
    per_page: int


def _resolve_token(request, pat: Optional[str]) -> Optional[str]:
    """PAT from request > user's GitHub OAuth token > None (server token used in tasks)."""
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
            # GitHub App user tokens (ghu_) use repository permission grants, not OAuth
            # scopes — skip scope check and let the clone surface any access errors.
            # Only classic OAuth tokens (gho_) carry X-OAuth-Scopes.
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
    """Check X-OAuth-Scopes header for classic OAuth tokens (gho_ prefix only)."""
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

    token = _resolve_token(request, payload.pat) or repo.auth_token or None
    latest_sha = fetch_latest_sha(owner, name, token=token)

    if latest_sha and latest_sha == repo.last_commit_sha:
        latest_run = repo.runs.order_by('-triggered_at').first()
        if latest_run and latest_run.status == 'completed':
            return AnalyzeResponse(run_id=latest_run.id, status='completed', cached=True)
        # latest run is failed/pending/running — fall through and re-queue

    user = request.user if request.user.is_authenticated else None
    run = AnalysisRun.objects.create(repo=repo, status='pending', user=user, webhook_url=payload.webhook_url or '')
    task = analyze_repository.delay(str(run.id), pat=token)
    run.celery_task_id = task.id
    run.save(update_fields=['celery_task_id'])

    return AnalyzeResponse(run_id=run.id, status='pending', cached=False)


@router.get('/runs/', response=RunListSchema)
def list_runs(
    request,
    q: str = '',
    sort: str = 'triggered_at',
    order: str = 'desc',
    page: int = 1,
    per_page: int = 25,
    mine: bool = False,
):
    from django.db.models import OuterRef, Subquery

    # Latest run per repo
    latest_per_repo = AnalysisRun.objects.filter(
        repo=OuterRef('pk')
    ).order_by('-triggered_at').values('id')[:1]
    latest_ids = Repository.objects.annotate(
        latest_id=Subquery(latest_per_repo)
    ).values('latest_id')

    qs = AnalysisRun.objects.filter(pk__in=latest_ids).select_related('repo', 'user')

    # Visibility: public repos shown to everyone; private only to the run's owner
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
    runs = qs[offset : offset + per_page]

    return RunListSchema(
        items=[
            RunListItemSchema(
                id=r.id,
                status=r.status,
                triggered_at=r.triggered_at.isoformat(),
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
                repo_url=r.repo.url,
                repo_owner=r.repo.owner,
                repo_name=r.repo.name,
                is_stale=r.repo.is_stale,
                is_private=r.repo.is_private,
                last_fetched_at=r.repo.last_fetched_at.isoformat() if r.repo.last_fetched_at else None,
                tags=r.result.get('classification', {}).get('tags', []) if r.result else [],
            )
            for r in runs
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get('/runs/{run_id}', response=RunStatusSchema)
def get_run(request, run_id: uuid.UUID):
    try:
        run = AnalysisRun.objects.select_related('repo', 'user').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private:
        if not request.user.is_authenticated or run.user != request.user:
            raise HttpError(403, 'Access denied')
    return RunStatusSchema(
        id=run.id,
        status=run.status,
        triggered_at=run.triggered_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        result=run.result,
        repo_url=run.repo.url,
        repo_owner=run.repo.owner,
        repo_name=run.repo.name,
        is_stale=run.repo.is_stale,
        last_fetched_at=run.repo.last_fetched_at.isoformat() if run.repo.last_fetched_at else None,
        auth_token_warning=run.repo.auth_token_warning,
    )


@router.post('/runs/{run_id}/retry', response=AnalyzeResponse)
def retry_run(request, run_id: uuid.UUID):
    """Force a fresh analysis regardless of cached SHA — testing only."""
    try:
        original = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    token = _resolve_token(request, None) or original.repo.auth_token or None
    user = request.user if request.user.is_authenticated else None
    run = AnalysisRun.objects.create(repo=original.repo, status='pending', user=user)
    task = analyze_repository.delay(str(run.id), pat=token)
    run.celery_task_id = task.id
    run.save(update_fields=['celery_task_id'])
    return AnalyzeResponse(run_id=run.id, status='pending', cached=False)


@router.get('/runs/{run_id}/timeline')
def get_timeline(request, run_id: uuid.UUID):
    try:
        run = AnalysisRun.objects.get(id=run_id, status='completed')
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found or not completed')
    result = run.result or {}
    commits = result.get('commits', {})
    deps = result.get('dependencies', {})
    return {
        'commit_frequency': commits.get('weekly_frequency', []),
        'monthly_frequency': commits.get('monthly_frequency', []),
        'contributor_churn': commits.get('contributor_churn', []),
        'dependency_count': deps.get('dependency_count', 0),
    }


class SlugRunSchema(Schema):
    run_id: uuid.UUID
    status: str


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


_BADGE_COLORS = {
    # project_health keys
    'thriving': '#4c1',
    'active': '#97ca00',
    'stable': '#dfb317',
    'declining': '#fe7d37',
    'abandoned': '#e05d44',
    # contribution_difficulty keys
    'very_easy': '#4c1',
    'easy': '#97ca00',
    'moderate': '#dfb317',
    'hard': '#fe7d37',
    'very_hard': '#e05d44',
}

_BADGE_NOT_ANALYZED = '#9f9f9f'


def _make_svg(label: str, value: str, color: str) -> str:
    lw = max(len(label) * 6 + 10, 90)
    vw = max(len(value) * 6 + 10, 60)
    tw = lw + vw
    lx = lw // 2
    vx = lw + vw // 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{tw}" height="20">'
        f'<linearGradient id="s" x2="0" y2="100%">'
        f'<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
        f'<stop offset="1" stop-opacity=".1"/></linearGradient>'
        f'<rect rx="3" width="{tw}" height="20" fill="#555"/>'
        f'<rect rx="3" x="{lw}" width="{vw}" height="20" fill="{color}"/>'
        f'<rect x="{lw}" width="4" height="20" fill="{color}"/>'
        f'<rect rx="3" width="{tw}" height="20" fill="url(#s)"/>'
        f'<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">'
        f'<text x="{lx}" y="15" fill="#010101" fill-opacity=".3">{label}</text>'
        f'<text x="{lx}" y="14">{label}</text>'
        f'<text x="{vx}" y="15" fill="#010101" fill-opacity=".3">{value}</text>'
        f'<text x="{vx}" y="14">{value}</text>'
        f'</g></svg>'
    )


class MyRepoSchema(Schema):
    full_name: str
    html_url: str
    private: bool


@router.get('/my-repos', response=list[MyRepoSchema])
def my_repos(request):
    if not request.user.is_authenticated:
        raise HttpError(401, 'Not authenticated')
    from allauth.socialaccount.models import SocialToken
    import requests as _requests
    social = SocialToken.objects.filter(
        account__user=request.user,
        account__provider='github',
    ).first()
    if not social:
        raise HttpError(403, 'GitHub not connected')
    resp = _requests.get(
        'https://api.github.com/user/repos',
        headers={
            'Authorization': f'Bearer {social.token}',
            'Accept': 'application/vnd.github+json',
        },
        params={'per_page': 100, 'sort': 'pushed', 'affiliation': 'owner,collaborator'},
        timeout=10,
    )
    if not resp.ok:
        raise HttpError(502, 'Failed to fetch repos from GitHub')
    return [
        MyRepoSchema(full_name=r['full_name'], html_url=r['html_url'], private=r['private'])
        for r in resp.json()
        if isinstance(r, dict)
    ]


class FeaturedRepoSchema(Schema):
    run_id: uuid.UUID
    repo_url: str
    repo_owner: str
    repo_name: str
    stars: Optional[int] = None
    health_label: Optional[str] = None
    health_key: Optional[str] = None
    primary_language: Optional[str] = None
    topics: list[str] = []
    github_description: Optional[str] = None


@router.get('/featured', response={200: Optional[FeaturedRepoSchema]})
def get_featured(request):
    from django.conf import settings as django_settings
    featured_url = getattr(django_settings, 'FEATURED_REPO_URL', '').strip()
    if not featured_url:
        return 200, None
    try:
        repo = Repository.objects.get(url=featured_url.rstrip('/'))
    except Repository.DoesNotExist:
        return 200, None
    if repo.is_private:
        return 200, None
    run = repo.runs.filter(status='completed').order_by('-triggered_at').first()
    if not run or not run.result:
        return 200, None
    meta = run.result.get('github_meta', {})
    health = run.result.get('classification', {}).get('project_health', {})
    return 200, FeaturedRepoSchema(
        run_id=run.id,
        repo_url=repo.url,
        repo_owner=repo.owner,
        repo_name=repo.name,
        stars=meta.get('stars'),
        health_label=health.get('label'),
        health_key=health.get('key'),
        primary_language=meta.get('primary_language'),
        topics=meta.get('topics', []),
        github_description=meta.get('github_description'),
    )


@router.get('/admin/stats')
def admin_stats(request):
    import os
    from django.conf import settings as django_settings
    if not request.user.is_staff:
        raise HttpError(403, 'Staff only')

    cache_dir = django_settings.REPO_CACHE_DIR
    cache_size_bytes = 0
    repo_clone_count = 0
    if os.path.isdir(cache_dir):
        for entry in os.scandir(cache_dir):
            if entry.is_dir():
                repo_clone_count += 1
                for root, dirs, files in os.walk(entry.path):
                    for f in files:
                        try:
                            cache_size_bytes += os.path.getsize(os.path.join(root, f))
                        except OSError:
                            pass

    from django.db.models import Count
    status_counts = dict(
        AnalysisRun.objects.values_list('status').annotate(c=Count('id')).values_list('status', 'c')
    )

    return {
        'total_repos': Repository.objects.count(),
        'total_runs': AnalysisRun.objects.count(),
        'queue_depth': status_counts.get('pending', 0) + status_counts.get('running', 0),
        'failed_runs': status_counts.get('failed', 0),
        'completed_runs': status_counts.get('completed', 0),
        'repo_clone_count': repo_clone_count,
        'cache_size_gb': round(cache_size_bytes / (1024 ** 3), 2),
    }


@router.get('/badge/{owner}/{name}.svg')
def repo_badge(request, owner: str, name: str):
    try:
        repo = Repository.objects.get(owner__iexact=owner, name__iexact=name)
    except Repository.DoesNotExist:
        svg = _make_svg('atlas insight', 'not found', _BADGE_NOT_ANALYZED)
        return HttpResponse(svg, content_type='image/svg+xml', status=404)

    if repo.is_private:
        svg = _make_svg('atlas insight', 'private', _BADGE_NOT_ANALYZED)
        return HttpResponse(svg, content_type='image/svg+xml', status=403)

    run = repo.runs.filter(status='completed').order_by('-triggered_at').first()
    if not run or not run.result:
        svg = _make_svg('atlas insight', 'not analyzed', _BADGE_NOT_ANALYZED)
        resp = HttpResponse(svg, content_type='image/svg+xml')
        resp['Cache-Control'] = 'max-age=300'
        return resp

    cls = run.result.get('classification', {})
    health = cls.get('project_health', {})
    label = 'atlas insight'
    value = health.get('label', 'analyzed')
    color = _BADGE_COLORS.get(health.get('key', ''), '#555')

    svg = _make_svg(label, value, color)
    resp = HttpResponse(svg, content_type='image/svg+xml')
    resp['Cache-Control'] = 'max-age=3600'
    return resp
