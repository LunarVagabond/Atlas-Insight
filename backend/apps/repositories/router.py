import logging
import re
import uuid
from typing import Optional

from django.db.models import Q
from django.http import HttpResponse
from django_ratelimit.decorators import ratelimit
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.analysis.github_meta import fetch_contribution_data, fetch_latest_sha
from apps.analysis.tasks import analyze_repository

from .models import AnalysisRun, Repository, RepoOfTheWeek, UserFavorite, WebhookDelivery

logger = logging.getLogger(__name__)
router = Router(tags=['repositories'])


def _assert_not_limited(request):
    if getattr(request, 'limited', False):
        raise HttpError(429, 'Rate limit exceeded. Please try again later.')


def _resolve_api_token_user(request):
    """If request carries a valid Bearer token, return the associated user; else None."""
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


class AnalyzeRequest(Schema):
    url: str
    pat: Optional[str] = None
    webhook_url: Optional[str] = None
    notification_email: Optional[str] = None


RERUN_COOLDOWN_HOURS = 4


def _cooldown_until(repo) -> Optional[str]:
    """Return ISO timestamp when re-run is available, or None if available now."""
    from datetime import timedelta
    if not repo.last_analyzed_at:
        return None
    from django.utils import timezone
    cutoff = repo.last_analyzed_at + timedelta(hours=RERUN_COOLDOWN_HOURS)
    if timezone.now() < cutoff:
        return cutoff.isoformat()
    return None


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
    is_private: bool
    last_fetched_at: Optional[str]
    auth_token_warning: str
    cooldown_until: Optional[str] = None


class AnalyzeResponse(Schema):
    run_id: uuid.UUID
    status: str
    cached: bool


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

    user = request.user if request.user.is_authenticated else _resolve_api_token_user(request)
    run = AnalysisRun.objects.create(
        repo=repo, status='pending', user=user,
        webhook_url=payload.webhook_url or '',
        notification_email=payload.notification_email or '',
    )
    task = analyze_repository.delay(str(run.id), pat=token)
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
    from django.db.models import Exists, OuterRef, Subquery

    # Latest non-failed run per repo — failed runs are hidden from public listings
    latest_per_repo = AnalysisRun.objects.filter(
        repo=OuterRef('pk'),
        status__in=['completed', 'pending', 'running'],
    ).order_by('-triggered_at').values('id')[:1]
    latest_ids = Repository.objects.annotate(
        latest_id=Subquery(latest_per_repo)
    ).exclude(latest_id=None).values('latest_id')

    qs = AnalysisRun.objects.filter(pk__in=latest_ids).select_related('repo', 'user')

    # Annotate whether each run has a prior completed run for the same repo
    prev_run_exists = AnalysisRun.objects.filter(
        repo=OuterRef('repo'),
        status='completed',
        triggered_at__lt=OuterRef('triggered_at'),
    )
    qs = qs.annotate(has_previous_run=Exists(prev_run_exists))

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
    runs = list(qs[offset : offset + per_page])

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
        if not request.user.is_authenticated or run.user != request.user:
            raise HttpError(403, 'Access denied')
    if run.status == 'completed':
        Repository.objects.filter(pk=run.repo_id).update(view_count=F('view_count') + 1)
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
    is_super = request.user.is_authenticated and request.user.is_superuser
    if not is_super:
        cooldown = _cooldown_until(original.repo)
        if cooldown:
            raise HttpError(
                429,
                f'This repository was analyzed recently. Re-analysis available after {cooldown}.',
            )
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


def _svg_escape(text: str) -> str:
    return (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;')
    )


