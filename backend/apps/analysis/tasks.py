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
def analyze_repository(self, run_id: str):
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
        repo_dir = repo_obj.working_dir

        commits = analyze_commits(repo_obj)
        edges = parse_imports(repo_dir)
        graph = analyze_graph(edges)
        deps = analyze_dependencies(repo_dir)
        readme = parse_readme(repo_dir)
        structure = analyze_structure(repo_obj, repo_dir)
        security = scan_security(repo_obj, repo_dir)
        github_meta = fetch_github_meta(run.repo.owner, run.repo.name)

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
        repo.save(update_fields=['last_commit_sha', 'last_analyzed_at'])
        logger.info('Analysis completed for run %s', run_id)

    except Exception as exc:
        logger.exception('Analysis failed for run %s', run_id)
        run.status = 'failed'
        run.result = {'error': str(exc)}

    run.completed_at = timezone.now()
    run.save(update_fields=['status', 'result', 'completed_at'])
