import logging
import re
import uuid
from typing import Optional

from django.db.models import Q
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
    last_fetched_at: Optional[str]


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
            return social.token
    return None


@router.post('/analyze', response=AnalyzeResponse)
def analyze(request, payload: AnalyzeRequest):
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

    token = _resolve_token(request, payload.pat)
    latest_sha = fetch_latest_sha(owner, name, token=token)

    if latest_sha and latest_sha == repo.last_commit_sha:
        latest_run = repo.runs.filter(status='completed').order_by('-triggered_at').first()
        if latest_run:
            return AnalyzeResponse(run_id=latest_run.id, status='completed', cached=True)

    user = request.user if request.user.is_authenticated else None
    run = AnalysisRun.objects.create(repo=repo, status='pending', user=user)
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
                last_fetched_at=r.repo.last_fetched_at.isoformat() if r.repo.last_fetched_at else None,
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
    )


@router.post('/runs/{run_id}/retry', response=AnalyzeResponse)
def retry_run(request, run_id: uuid.UUID):
    """Force a fresh analysis regardless of cached SHA — testing only."""
    try:
        original = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    token = _resolve_token(request, None)
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