def _make_card_svg(
    owner: str, name: str, health_label: str, color: str,
    oss_score, total_commits: int, total_files: int, contributors: int,
    theme: str = 'dark',
) -> str:
    owner = _svg_escape(owner[:22])
    name = _svg_escape(name[:30])
    health_label = _svg_escape(health_label)
    score_str = str(oss_score) if oss_score is not None else '—'
    pill_w = max(len(health_label) * 7 + 24, 72)
    pill_cx = 18 + pill_w // 2
    stats = f'{total_commits:,} commits  ·  {total_files:,} files  ·  {contributors} contributor{"s" if contributors != 1 else ""}'
    f = 'DejaVu Sans,Verdana,Geneva,sans-serif'
    W, H = 480, 150
    if theme == 'light':
        bg, title, sub, muted = '#ffffff', '#24292f', '#57606a', '#8c959f'
    else:
        bg, title, sub, muted = '#0d1117', '#e6edf3', '#8b949e', '#6e7681'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" rx="10" fill="{bg}"/>'
        f'<rect width="{W}" height="{H}" rx="10" fill="none" stroke="{color}" stroke-width="1" stroke-opacity="0.35"/>'
        f'<rect width="4" height="{H}" rx="2" fill="{color}"/>'
        # top-left: brand label
        f'<text x="18" y="26" font-family="{f}" font-size="11" fill="{muted}">atlas insight</text>'
        # top-right: score (big) + /10 label
        f'<text x="{W - 16}" y="42" font-family="{f}" font-size="32" font-weight="700" fill="{color}" text-anchor="end">{score_str}</text>'
        f'<text x="{W - 16}" y="54" font-family="{f}" font-size="10" fill="{sub}" text-anchor="end">/10  OSS Score</text>'
        # divider 1
        f'<line x1="18" y1="62" x2="{W - 16}" y2="62" stroke="{muted}" stroke-width="0.5" stroke-opacity="0.35"/>'
        # repo name
        f'<text x="18" y="90" font-family="{f}" font-size="18" font-weight="700" fill="{title}">{owner}/{name}</text>'
        # health pill
        f'<rect x="18" y="100" width="{pill_w}" height="22" rx="11" fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="1"/>'
        f'<text x="{pill_cx}" y="115" font-family="{f}" font-size="11" font-weight="600" fill="{color}" text-anchor="middle">{health_label}</text>'
        # divider 2
        f'<line x1="18" y1="130" x2="{W - 16}" y2="130" stroke="{muted}" stroke-width="0.5" stroke-opacity="0.35"/>'
        # stats
        f'<text x="18" y="144" font-family="{f}" font-size="10" fill="{muted}">{stats}</text>'
        f'</svg>'
    )


def _make_svg(label: str, value: str, color: str) -> str:
    label = _svg_escape(label)
    value = _svg_escape(value)
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


