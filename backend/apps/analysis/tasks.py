import logging

from celery import shared_task
from django.utils import timezone

from apps.repositories.models import AnalysisRun

from .commit_analysis import analyze_commits
from .dep_report import analyze_dependencies
from .git_ops import clone_or_fetch
from .graph_analysis import analyze_graph
from .heuristics import compute_heuristics
from .import_parser import parse_imports

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def analyze_repository(self, run_id: int):
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        logger.error('AnalysisRun %s not found', run_id)
        return

    run.status = 'running'
    run.save(update_fields=['status'])
    logger.info('Starting analysis for run %s: %s', run_id, run.repo.url)

    try:
        repo_obj, sha = clone_or_fetch(run.repo.url)
        commits = analyze_commits(repo_obj)
        edges = parse_imports(repo_obj.working_dir)
        graph = analyze_graph(edges)
        deps = analyze_dependencies(repo_obj.working_dir)
        signals = compute_heuristics(commits, graph, deps)

        run.result = {
            'commits': commits,
            'graph': graph,
            'dependencies': deps,
            'heuristics': signals,
        }
        run.status = 'completed'

        repo = run.repo
        repo.last_commit_sha = sha
        repo.last_analyzed_at = timezone.now()
        repo.save(update_fields=['last_commit_sha', 'last_analyzed_at'])
        logger.info('Analysis completed for run %s', run_id)
    except Exception as exc:
        logger.exception('Analysis failed for run %s', run_id)
        run.status = 'failed'
        run.result = {'error': str(exc)}

    run.completed_at = timezone.now()
    run.save(update_fields=['status', 'result', 'completed_at'])
