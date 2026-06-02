"""Admin + webhook endpoints: stats, rate-limit, pick-spotlight, watched, github-webhook."""
import logging
import uuid
from typing import Optional

from django_ratelimit.decorators import ratelimit
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.analysis.tasks import analyze_repository
from .models import AnalysisRun, Repository, RepoOfTheWeek, WebhookDelivery

logger = logging.getLogger(__name__)
router = Router()


class WatchedRepoSchema(Schema):
    id: uuid.UUID
    url: str
    owner: str
    name: str
    is_stale: bool
    last_analyzed_at: Optional[str] = None


@router.get('/admin/stats')
@ratelimit(key='user', rate='30/h', method='GET', block=True)
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


@router.get('/admin/rate-limit')
@ratelimit(key='user', rate='30/h', method='GET', block=True)
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


@router.post('/admin/pick-spotlight')
@ratelimit(key='user', rate='10/h', method='POST', block=True)
def admin_pick_spotlight(request):
    import random
    from datetime import date, timedelta
    from django.db.models import Count

    if not request.user.is_superuser:
        raise HttpError(403, 'Superuser only')

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    RepoOfTheWeek.objects.filter(week_start=week_start).delete()

    eligible = list(
        Repository.objects.filter(is_private=False, runs__status='completed').distinct()
    )
    if not eligible:
        raise HttpError(409, 'No eligible public repos with completed analyses')

    pick_counts = dict(
        RepoOfTheWeek.objects.filter(repo__in=eligible)
        .values('repo_id')
        .annotate(n=Count('id'))
        .values_list('repo_id', 'n')
    )
    min_picks = min((pick_counts.get(r.pk, 0) for r in eligible), default=0)
    candidates = [r for r in eligible if pick_counts.get(r.pk, 0) <= min_picks]
    weights = [r.scan_count * 0.6 + r.view_count * 0.4 + 1 for r in candidates]
    chosen = random.choices(candidates, weights=weights, k=1)[0]
    current_picks = pick_counts.get(chosen.pk, 0)

    RepoOfTheWeek.objects.create(
        repo=chosen,
        week_start=week_start,
        pick_number=current_picks + 1,
    )
    logger.info('Admin manually picked Repo of Week: %s/%s', chosen.owner, chosen.name)
    return {
        'owner': chosen.owner,
        'name': chosen.name,
        'url': chosen.url,
        'week_start': week_start.isoformat(),
        'pick_number': current_picks + 1,
    }


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

    run = AnalysisRun.objects.create(repo=repo, status='pending')
    task = analyze_repository.delay(str(run.id))
    run.celery_task_id = task.id
    run.save(update_fields=['celery_task_id'])

    delivery.triggered_reanalysis = True
    delivery.run = run
    delivery.save(update_fields=['triggered_reanalysis', 'run'])

    logger.info('Webhook triggered re-analysis for %s/%s (run %s)', repo.owner, repo.name, run.id)
    return 200, None
