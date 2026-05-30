import logging
import os
from datetime import datetime, timezone as _tz

from celery import shared_task
from django.utils import timezone

from apps.repositories.models import AnalysisRun

from .classifications import classify_repo
from .commit_analysis import analyze_commits
from .contribution_analysis import analyze_contributions
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

    # Set is_private immediately via a lightweight API check so that even
    # failed runs are correctly hidden from users who don't own them.
    try:
        import requests as _requests
        _headers = {'Accept': 'application/vnd.github+json'}
        if pat:
            _headers['Authorization'] = f'Bearer {pat}'
        _r = _requests.get(
            f'https://api.github.com/repos/{run.repo.owner}/{run.repo.name}',
            headers=_headers, timeout=10,
        )
        if _r.status_code == 200:
            _is_private = _r.json().get('private', False)
            if run.repo.is_private != _is_private:
                run.repo.is_private = _is_private
                run.repo.save(update_fields=['is_private'])
    except Exception:
        pass

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
        contribution_data = github_meta.pop('contribution_data', None)
        github_languages = github_meta.pop('github_languages', None)

        # GitHub is authoritative for anything it provides — replace locally-computed values
        if github_languages:
            structure['languages'] = github_languages

        releases_meta = github_meta.get('releases_meta')
        if releases_meta:
            structure['release_count'] = releases_meta.get('stable_count', structure['release_count'])
            if releases_meta.get('latest_stable'):
                structure['last_release'] = {
                    'name': releases_meta['latest_stable']['name'],
                    'date': releases_meta['latest_stable']['date'],
                }

        created_at = github_meta.get('created_at')
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                structure['repo_age_days'] = (datetime.now(_tz.utc) - created_dt).days
            except Exception:
                pass

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
            'contribution_opportunities': analyze_contributions(commits, graph, deps, readme, structure, security, contribution_data),
        }
        run.status = 'completed'

        repo = run.repo
        repo.last_commit_sha = sha
        repo.last_analyzed_at = timezone.now()
        repo.last_fetched_at = fetched_at
        repo.is_stale = False
        repo.is_private = github_meta.get('is_private', False)
        repo.save(update_fields=['last_commit_sha', 'last_analyzed_at', 'last_fetched_at', 'is_stale', 'is_private'])
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


@shared_task
def cleanup_old_runs():
    """For each repo, delete runs beyond RUNS_TO_KEEP_PER_REPO (oldest first).
    Never deletes pending/running runs."""
    from django.conf import settings

    from apps.repositories.models import AnalysisRun, Repository

    keep = getattr(settings, 'RUNS_TO_KEEP_PER_REPO', 10)
    deleted_total = 0

    for repo in Repository.objects.all():
        # IDs to keep: latest `keep` runs regardless of status
        keep_ids = (
            AnalysisRun.objects.filter(repo=repo)
            .order_by('-triggered_at')
            .values_list('id', flat=True)[:keep]
        )
        # Also always keep any in-flight runs
        inflight_ids = (
            AnalysisRun.objects.filter(repo=repo, status__in=['pending', 'running'])
            .values_list('id', flat=True)
        )
        safe_ids = set(keep_ids) | set(inflight_ids)
        deleted, _ = (
            AnalysisRun.objects.filter(repo=repo)
            .exclude(id__in=safe_ids)
            .delete()
        )
        deleted_total += deleted

    logger.info('Run cleanup complete: %d old runs deleted (keeping %d per repo)', deleted_total, keep)


@shared_task
def evict_stale_clones():
    """Delete local cache clones not fetched within EVICT_AFTER_DAYS.

    AnalysisRun.result JSON is untouched. clone_or_fetch re-clones on next run.
    """
    import shutil
    from datetime import timedelta

    from django.conf import settings

    from apps.repositories.models import Repository

    from .git_ops import get_cache_path

    threshold = timezone.now() - timedelta(days=settings.EVICT_AFTER_DAYS)
    evicted = 0

    for repo in Repository.objects.filter(last_fetched_at__lt=threshold):
        try:
            path = get_cache_path(repo.url)
        except ValueError:
            continue
        if os.path.exists(path):
            shutil.rmtree(path)
            evicted += 1
            logger.info('Evicted clone cache for %s/%s (%s)', repo.owner, repo.name, path)

    logger.info(
        'Clone eviction complete: %d clones removed (threshold: %d days)',
        evicted, settings.EVICT_AFTER_DAYS,
    )


@shared_task
def cleanup_old_logs():
    """Delete rotated log backup files older than LOG_RETENTION_DAYS."""
    import time

    from django.conf import settings

    retention_seconds = settings.LOG_RETENTION_DAYS * 86400
    cutoff = time.time() - retention_seconds
    log_dir = settings.LOG_DIR
    deleted = 0

    for entry in log_dir.iterdir():
        # RotatingFileHandler backups: django.log.1, celery.log.2, etc.
        if entry.is_file() and entry.suffix.lstrip('.').isdigit():
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
                deleted += 1
                logger.info('Deleted old log backup: %s', entry.name)

    logger.info(
        'Log cleanup complete: %d backup files removed (retention: %d days)',
        deleted, settings.LOG_RETENTION_DAYS,
    )
