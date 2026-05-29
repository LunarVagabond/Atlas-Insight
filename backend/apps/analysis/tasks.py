import logging

from celery import shared_task
from django.utils import timezone

from apps.repositories.models import AnalysisRun

from .classifications import classify_repo
from .commit_analysis import analyze_commits
from .dep_report import analyze_dependencies
from .git_ops import clone_or_fetch
from .github_meta import fetch_github_meta
from .graph_analysis import analyze_graph
from .heuristics import compute_heuristics
from .import_parser import parse_imports
from .project_structure import analyze_structure
from .readme_parser import parse_readme
from .security_scan import scan_security

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def analyze_repository(self, run_id: str, pat: str | None = None):
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        logger.error('AnalysisRun %s not found', run_id)
        return

    run.status = 'running'
    run.save(update_fields=['status'])
    logger.info('Starting analysis for run %s: %s', run_id, run.repo.url)

    try:
        repo_obj, sha, fetched_at = clone_or_fetch(run.repo.url, pat=pat)
        repo_dir = repo_obj.working_dir

        commits = analyze_commits(repo_obj)
        edges = parse_imports(repo_dir)
        graph = analyze_graph(edges)
        deps = analyze_dependencies(repo_dir)
        readme = parse_readme(repo_dir)
        structure = analyze_structure(repo_obj, repo_dir, deps=deps)
        security = scan_security(repo_obj, repo_dir)
        github_meta = fetch_github_meta(run.repo.owner, run.repo.name, token=pat)

        signals = compute_heuristics(commits, graph, deps, readme, structure, security)
        classification = classify_repo(
            commits, graph, deps, readme, structure, security, github_meta
        )

        run.result = {
            'commits': commits,
            'graph': graph,
            'dependencies': deps,
            'heuristics': signals,
            'readme': readme,
            'structure': structure,
            'security': security,
            'github_meta': github_meta,
            'classification': classification,
        }
        run.status = 'completed'

        repo = run.repo
        repo.last_commit_sha = sha
        repo.last_analyzed_at = timezone.now()
        repo.last_fetched_at = fetched_at
        repo.is_stale = False
        repo.save(update_fields=['last_commit_sha', 'last_analyzed_at', 'last_fetched_at', 'is_stale'])
        logger.info('Analysis completed for run %s', run_id)

    except Exception as exc:
        logger.exception('Analysis failed for run %s', run_id)
        run.status = 'failed'
        run.result = {'error': str(exc)}

    run.completed_at = timezone.now()
    run.save(update_fields=['status', 'result', 'completed_at'])


@shared_task
def check_stale_repos():
    from datetime import timedelta

    from django.conf import settings

    from apps.repositories.models import Repository

    from .github_meta import fetch_latest_sha

    stale_threshold = timezone.now() - timedelta(days=settings.STALE_AFTER_DAYS)
    repos = Repository.objects.exclude(last_commit_sha='')
    updated = 0
    for repo in repos:
        if repo.is_stale:
            continue
        stale = False
        # Time-based: not fetched within STALE_AFTER_DAYS
        if repo.last_fetched_at and repo.last_fetched_at < stale_threshold:
            stale = True
        # SHA-based: new commits on GitHub
        if not stale:
            try:
                latest = fetch_latest_sha(repo.owner, repo.name)
                if latest and latest != repo.last_commit_sha:
                    stale = True
            except Exception:
                logger.warning('Stale SHA check failed for %s/%s', repo.owner, repo.name)
        if stale:
            repo.is_stale = True
            repo.save(update_fields=['is_stale'])
            updated += 1
    logger.info('Stale check complete: %d repos marked stale', updated)
