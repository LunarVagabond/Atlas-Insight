"""Meta endpoints: badge, card, featured, trending, spotlight, my-repos, favorites."""
import uuid
from typing import Optional

from django.http import HttpResponse
from django_ratelimit.decorators import ratelimit
from ninja import Router, Schema
from ninja.errors import HttpError

from .models import AnalysisRun, Repository, RepoOfTheWeek, UserFavorite

router = Router()


def _assert_not_limited(request):
    if getattr(request, 'limited', False):
        raise HttpError(429, 'Rate limit exceeded. Please try again later.')


_BADGE_COLORS = {
    'thriving': '#4c1',
    'active': '#97ca00',
    'stable': '#dfb317',
    'declining': '#fe7d37',
    'abandoned': '#e05d44',
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
    branch: str = '',
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
    branch_line = ''
    if branch:
        branch_escaped = _svg_escape(branch[:40])
        branch_line = f'<text x="18" y="104" font-family="{f}" font-size="10" fill="{muted}">@ {branch_escaped}</text>'
        pill_y, pill_text_y = 112, 127
    else:
        pill_y, pill_text_y = 100, 115
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" rx="10" fill="{bg}"/>'
        f'<rect width="{W}" height="{H}" rx="10" fill="none" stroke="{color}" stroke-width="1" stroke-opacity="0.35"/>'
        f'<rect width="4" height="{H}" rx="2" fill="{color}"/>'
        f'<text x="18" y="26" font-family="{f}" font-size="11" fill="{muted}">atlas insight</text>'
        f'<text x="{W - 16}" y="42" font-family="{f}" font-size="32" font-weight="700" fill="{color}" text-anchor="end">{score_str}</text>'
        f'<text x="{W - 16}" y="54" font-family="{f}" font-size="10" fill="{sub}" text-anchor="end">/10  OSS Score</text>'
        f'<line x1="18" y1="62" x2="{W - 16}" y2="62" stroke="{muted}" stroke-width="0.5" stroke-opacity="0.35"/>'
        f'<text x="18" y="90" font-family="{f}" font-size="18" font-weight="700" fill="{title}">{owner}/{name}</text>'
        f'{branch_line}'
        f'<rect x="18" y="{pill_y}" width="{pill_w}" height="22" rx="11" fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="1"/>'
        f'<text x="{pill_cx}" y="{pill_text_y}" font-family="{f}" font-size="11" font-weight="600" fill="{color}" text-anchor="middle">{health_label}</text>'
        f'<line x1="18" y1="130" x2="{W - 16}" y2="130" stroke="{muted}" stroke-width="0.5" stroke-opacity="0.35"/>'
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


def _spotlight_to_schema(spot: 'RepoOfTheWeek'):
    run = spot.repo.runs.filter(status='completed', branch='').order_by('-triggered_at').first()
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


class MyRepoSchema(Schema):
    full_name: str
    html_url: str
    private: bool


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
        branch=run.branch or '',
    )
    resp = HttpResponse(svg, content_type='image/svg+xml')
    resp['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=3600'
    return resp


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

    run = repo.runs.filter(status='completed', branch='').order_by('-triggered_at').first()
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
    run = repo.runs.filter(status='completed', branch='').order_by('-triggered_at').first()
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


@router.get('/spotlight/current', response={200: Optional[SpotlightSchema]})
def get_spotlight_current(request):
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
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
    per_page = min(per_page, 20)
    qs = RepoOfTheWeek.objects.select_related('repo').order_by('-week_start')
    total = qs.count()
    offset = (page - 1) * per_page
    spots = list(qs[offset: offset + per_page])
    items = []
    for spot in spots:
        run = spot.repo.runs.filter(status='completed', branch='').order_by('-triggered_at').first()
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
