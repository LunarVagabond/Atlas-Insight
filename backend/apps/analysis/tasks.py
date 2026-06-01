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
from .heuristics import compute_heuristics, compute_oss_score
from .import_parser import parse_imports
from .project_structure import analyze_structure
from .readme_parser import parse_readme
from .arch_tours import generate_arch_tours
from .ownership_analysis import analyze_ownership
from .security_scan import scan_security
from .todo_scan import scan_todos
from .vuln_scan import scan_vulnerabilities

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
        security['vulnerabilities'] = scan_vulnerabilities(deps)
        todos = scan_todos(repo_dir)
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
        oss_score = compute_oss_score(signals)
        classification = classify_repo(
            commits, graph, deps, readme, structure, security, github_meta
        )

        run.result = {
            'commits': commits,
            'graph': graph,
            'dependencies': deps,
            'heuristics': signals,
            'oss_score': oss_score,
            'readme': readme,
            'structure': structure,
            'security': security,
            'github_meta': github_meta,
            'classification': classification,
            'todos': todos,
            'arch_tours': generate_arch_tours(structure, graph, commits),
            'ownership': analyze_ownership(structure, commits, graph),
            'contribution_opportunities': analyze_contributions(
                commits, graph, deps, readme, structure, security, contribution_data, todos=todos
            ),
        }
        run.status = 'completed'

        from django.db.models import F
        repo = run.repo
        repo.last_commit_sha = sha
        repo.last_analyzed_at = timezone.now()
        repo.last_fetched_at = fetched_at
        repo.is_stale = False
        repo.is_private = github_meta.get('is_private', False)
        update_fields = ['last_commit_sha', 'last_analyzed_at', 'last_fetched_at', 'is_stale', 'is_private']
        if pat and pat != repo.auth_token:
            repo.auth_token = pat
            repo.auth_token_warning = ''
            update_fields += ['auth_token', 'auth_token_warning']
        repo.save(update_fields=update_fields)
        run.repo.__class__.objects.filter(pk=repo.pk).update(scan_count=F('scan_count') + 1)
        logger.info('Analysis completed for run %s', run_id)

    except Exception as exc:
        logger.exception('Analysis failed for run %s', run_id)
        run.status = 'failed'
        import git as _git
        if isinstance(exc, PermissionError):
            friendly = str(exc)
            # Stored token caused an auth failure — remove it and warn the user.
            try:
                _repo = run.repo
                if _repo.auth_token:
                    _repo.auth_token = ''
                    _repo.auth_token_warning = (
                        'A stored access token for this repository is no longer valid '
                        'and has been removed. Re-submit with a new Personal Access Token '
                        'to re-analyze private repositories.'
                    )
                    _repo.save(update_fields=['auth_token', 'auth_token_warning'])
            except Exception:
                pass
        elif isinstance(exc, _git.GitCommandError):
            friendly = (
                'Failed to clone or fetch the repository. '
                'It may be private, deleted, or temporarily unavailable.'
            )
        elif isinstance(exc, ValueError):
            friendly = str(exc)
        else:
            friendly = 'An unexpected error occurred during analysis. Please try again.'
        run.result = {'error': friendly}

    run.completed_at = timezone.now()
    run.save(update_fields=['status', 'result', 'completed_at'])

    # Fire webhook if configured
    if run.webhook_url:
        try:
            import requests as _requests
            _requests.post(
                run.webhook_url,
                json={
                    'run_id': str(run.id),
                    'status': run.status,
                    'repo_url': run.repo.url,
                    'repo_owner': run.repo.owner,
                    'repo_name': run.repo.name,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'error': run.result.get('error') if run.result else None,
                },
                timeout=10,
                headers={'Content-Type': 'application/json', 'User-Agent': 'AtlasInsight/1.0'},
            )
        except Exception:
            logger.warning('Webhook POST failed for run %s → %s', run.id, run.webhook_url)

    # Send email notification if configured
    if run.notification_email:
        try:
            from django.conf import settings as _s
            from django.core.mail import send_mail
            result_url = f'{_s.FRONTEND_URL}/results/{run.id}'
            subject = f'[Atlas Insight] Analysis {run.status}: {run.repo.owner}/{run.repo.name}'
            body = (
                f'Your analysis of {run.repo.url} is complete.\n'
                f'Status: {run.status}\n\n'
                f'View results: {result_url}\n'
            )
            if run.result and run.result.get('error'):
                body += f'\nError: {run.result["error"]}\n'
            send_mail(subject, body, None, [run.notification_email], fail_silently=True)
        except Exception:
            logger.warning('Email notification failed for run %s', run.id)


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
def select_repo_of_week():
    """Weekly task: pick a public repo for the spotlight using a fair-rotation, weighted algorithm.

    Rotation rule: every repo gets one spotlight before any repo gets a second.
    Within the eligible tier, weight = scan_count * 0.6 + view_count * 0.4 + 1.
    Idempotent: skips if current week already has a pick.
    """
    import random
    from datetime import date, timedelta

    from django.db.models import Count

    from apps.repositories.models import RepoOfTheWeek, Repository

    # Monday of current week
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    if RepoOfTheWeek.objects.filter(week_start=week_start).exists():
        logger.info('Repo of the Week already selected for week %s', week_start)
        return

    eligible_repos = list(
        Repository.objects.filter(
            is_private=False,
            runs__status='completed',
        ).distinct()
    )
    if not eligible_repos:
        logger.warning('No eligible public repos for Repo of the Week')
        return

    pick_counts = dict(
        RepoOfTheWeek.objects.filter(repo__in=eligible_repos)
        .values('repo_id')
        .annotate(n=Count('id'))
        .values_list('repo_id', 'n')
    )

    min_picks = min((pick_counts.get(r.pk, 0) for r in eligible_repos), default=0)
    candidates = [r for r in eligible_repos if pick_counts.get(r.pk, 0) <= min_picks]

    weights = [r.scan_count * 0.6 + r.view_count * 0.4 + 1 for r in candidates]
    chosen = random.choices(candidates, weights=weights, k=1)[0]
    current_picks = pick_counts.get(chosen.pk, 0)

    RepoOfTheWeek.objects.create(
        repo=chosen,
        week_start=week_start,
        pick_number=current_picks + 1,
    )
    logger.info(
        'Repo of the Week selected: %s/%s (pick #%d)',
        chosen.owner, chosen.name, current_picks + 1,
    )


@shared_task
def reanalyze_watched_repos():
    """Daily task: re-analyze watched repos when new commits are detected."""
    from apps.repositories.models import AnalysisRun, Repository

    from .github_meta import fetch_latest_sha as _fetch_sha

    watched = list(Repository.objects.filter(is_watched=True))
    if not watched:
        logger.info('No watched repos to re-analyze')
        return

    queued = 0
    for repo in watched:
        try:
            latest_sha = _fetch_sha(repo.owner, repo.name, token=repo.auth_token or None)
        except Exception:
            logger.warning('Could not fetch SHA for watched repo %s/%s', repo.owner, repo.name)
            continue

        if latest_sha and latest_sha == repo.last_commit_sha and repo.last_analyzed_at:
            continue

        run = AnalysisRun.objects.create(repo=repo, status='pending')
        task = analyze_repository.delay(str(run.id), pat=repo.auth_token or None)
        run.celery_task_id = task.id
        run.save(update_fields=['celery_task_id'])
        queued += 1
        logger.info('Queued re-analysis for watched repo %s/%s (run %s)', repo.owner, repo.name, run.id)

    logger.info('Watched repo re-analysis: %d/%d repos queued', queued, len(watched))


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
