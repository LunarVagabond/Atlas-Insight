import logging
import re

import requests
from django.conf import settings
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.analysis.tasks import analyze_repository

from .models import AnalysisRun, Repository

logger = logging.getLogger(__name__)
router = Router(tags=['repositories'])

GITHUB_URL_RE = re.compile(
    r'^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$'
)


class AnalyzeRequest(Schema):
    url: str


class RunStatusSchema(Schema):
    id: int
    status: str
    triggered_at: str
    completed_at: str | None
    result: dict | None


class AnalyzeResponse(Schema):
    run_id: int
    status: str
    cached: bool


def _fetch_latest_sha(owner: str, name: str) -> str | None:
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if settings.GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {settings.GITHUB_TOKEN}'
    try:
        resp = requests.get(
            f'https://api.github.com/repos/{owner}/{name}/commits',
            params={'per_page': 1},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]['sha']
    except Exception:
        logger.warning('Failed to fetch latest SHA for %s/%s', owner, name)
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

    latest_sha = _fetch_latest_sha(owner, name)

    if latest_sha and latest_sha == repo.last_commit_sha:
        latest_run = repo.runs.filter(status='completed').order_by('-triggered_at').first()
        if latest_run:
            return AnalyzeResponse(run_id=latest_run.id, status='completed', cached=True)

    run = AnalysisRun.objects.create(repo=repo, status='pending')
    task = analyze_repository.delay(run.id)
    run.celery_task_id = task.id
    run.save(update_fields=['celery_task_id'])

    return AnalyzeResponse(run_id=run.id, status='pending', cached=False)


@router.get('/runs/{run_id}', response=RunStatusSchema)
def get_run(request, run_id: int):
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    return RunStatusSchema(
        id=run.id,
        status=run.status,
        triggered_at=run.triggered_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        result=run.result,
    )


@router.get('/runs/{run_id}/timeline')
def get_timeline(request, run_id: int):
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