@router.get('/runs/{run_id}/card.svg')
@ratelimit(key='ip', rate='30/m', method='GET', block=False)
def run_card(request, run_id: uuid.UUID, theme: str = 'dark'):
    if getattr(request, 'limited', False):
        return HttpResponse('Rate limit exceeded', status=429)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        return HttpResponse('Not found', status=404)
    if run.status != 'completed' or not run.result:
        return HttpResponse('Not ready', status=404)

    res = run.result
    cls = res.get('classification', {})
    health = cls.get('project_health', {})
    oss = res.get('oss_score', {})
    oss_score = oss.get('score') if isinstance(oss, dict) else None
    commits = res.get('commits', {})
    structure = res.get('structure', {})
    card_theme = theme if theme in ('dark', 'light') else 'dark'

    svg = _make_card_svg(
        owner=run.repo.owner,
        name=run.repo.name,
        health_label=health.get('label', 'analyzed'),
        color=_BADGE_COLORS.get(health.get('key', ''), '#555'),
        oss_score=oss_score,
        total_commits=commits.get('total_commits', 0),
        total_files=structure.get('total_files', 0),
        contributors=commits.get('total_contributors', 0),
        theme=card_theme,
    )
    resp = HttpResponse(svg, content_type='image/svg+xml')
    resp['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=3600'
    return resp


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


class TrendingRepoSchema(Schema):
    run_id: uuid.UUID
    repo_url: str
    repo_owner: str
    repo_name: str
    analysis_count: int
    health_label: Optional[str] = None
    health_key: Optional[str] = None
    primary_language: Optional[str] = None
    stars: Optional[int] = None


@router.get('/trending', response=list[TrendingRepoSchema])
@ratelimit(key='user_or_ip', rate='60/h', method='GET', block=False)
def trending(request):
    _assert_not_limited(request)
    from datetime import timedelta

    from django.db.models import Count
    from django.utils import timezone

    since = timezone.now() - timedelta(days=7)
    repo_counts = (
        AnalysisRun.objects
        .filter(status='completed', triggered_at__gte=since, repo__is_private=False)
        .values('repo_id')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    result = []
    for rc in repo_counts:
        run = (
            AnalysisRun.objects
            .filter(repo_id=rc['repo_id'], status='completed')
            .select_related('repo')
            .order_by('-triggered_at')
            .first()
        )
        if not run:
            continue
        meta = run.result.get('github_meta', {}) if run.result else {}
        health = run.result.get('classification', {}).get('project_health', {}) if run.result else {}
        result.append(TrendingRepoSchema(
            run_id=run.id,
            repo_url=run.repo.url,
            repo_owner=run.repo.owner,
            repo_name=run.repo.name,
            analysis_count=rc['count'],
            health_label=health.get('label'),
            health_key=health.get('key'),
            primary_language=meta.get('primary_language'),
            stars=meta.get('stars'),
        ))
    return result


class SpotlightSchema(Schema):
    run_id: uuid.UUID
    repo_url: str
    repo_owner: str
    repo_name: str
    week_start: str
    stars: Optional[int] = None
    health_label: Optional[str] = None
    health_key: Optional[str] = None
    primary_language: Optional[str] = None
    topics: list[str] = []
    github_description: Optional[str] = None
    pick_number: int


class SpotlightItemSchema(Schema):
    week_start: str
    repo_url: str
    repo_owner: str
    repo_name: str
    run_id: Optional[uuid.UUID] = None
    health_label: Optional[str] = None
    health_key: Optional[str] = None
    primary_language: Optional[str] = None
    stars: Optional[int] = None
    pick_number: int


class SpotlightHistorySchema(Schema):
    items: list[SpotlightItemSchema]
    total: int
    page: int
    per_page: int


def _spotlight_to_schema(spot: 'RepoOfTheWeek') -> Optional[SpotlightSchema]:
    run = spot.repo.runs.filter(status='completed').order_by('-triggered_at').first()
    if not run or not run.result:
        return None
    meta = run.result.get('github_meta', {})
    health = run.result.get('classification', {}).get('project_health', {})
    return SpotlightSchema(
        run_id=run.id,
        repo_url=spot.repo.url,
        repo_owner=spot.repo.owner,
        repo_name=spot.repo.name,
        week_start=spot.week_start.isoformat(),
        stars=meta.get('stars'),
        health_label=health.get('label'),
        health_key=health.get('key'),
        primary_language=meta.get('primary_language'),
        topics=meta.get('topics', []),
        github_description=meta.get('github_description'),
        pick_number=spot.pick_number,
    )


@router.get('/spotlight/current', response={200: Optional[SpotlightSchema]})
def get_spotlight_current(request):
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    # Try current week first, fall back to most recent pick if task hasn't run yet
    spot = (
        RepoOfTheWeek.objects.select_related('repo').filter(week_start=week_start).first()
        or RepoOfTheWeek.objects.select_related('repo').order_by('-week_start').first()
    )
    if not spot:
        return 200, None
    schema = _spotlight_to_schema(spot)
    return 200, schema


@router.get('/spotlight/history', response=SpotlightHistorySchema)
def get_spotlight_history(request, page: int = 1, per_page: int = 20):
    qs = RepoOfTheWeek.objects.select_related('repo').order_by('-week_start')
    total = qs.count()
    offset = (page - 1) * per_page
    spots = list(qs[offset: offset + per_page])
    items = []
    for spot in spots:
        run = spot.repo.runs.filter(status='completed').order_by('-triggered_at').first()
        meta = run.result.get('github_meta', {}) if run and run.result else {}
        cls = run.result.get('classification', {}) if run and run.result else {}
        health = cls.get('project_health', {})
        items.append(SpotlightItemSchema(
            week_start=spot.week_start.isoformat(),
            repo_url=spot.repo.url,
            repo_owner=spot.repo.owner,
            repo_name=spot.repo.name,
            run_id=run.id if run else None,
            health_label=health.get('label'),
            health_key=health.get('key'),
            primary_language=meta.get('primary_language'),
            stars=meta.get('stars'),
            pick_number=spot.pick_number,
        ))
    return SpotlightHistorySchema(items=items, total=total, page=page, per_page=per_page)


def _jit_token(run: AnalysisRun) -> str:
    from django.conf import settings as _s
    return run.repo.auth_token or getattr(_s, 'GITHUB_TOKEN', '') or ''


def _jit_headers(token: str) -> dict:
    h = {'Accept': 'application/vnd.github+json'}
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


@router.get('/runs/{run_id}/issues')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_run_issues(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_issues'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    data = fetch_contribution_data(run.repo.owner, run.repo.name, _jit_headers(token))
    issues = data['issues'] if data else []
    cache.set(cache_key, issues, 900)
    return issues


@router.get('/runs/{run_id}/prs')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_run_prs(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_prs'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    data = fetch_contribution_data(run.repo.owner, run.repo.name, _jit_headers(token))
    pr_refs = data['pr_issue_refs'] if data else []
    result = {
        'pr_issue_refs': pr_refs,
        'open_prs': run.result.get('github_meta', {}).get('open_prs', 0) if run.result else 0,
    }
    cache.set(cache_key, result, 900)
    return result


def _compute_run_diff(curr: dict, prev: dict, prev_run_id, prev_triggered_at) -> dict:
    curr_h = {h['signal']: h for h in curr.get('heuristics', [])}
    prev_h = {h['signal']: h for h in prev.get('heuristics', [])}
    heuristic_deltas = []
    for signal, ch in curr_h.items():
        ph = prev_h.get(signal)
        if ph:
            delta = ch['score'] - ph['score']
            heuristic_deltas.append({
                'signal': signal,
                'label': ch['label'],
                'before': ph['score'],
                'after': ch['score'],
                'delta': delta,
                'direction': 'up' if delta > 2 else 'down' if delta < -2 else 'same',
            })

    curr_dep_names = {d['name'] for d in curr.get('dependencies', {}).get('dependencies', [])}
    prev_dep_names = {d['name'] for d in prev.get('dependencies', {}).get('dependencies', [])}

    curr_struct = curr.get('structure', {})
    prev_struct = prev.get('structure', {})
    curr_graph = curr.get('graph', {})
    prev_graph = prev.get('graph', {})
    curr_cls = curr.get('classification', {})
    prev_cls = prev.get('classification', {})

    def cls_delta(key):
        c = curr_cls.get(key, {})
        p = prev_cls.get(key, {})
        if not c or not p:
            return None
        return {
            'before_label': p.get('label'),
            'after_label': c.get('label'),
            'delta': c.get('score', 0) - p.get('score', 0),
            'changed': c.get('key') != p.get('key'),
        }

    added_deps = sorted(curr_dep_names - prev_dep_names)[:20]
    removed_deps = sorted(prev_dep_names - curr_dep_names)[:20]

    return {
        'available': True,
        'previous_run_id': str(prev_run_id),
        'previous_triggered_at': prev_triggered_at.isoformat(),
        'heuristics': heuristic_deltas,
        'dependencies': {
            'added': added_deps,
            'removed': removed_deps,
            'added_count': len(curr_dep_names - prev_dep_names),
            'removed_count': len(prev_dep_names - curr_dep_names),
        },
        'contributors': {
            'before': prev.get('commits', {}).get('total_contributors', 0),
            'after': curr.get('commits', {}).get('total_contributors', 0),
            'delta': curr.get('commits', {}).get('total_contributors', 0) - prev.get('commits', {}).get('total_contributors', 0),
        },
        'graph': {
            'nodes_before': prev_graph.get('node_count', 0),
            'nodes_after': curr_graph.get('node_count', 0),
            'nodes_delta': curr_graph.get('node_count', 0) - prev_graph.get('node_count', 0),
            'god_modules_before': len(prev_graph.get('god_modules', [])),
            'god_modules_after': len(curr_graph.get('god_modules', [])),
            'god_modules_delta': len(curr_graph.get('god_modules', [])) - len(prev_graph.get('god_modules', [])),
        },
        'structure': {
            'files_before': prev_struct.get('total_files', 0),
            'files_after': curr_struct.get('total_files', 0),
            'files_delta': curr_struct.get('total_files', 0) - prev_struct.get('total_files', 0),
            'test_ratio_before': round(prev_struct.get('test_ratio', 0), 3),
            'test_ratio_after': round(curr_struct.get('test_ratio', 0), 3),
        },
        'classification': {
            'project_health': cls_delta('project_health'),
            'contribution_difficulty': cls_delta('contribution_difficulty'),
            'documentation_grade': cls_delta('documentation_grade'),
            'code_complexity': cls_delta('code_complexity'),
        },
    }


@router.get('/runs/{run_id}/diff')
@ratelimit(key='user_or_ip', rate='60/h', method='GET', block=False)
def get_run_diff(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        return {'available': False}

    prev_run = (
        AnalysisRun.objects
        .filter(repo=run.repo, status='completed', triggered_at__lt=run.triggered_at)
        .exclude(id=run.id)
        .order_by('-triggered_at')
        .first()
    )
    if not prev_run or not prev_run.result:
        return {'available': False}

    return _compute_run_diff(run.result, prev_run.result, prev_run.id, prev_run.triggered_at)


class SimilarRunOut(Schema):
    run_id: str
    owner: str
    name: str
    repo_url: str
    oss_score: float
    health_key: str
    primary_language: Optional[str]
    stars: int


@router.get('/runs/{run_id}/similar', response=list[SimilarRunOut])
@ratelimit(key='user_or_ip', rate='60/h', method='GET', block=False)
def get_similar_runs(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        return []

    lang = (run.result.get('github_meta') or {}).get('primary_language')
    score = (run.result.get('oss_score') or {}).get('score', 5)

    qs = AnalysisRun.objects.select_related('repo').filter(
        status='completed',
        repo__is_private=False,
    ).exclude(repo=run.repo).order_by('-completed_at')

    if lang:
        qs = qs.filter(result__github_meta__primary_language=lang)

    results = []
    for candidate in qs[:50]:
        if not candidate.result:
            continue
        cand_score = (candidate.result.get('oss_score') or {}).get('score', 5)
        if abs(cand_score - score) > 2:
            continue
        health_key = (
            (candidate.result.get('classification') or {})
            .get('project_health', {})
            .get('key', '')
        )
        stars = (candidate.result.get('github_meta') or {}).get('stars', 0)
        results.append(SimilarRunOut(
            run_id=str(candidate.id),
            owner=candidate.repo.owner,
            name=candidate.repo.name,
            repo_url=candidate.repo.url,
            oss_score=round(cand_score, 1),
            health_key=health_key,
            primary_language=lang,
            stars=stars,
        ))
        if len(results) >= 5:
            break

    return results


@router.get('/runs/{run_id}/file-history')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_file_history(request, run_id: uuid.UUID, path: str = ''):
    _assert_not_limited(request)
    import hashlib
    import re as _re
    import requests as _requests

    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if not path:
        raise HttpError(422, 'path parameter required')

    from django.core.cache import cache
    path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
    cache_key = f'jit_{run_id}_fh_{path_hash}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    headers = _jit_headers(token)
    url = f'https://api.github.com/repos/{run.repo.owner}/{run.repo.name}/commits'
    resp = _requests.get(url, headers=headers, params={'path': path, 'per_page': 10}, timeout=10)
    if not resp.ok:
        raise HttpError(502, 'Failed to fetch file history from GitHub')

    commits = []
    for c in resp.json():
        if not isinstance(c, dict):
            continue
        message = c.get('commit', {}).get('message', '').split('\n')[0][:120]
        refs = [int(m) for m in _re.findall(r'#(\d+)', message)][:5]
        commits.append({
            'sha': c['sha'][:7],
            'full_sha': c['sha'],
            'message': message,
            'date': c.get('commit', {}).get('author', {}).get('date', ''),
            'author': c.get('commit', {}).get('author', {}).get('name', ''),
            'url': c.get('html_url', ''),
            'issue_refs': refs,
        })

    result = {'path': path, 'commits': commits}
    cache.set(cache_key, result, 900)
    return result


@router.post('/repos/{repo_id}/favorite', response={200: None})
@ratelimit(key='user_or_ip', rate='60/h', method='POST', block=False)
def add_favorite(request, repo_id: uuid.UUID):
    _assert_not_limited(request)
    if not request.user.is_authenticated:
        raise HttpError(403, 'Authentication required')
    try:
        repo = Repository.objects.get(id=repo_id)
    except Repository.DoesNotExist:
        raise HttpError(404, 'Repository not found')
    UserFavorite.objects.get_or_create(user=request.user, repo=repo)
    return 200, None


@router.delete('/repos/{repo_id}/favorite', response={204: None})
@ratelimit(key='user_or_ip', rate='60/h', method='DELETE', block=False)
def remove_favorite(request, repo_id: uuid.UUID):
    _assert_not_limited(request)
    if not request.user.is_authenticated:
        raise HttpError(403, 'Authentication required')
    UserFavorite.objects.filter(user=request.user, repo__id=repo_id).delete()
    return 204, None


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


@router.get('/runs/{run_id}/vulnerabilities')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_run_vulnerabilities(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    import requests as _requests

    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        return {'checked': 0, 'vulnerable': []}

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_vulns'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    deps = run.result.get('dependencies', {}).get('dependencies', [])
    queries = []
    for dep in deps:
        name = dep.get('name', '')
        version = dep.get('version', '')
        ecosystem = dep.get('ecosystem', '')
        if not name or not version or not ecosystem:
            continue
        # OSV ecosystem names
        osv_eco = {'npm': 'npm', 'pip': 'PyPI', 'cargo': 'crates.io', 'gem': 'RubyGems'}.get(ecosystem, ecosystem)
        queries.append({'package': {'name': name, 'ecosystem': osv_eco}, 'version': version})

    if not queries:
        result = {'checked': 0, 'vulnerable': []}
        cache.set(cache_key, result, 900)
        return result

    try:
        resp = _requests.post(
            'https://api.osv.dev/v1/querybatch',
            json={'queries': queries},
            timeout=15,
        )
        resp.raise_for_status()
        batch_results = resp.json().get('results', [])
    except Exception:
        raise HttpError(502, 'Failed to reach OSV vulnerability database')

    from apps.analysis.vuln_scan import _enrich_vulns

    raw_vulns = []
    all_ids = []
    for query, batch_result in zip(queries, batch_results):
        for v in batch_result.get('vulns', []):
            vid = v.get('id', '')
            if not vid:
                continue
            raw_vulns.append({'query': query, 'id': vid})
            all_ids.append(vid)

    details = _enrich_vulns(all_ids)

    vulnerable = []
    for item in raw_vulns:
        vid = item['id']
        q = item['query']
        d = details.get(vid, {})
        vulnerable.append({
            'name': q['package']['name'],
            'version': q['version'],
            'ecosystem': q['package']['ecosystem'],
            'vuln_id': vid,
            'summary': d.get('summary', ''),
            'severity': d.get('severity'),
            'severity_score': d.get('severity_score'),
            'url': f'https://osv.dev/vulnerability/{vid}',
        })

    result = {'checked': len(queries), 'vulnerable': vulnerable}
    cache.set(cache_key, result, 900)
    return result


@router.get('/admin/rate-limit')
def admin_rate_limit(request):
    """Live GitHub API rate limit status for the server token."""
    import requests as _requests
    from django.conf import settings as django_settings

    if not request.user.is_staff:
        raise HttpError(403, 'Staff only')
    token = getattr(django_settings, 'GITHUB_TOKEN', '')
    headers = {'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        resp = _requests.get('https://api.github.com/rate_limit', headers=headers, timeout=8)
        resp.raise_for_status()
        data = resp.json().get('resources', {})
    except Exception:
        raise HttpError(502, 'Failed to fetch rate limit from GitHub')

    def fmt(r: dict) -> dict:
        from datetime import datetime, timezone as _tz
        reset_at = datetime.fromtimestamp(r.get('reset', 0), tz=_tz.utc).isoformat() if r.get('reset') else None
        return {'limit': r.get('limit', 0), 'remaining': r.get('remaining', 0), 'reset_at': reset_at}

    return {
        'core': fmt(data.get('core', {})),
        'search': fmt(data.get('search', {})),
        'graphql': fmt(data.get('graphql', {})),
    }


class WatchedRepoSchema(Schema):
    id: uuid.UUID
    url: str
    owner: str
    name: str
    is_stale: bool
    last_analyzed_at: Optional[str] = None


@router.get('/watched', response=list[WatchedRepoSchema])
def list_watched(request):
    if not request.user.is_staff:
        raise HttpError(403, 'Staff only')
    repos = Repository.objects.filter(is_watched=True).order_by('owner', 'name')
    return [
        WatchedRepoSchema(
            id=r.id,
            url=r.url,
            owner=r.owner,
            name=r.name,
            is_stale=r.is_stale,
            last_analyzed_at=r.last_analyzed_at.isoformat() if r.last_analyzed_at else None,
        )
        for r in repos
    ]


@router.post('/repos/{repo_id}/watch', response={200: None})
def watch_repo(request, repo_id: uuid.UUID):
    if not request.user.is_superuser:
        raise HttpError(403, 'Superuser only')
    try:
        repo = Repository.objects.get(id=repo_id)
    except Repository.DoesNotExist:
        raise HttpError(404, 'Repository not found')
    repo.is_watched = True
    repo.save(update_fields=['is_watched'])
    return 200, None


@router.delete('/repos/{repo_id}/watch', response={204: None})
def unwatch_repo(request, repo_id: uuid.UUID):
    if not request.user.is_superuser:
        raise HttpError(403, 'Superuser only')
    try:
        repo = Repository.objects.get(id=repo_id)
    except Repository.DoesNotExist:
        raise HttpError(404, 'Repository not found')
    repo.is_watched = False
    repo.save(update_fields=['is_watched'])
    return 204, None


@router.post('/webhooks/github', response={200: None})
def github_webhook(request):
    import hashlib
    import hmac
    import json

    from django.conf import settings as django_settings
    from django.core.cache import cache

    secret = getattr(django_settings, 'GITHUB_WEBHOOK_SECRET', '')
    if not secret and not getattr(django_settings, 'DEBUG', False):
        raise HttpError(500, 'Webhook secret not configured')

    sig_header = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
    if secret:
        body = request.body
        expected = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            raise HttpError(400, 'Invalid signature')

    raw_delivery_id = request.META.get('HTTP_X_GITHUB_DELIVERY', '')
    if raw_delivery_id:
        dedup_key = f'gh_delivery_{raw_delivery_id}'
        if cache.get(dedup_key):
            return 200, None
        cache.set(dedup_key, 1, 3600)

    try:
        payload = json.loads(request.body)
    except Exception:
        raise HttpError(400, 'Invalid JSON')

    event_type = request.META.get('HTTP_X_GITHUB_EVENT', '')
    repo_html_url = payload.get('repository', {}).get('html_url', '')
    delivery_id = raw_delivery_id or f'no-id-{uuid.uuid4()}'

    delivery = WebhookDelivery.objects.create(
        delivery_id=delivery_id,
        event_type=event_type,
        repo_url=repo_html_url,
        triggered_reanalysis=False,
        raw_payload=payload,
    )

    if event_type != 'push':
        return 200, None

    if not repo_html_url:
        return 200, None

    try:
        repo = Repository.objects.get(url=repo_html_url.rstrip('/'))
    except Repository.DoesNotExist:
        return 200, None

    token = repo.auth_token or None
    run = AnalysisRun.objects.create(repo=repo, status='pending')
    from apps.analysis.tasks import analyze_repository
    task = analyze_repository.delay(str(run.id), pat=token)
    run.celery_task_id = task.id
    run.save(update_fields=['celery_task_id'])

    delivery.triggered_reanalysis = True
    delivery.run = run
    delivery.save(update_fields=['triggered_reanalysis', 'run'])

    logger.info('Webhook triggered re-analysis for %s/%s (run %s)', repo.owner, repo.name, run.id)
    return 200, None


@router.get('/badge/{owner}/{name}.svg')
@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def repo_badge(request, owner: str, name: str):
    if getattr(request, 'limited', False):
        return HttpResponse('Rate limit exceeded', status=429)
    try:
        repo = Repository.objects.get(owner__iexact=owner, name__iexact=name)
    except Repository.DoesNotExist:
        svg = _make_svg('atlas insight', 'not found', _BADGE_NOT_ANALYZED)
        return HttpResponse(svg, content_type='image/svg+xml', status=404)

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
    resp['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=3600'
    return resp
