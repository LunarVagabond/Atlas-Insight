import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from datetime import timezone as _tz

from celery import shared_task
from django.db.models import Exists, OuterRef
from django.utils import timezone
from prometheus_client import Counter, Gauge, Histogram

from apps.repositories.models import AnalysisRun

from .arch_tours import generate_arch_tours
from .changelog_analysis import analyze_changelog
from .cicd_analysis import analyze_cicd
from .classifications import classify_repo
from .tools import detect_tools
from .commit_analysis import analyze_commits
from .complexity import analyze_complexity
from .contribution_analysis import analyze_contributions
from .dead_code import analyze_dead_code
from .dep_report import analyze_dependencies
from .diff_analysis import compute_run_diff
from .git_ops import clone_or_fetch
from .github_meta import fetch_github_meta
from .graph_analysis import analyze_graph
from .heuristics import compute_heuristics, compute_oss_score
from .import_parser import parse_imports
from .license_analysis import analyze_license
from .ownership_analysis import analyze_ownership
from .project_structure import analyze_structure
from .project_structure.tech_stack import detect_tech_stack
from .readme_parser import parse_readme
from .repo_type import detect_docs_only, detect_repo_type
from .security_scan import scan_security
from .test_coverage import analyze_test_coverage
from .todo_scan import scan_todos
from .vuln_scan import scan_vulnerabilities

logger = logging.getLogger(__name__)

_RESULT_UPDATE_FIELDS = [
    'status', 'completed_at', 'progress_step', 'commit_sha',
    'oss_score', 'oss_badge', 'primary_language', 'github_stars', 'archived',
    'total_commits', 'total_contributors', 'days_since_last_commit', 'abandoned',
    'bus_factor', 'security_issue_count', 'dependency_count', 'test_ratio',
    'is_docs_only', 'error_message',
    'commits_data', 'graph_data', 'deps_data', 'heuristics_data', 'oss_score_data',
    'readme_data', 'structure_data', 'security_data', 'github_meta_data',
    'classification_data', 'todos_data', 'arch_tours_data', 'ownership_data',
    'contribution_opportunities_data', 'repo_type_data', 'license_data',
    'complexity_data', 'dead_code_data', 'test_coverage_data', 'containers_data',
    'cicd_data', 'tools_data', 'changelog_data', 'diff_data', 'similar_runs_data',
    'issues_data', 'pr_refs_data',
]


def _extract_run_fields(run: 'AnalysisRun', result: dict) -> None:
    oss_raw = result.get('oss_score')
    if isinstance(oss_raw, dict):
        oss_raw = dict(oss_raw)
        mode_reason = result.get('scoring_mode_reason')
        if mode_reason:
            oss_raw['mode_reason'] = mode_reason
        run.oss_score = oss_raw.get('score')
        run.oss_badge = oss_raw.get('badge', '') or ''
        run.oss_score_data = oss_raw
    else:
        run.oss_score = None
        run.oss_badge = ''
        run.oss_score_data = None

    gm = result.get('github_meta') or {}
    run.primary_language = gm.get('primary_language') or ''
    run.github_stars = gm.get('stars')
    run.archived = gm.get('archived')

    cm = result.get('commits') or {}
    run.total_commits = cm.get('total_commits')
    run.total_contributors = cm.get('total_contributors')
    run.days_since_last_commit = cm.get('days_since_last_commit')
    run.abandoned = cm.get('abandoned')

    st = result.get('structure') or {}
    run.bus_factor = st.get('bus_factor')

    sec = result.get('security') or {}
    run.security_issue_count = sec.get('issue_count')

    deps = result.get('dependencies') or {}
    run.dependency_count = deps.get('dependency_count')

    tc = result.get('test_coverage') or {}
    run.test_ratio = tc.get('test_ratio')

    run.is_docs_only = bool(result.get('is_docs_only', False))
    run.error_message = None

    run.commits_data = result.get('commits')
    run.graph_data = result.get('graph')
    run.deps_data = result.get('dependencies')
    run.heuristics_data = result.get('heuristics')
    run.readme_data = result.get('readme')
    run.structure_data = result.get('structure')
    run.security_data = result.get('security')
    run.github_meta_data = result.get('github_meta')
    run.classification_data = result.get('classification')
    run.todos_data = result.get('todos')
    run.arch_tours_data = result.get('arch_tours')
    run.ownership_data = result.get('ownership')
    run.contribution_opportunities_data = result.get('contribution_opportunities')
    run.repo_type_data = result.get('repo_type')
    run.license_data = result.get('license')
    run.complexity_data = result.get('complexity')
    run.dead_code_data = result.get('dead_code')
    run.test_coverage_data = result.get('test_coverage')
    run.containers_data = result.get('containers')
    run.cicd_data = result.get('cicd')
    run.tools_data = result.get('tools')
    run.changelog_data = result.get('changelog')
    run.diff_data = result.get('diff')
    run.similar_runs_data = result.get('similar_runs')
    run.issues_data = result.get('issues')
    run.pr_refs_data = result.get('pr_refs')


def _analyze_sub_projects(
    repo_type_info: dict,
    all_edges: list[dict],
    repo_obj,
    commits: dict,
    scoring_mode: str = 'oss',
) -> dict:
    sub_project_results = []
    for sp in repo_type_info['sub_projects']:
        sp_path = sp['path']      # e.g. 'frontend/'
        sp_abs = sp['abs_path']

        sub_deps = analyze_dependencies(sp_abs)
        sub_vulns = scan_vulnerabilities(sub_deps)
        sub_deps['vulnerabilities'] = sub_vulns

        sub_edges = [e for e in all_edges if e['source'].startswith(sp_path)]
        sub_graph = analyze_graph(sub_edges)

        sub_security = scan_security(repo_obj, sp_abs, path_prefix=sp_path)

        sub_signals = compute_heuristics(
            commits, sub_graph, sub_deps,
            readme=None, structure=None, security=sub_security,
            scoring_mode=scoring_mode,
        )
        sub_oss_score = compute_oss_score(sub_signals, scoring_mode=scoring_mode)
        sub_tech_stack = detect_tech_stack(sp_abs, sub_deps.get('dependencies', []))

        sub_project_results.append({
            'name': sp['name'],
            'path': sp_path,
            'languages': sp['languages'],
            'tech_stack': sub_tech_stack,
            'dependencies': sub_deps,
            'graph': sub_graph,
            'security': sub_security,
            'heuristics': sub_signals,
            'oss_score': sub_oss_score,
        })

    return {
        'type': repo_type_info['type'],
        'detected_by': repo_type_info['detected_by'],
        'sub_projects': sub_project_results,
    }


def _compute_run_diff(run: AnalysisRun, result: dict) -> dict:
    try:
        prev_run = (
            AnalysisRun.objects
            .filter(
                repo=run.repo, status='completed', branch=run.branch,
                triggered_at__lt=run.triggered_at,
            )
            .exclude(id=run.id)
            .order_by('-triggered_at')
            .first()
        )
        if prev_run and prev_run.result:
            return compute_run_diff(result, prev_run.result, prev_run.id, prev_run.triggered_at)
    except Exception:
        pass
    return {'available': False}


def _compute_similar_runs(run: AnalysisRun, result: dict) -> list[dict]:
    try:
        lang = (result.get('github_meta') or {}).get('primary_language')
        oss_raw = result.get('oss_score')
        score = oss_raw.get('score', 5) if isinstance(oss_raw, dict) else 5
        sim_qs = (
            AnalysisRun.objects.select_related('repo')
            .filter(status='completed', repo__is_private=False)
            .exclude(repo=run.repo)
            .order_by('-completed_at')
        )
        if lang:
            sim_qs = sim_qs.filter(primary_language=lang)
        similar: list[dict] = []
        for c in sim_qs[:50]:
            if c.oss_score is None:
                continue
            cand_score = c.oss_score
            if abs(cand_score - score) > 2:
                continue
            similar.append({
                'run_id': str(c.id),
                'owner': c.repo.owner,
                'name': c.repo.name,
                'repo_url': c.repo.url,
                'oss_score': round(float(cand_score), 1),
                'health_key': ((c.classification_data or {}).get('project_health') or {}).get('key', ''),
                'primary_language': lang,
                'stars': c.github_stars or 0,
            })
            if len(similar) >= 5:
                break
        return similar
    except Exception:
        return []


@shared_task
def notify_run_complete(run_id: str):
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        return

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
                    'error': run.error_message or None,
                },
                timeout=10,
                headers={'Content-Type': 'application/json', 'User-Agent': 'AtlasInsight/1.0'},
            )
        except Exception:
            logger.warning('Webhook POST failed for run %s → %s', run.id, run.webhook_url)

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
            if run.error_message:
                body += f'\nError: {run.error_message}\n'
            send_mail(subject, body, None, [run.notification_email], fail_silently=True)
        except Exception:
            logger.warning('Email notification failed for run %s', run.id)


analysis_runs_total = Counter(
    'analysis_runs_total',
    'Total analysis runs by outcome',
    ['status'],
)
analysis_duration_seconds = Histogram(
    'analysis_duration_seconds',
    'Wall-clock seconds for analyze_repository task',
    buckets=[10, 30, 60, 120, 300, 600, 1200],
)
celery_queue_depth = Gauge(
    'celery_queue_depth',
    'Tasks pending in the Celery default queue',
)


def _update_queue_depth():
    try:
        import redis as _redis
        from django.conf import settings as _s
        r = _redis.Redis.from_url(_s.CELERY_BROKER_URL)
        celery_queue_depth.set(r.llen('celery'))
    except Exception:
        pass


@shared_task(bind=True)
def analyze_repository(self, run_id: str):
    _update_queue_depth()
    _start = time.monotonic()

    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        logger.error('AnalysisRun %s not found', run_id)
        return

    pat = run.repo.auth_token or None

    run.status = 'running'
    run.progress_step = 'cloning'
    run.save(update_fields=['status', 'progress_step'])
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
        repo_obj, sha, fetched_at = clone_or_fetch(run.repo.url, pat=pat, branch=run.branch)
        repo_dir = repo_obj.working_dir

        run.progress_step = 'parsing'
        run.save(update_fields=['progress_step'])

        is_docs_only = detect_docs_only(repo_dir)
        commits = analyze_commits(repo_obj)
        readme = parse_readme(repo_dir)
        contribution_data: dict | None = None

        if is_docs_only:
            _empty_graph = {
                'node_count': 0, 'edge_count': 0, 'cycles': [], 'cycle_count': 0,
                'god_modules': [], 'hotspots': [], 'nodes': [], 'edges': [],
            }
            _empty_deps = {'dependencies': [], 'dev_dependencies': [], 'tech_stack': []}
            structure = analyze_structure(repo_obj, repo_dir, deps=_empty_deps)
            security = scan_security(repo_obj, repo_dir)
            security['vulnerabilities'] = []

            run.progress_step = 'metadata'
            run.save(update_fields=['progress_step'])

            github_meta = fetch_github_meta(run.repo.owner, run.repo.name, token=pat)
            github_meta.pop('contribution_data', None)
            github_languages = github_meta.pop('github_languages', None)
            if github_languages:
                structure['languages'] = github_languages

            releases_meta = github_meta.get('releases_meta')
            if releases_meta:
                structure['release_count'] = releases_meta.get('total_count', structure['release_count'])
                if releases_meta.get('latest_release'):
                    structure['last_release'] = {
                        'name': releases_meta['latest_release']['name'],
                        'date': releases_meta['latest_release']['date'],
                    }

            created_at = github_meta.get('created_at')
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    structure['repo_age_days'] = (datetime.now(_tz.utc) - created_dt).days
                except Exception:
                    pass

            run.progress_step = 'heuristics'
            run.save(update_fields=['progress_step'])

            from .scoring_mode import infer_scoring_mode

            scoring_mode, scoring_mode_reason = infer_scoring_mode(
                is_private=run.repo.is_private,
                github_meta=github_meta,
                structure=structure,
            )

            classification = classify_repo(
                commits, _empty_graph, _empty_deps, readme, structure, security, github_meta,
                scoring_mode=scoring_mode,
            )
            oss_score = compute_oss_score([], scoring_mode=scoring_mode)
            oss_score['mode_reason'] = scoring_mode_reason

            run.progress_step = 'finalizing'
            run.save(update_fields=['progress_step'])

            result = {
                'is_docs_only': True,
                'commits': commits,
                'graph': _empty_graph,
                'dependencies': _empty_deps,
                'heuristics': [],
                'oss_score': oss_score,
                'scoring_mode': scoring_mode,
                'scoring_mode_reason': scoring_mode_reason,
                'readme': readme,
                'structure': structure,
                'security': security,
                'github_meta': github_meta,
                'classification': classification,
                'todos': {'todos': [], 'total': 0, 'by_type': {}},
                'arch_tours': [],
                'ownership': analyze_ownership(structure, commits, _empty_graph),
                'contribution_opportunities': [],
            }
        else:
            edges = parse_imports(repo_dir)

            repo_type_info = detect_repo_type(repo_dir)
            repo_type_result = None

            with ThreadPoolExecutor(max_workers=2) as _parse_pool:
                _graph_f = _parse_pool.submit(analyze_graph, edges)
                _todos_f = _parse_pool.submit(scan_todos, repo_dir)
                graph = _graph_f.result()
                todos = _todos_f.result()

            deps = analyze_dependencies(repo_dir)

            with ThreadPoolExecutor(max_workers=3) as _struct_pool:
                _sec_f = _struct_pool.submit(scan_security, repo_obj, repo_dir)
                _struct_f = _struct_pool.submit(analyze_structure, repo_obj, repo_dir, deps)
                _vuln_f = _struct_pool.submit(scan_vulnerabilities, deps)
                security = _sec_f.result()
                structure = _struct_f.result()
                security['vulnerabilities'] = _vuln_f.result()

            run.progress_step = 'metadata'
            run.save(update_fields=['progress_step'])

            github_meta = fetch_github_meta(run.repo.owner, run.repo.name, token=pat)
            contribution_data = github_meta.pop('contribution_data', None)
            github_languages = github_meta.pop('github_languages', None)

            if github_languages:
                structure['languages'] = github_languages

            releases_meta = github_meta.get('releases_meta')
            if releases_meta:
                structure['release_count'] = releases_meta.get('total_count', structure['release_count'])
                if releases_meta.get('latest_release'):
                    structure['last_release'] = {
                        'name': releases_meta['latest_release']['name'],
                        'date': releases_meta['latest_release']['date'],
                    }

            created_at = github_meta.get('created_at')
            if created_at:
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    structure['repo_age_days'] = (datetime.now(_tz.utc) - created_dt).days
                except Exception:
                    pass

            run.progress_step = 'heuristics'
            run.save(update_fields=['progress_step'])

            from .scoring_mode import infer_scoring_mode

            scoring_mode, scoring_mode_reason = infer_scoring_mode(
                is_private=run.repo.is_private,
                github_meta=github_meta,
                structure=structure,
            )

            if repo_type_info['type'] != 'single':
                try:
                    repo_type_result = _analyze_sub_projects(
                        repo_type_info, edges, repo_obj, commits, scoring_mode=scoring_mode,
                    )
                except Exception:
                    logger.warning('Sub-project analysis failed — continuing without repo_type', exc_info=True)
                    repo_type_result = None

            def _run_license():
                return analyze_license(
                    repo_dir, deps, github_meta, scoring_mode=scoring_mode,
                )

            def _run_complexity():
                return analyze_complexity(repo_dir, structure)

            def _run_dead_code():
                return analyze_dead_code(edges, repo_dir)

            def _run_test_coverage():
                return analyze_test_coverage(repo_dir, structure)

            def _run_tools():
                return detect_tools(repo_dir)

            def _run_cicd():
                return analyze_cicd(repo_dir, structure)

            def _run_changelog():
                return analyze_changelog(repo_dir, structure, commits)

            _extra_tasks = {
                'license': _run_license,
                'complexity': _run_complexity,
                'dead_code': _run_dead_code,
                'test_coverage': _run_test_coverage,
                'tools': _run_tools,
                'cicd': _run_cicd,
                'changelog': _run_changelog,
            }
            _extra_results: dict = {}
            with ThreadPoolExecutor(max_workers=7) as _pool:
                _futures = {_pool.submit(fn): key for key, fn in _extra_tasks.items()}
                for _future in as_completed(_futures):
                    _key = _futures[_future]
                    try:
                        _extra_results[_key] = _future.result()
                    except Exception:
                        logger.warning('Extra analyzer %s failed', _key, exc_info=True)
                        _extra_results[_key] = {}

            _tools = _extra_results.get('tools') or {}
            signals = compute_heuristics(
                commits, graph, deps, readme, structure, security,
                license_data=_extra_results.get('license'),
                complexity_data=_extra_results.get('complexity'),
                test_coverage_data=_extra_results.get('test_coverage'),
                cicd_data=_extra_results.get('cicd'),
                container_data=_tools.get('docker'),
                scoring_mode=scoring_mode,
            )
            oss_score = compute_oss_score(signals, scoring_mode=scoring_mode)
            oss_score['mode_reason'] = scoring_mode_reason
            classification = classify_repo(
                commits, graph, deps, readme, structure, security, github_meta,
                scoring_mode=scoring_mode,
            )

            run.progress_step = 'finalizing'
            run.save(update_fields=['progress_step'])

            def _run_arch_tours():
                return generate_arch_tours(structure, graph, commits)

            def _run_ownership():
                return analyze_ownership(structure, commits, graph)

            def _run_contributions():
                return analyze_contributions(
                    commits, graph, deps, readme, structure, security, contribution_data,
                    todos=todos, scoring_mode=scoring_mode,
                )

            _finalize: dict = {}
            with ThreadPoolExecutor(max_workers=3) as _fin_pool:
                _fin_tasks = {
                    'arch_tours': _run_arch_tours,
                    'ownership': _run_ownership,
                    'contribution_opportunities': _run_contributions,
                }
                _fin_futures = {_fin_pool.submit(fn): key for key, fn in _fin_tasks.items()}
                for _future in as_completed(_fin_futures):
                    _key = _fin_futures[_future]
                    try:
                        _finalize[_key] = _future.result()
                    except Exception:
                        logger.warning('Finalizing step %s failed', _key, exc_info=True)
                        _finalize[_key] = [] if _key == 'contribution_opportunities' else []

            result = {
                'commits': commits,
                'graph': graph,
                'dependencies': deps,
                'heuristics': signals,
                'oss_score': oss_score,
                'scoring_mode': scoring_mode,
                'scoring_mode_reason': scoring_mode_reason,
                'readme': readme,
                'structure': structure,
                'security': security,
                'github_meta': github_meta,
                'classification': classification,
                'todos': todos,
                'arch_tours': _finalize.get('arch_tours', []),
                'ownership': _finalize.get('ownership', {}),
                'contribution_opportunities': _finalize.get('contribution_opportunities', []),
                'license': _extra_results.get('license', {}),
                'complexity': _extra_results.get('complexity', {}),
                'dead_code': _extra_results.get('dead_code', {}),
                'test_coverage': _extra_results.get('test_coverage', {}),
                'tools': _tools,
                'containers': _tools.get('docker', {}),
                'cicd': _extra_results.get('cicd', {}),
                'changelog': _extra_results.get('changelog', {}),
            }
            if repo_type_result is not None:
                result['repo_type'] = repo_type_result

            # Bake contribution issues + pr refs into result (eliminates JIT GitHub calls)
            result['issues'] = (contribution_data or {}).get('issues', [])
            result['pr_refs'] = (contribution_data or {}).get('pr_issue_refs', [])

        # Compute diff + similar repos in parallel — baked in so frontend needs no extra call
        with ThreadPoolExecutor(max_workers=2) as _tail_pool:
            _diff_f = _tail_pool.submit(_compute_run_diff, run, result)
            _sim_f = _tail_pool.submit(_compute_similar_runs, run, result)
            result['diff'] = _diff_f.result()
            result['similar_runs'] = _sim_f.result()

        _extract_run_fields(run, result)
        run.status = 'completed'
        run.progress_step = ''
        run.commit_sha = sha
        analysis_runs_total.labels(status='completed').inc()

        from django.db.models import F
        repo = run.repo
        repo.last_analyzed_at = timezone.now()
        repo.last_fetched_at = fetched_at
        repo.is_stale = False
        repo.is_private = github_meta.get('is_private', False)
        update_fields = ['last_analyzed_at', 'last_fetched_at', 'is_stale', 'is_private']
        if not run.branch:
            repo.last_commit_sha = sha
            update_fields.append('last_commit_sha')
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
        run.error_message = friendly
        analysis_runs_total.labels(status='failed').inc()

    analysis_duration_seconds.observe(time.monotonic() - _start)
    run.completed_at = timezone.now()
    run.progress_step = ''
    run.save(update_fields=_RESULT_UPDATE_FIELDS)

    if run.status == 'completed':
        try:
            from apps.analysis.constellation import detect_refs, upsert_constellation
            edges = detect_refs(run)
            upsert_constellation(run, edges)
        except Exception:
            logger.warning('Constellation detection failed for run %s', run_id, exc_info=True)

    if run.webhook_url or run.notification_email:
        notify_run_complete.delay(str(run.id))


@shared_task
def check_stale_repos():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import timedelta

    from django.conf import settings

    from apps.repositories.models import Repository

    from .github_meta import fetch_latest_sha

    stale_threshold = timezone.now() - timedelta(days=settings.STALE_AFTER_DAYS)
    repos = list(Repository.objects.exclude(last_commit_sha='').filter(is_stale=False))

    def _check(repo) -> bool:
        if repo.last_fetched_at and repo.last_fetched_at < stale_threshold:
            return True
        try:
            latest = fetch_latest_sha(repo.owner, repo.name)
            return bool(latest and latest != repo.last_commit_sha)
        except Exception:
            logger.warning('Stale SHA check failed for %s/%s', repo.owner, repo.name)
            return False

    stale_ids = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_check, r): r.pk for r in repos}
        for future in as_completed(futures):
            if future.result():
                stale_ids.append(futures[future])

    if stale_ids:
        Repository.objects.filter(pk__in=stale_ids).update(is_stale=True)
    logger.info('Stale check complete: %d repos marked stale', len(stale_ids))


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
    """Three-pass clone eviction:
    1. Time-based  — remove clones idle > EVICT_AFTER_HOURS (skip in-flight runs).
    2. Orphan sweep — remove dirs in REPO_CACHE_DIR with no matching Repository row.
    3. Size cap     — if cache total > MAX_CACHE_GB, evict LRU clones until under limit.
    """
    import shutil
    from datetime import timedelta

    from django.conf import settings

    from apps.repositories.models import AnalysisRun, Repository

    from .git_ops import get_cache_path

    cache_dir = settings.REPO_CACHE_DIR
    evicted = 0

    def _dir_size(path: str) -> int:
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
        return total

    active_repo_ids = set(
        AnalysisRun.objects.filter(status__in=['pending', 'running'])
        .values_list('repo_id', flat=True)
    )

    # Pass 1: time-based — repos not fetched within EVICT_AFTER_HOURS
    threshold = timezone.now() - timedelta(hours=settings.EVICT_AFTER_HOURS)
    for repo in (
        Repository.objects
        .filter(last_fetched_at__lt=threshold)
        .exclude(pk__in=active_repo_ids)
    ):
        try:
            path = get_cache_path(repo.url)
        except ValueError:
            continue
        if os.path.exists(path):
            shutil.rmtree(path)
            evicted += 1
            logger.info('Evicted inactive clone %s/%s', repo.owner, repo.name)

    # Pass 2: orphan sweep — dirs with no matching Repository row
    if cache_dir.exists():
        known_paths = set()
        for repo in Repository.objects.all():
            try:
                known_paths.add(get_cache_path(repo.url))
            except ValueError:
                pass
        for entry in cache_dir.iterdir():
            if entry.is_dir() and str(entry) not in known_paths:
                shutil.rmtree(entry)
                evicted += 1
                logger.info('Evicted orphan clone dir %s', entry.name)

    # Pass 3: size cap — LRU eviction when total exceeds MAX_CACHE_GB
    max_bytes = int(settings.MAX_CACHE_GB * 1024 ** 3)
    if cache_dir.exists():
        candidates = []
        for repo in (
            Repository.objects
            .exclude(pk__in=active_repo_ids)
            .order_by('last_fetched_at')
        ):
            try:
                path = get_cache_path(repo.url)
            except ValueError:
                continue
            if os.path.exists(path):
                candidates.append((path, repo))

        total_bytes = sum(_dir_size(p) for p, _ in candidates)
        for path, repo in candidates:
            if total_bytes <= max_bytes:
                break
            size = _dir_size(path)
            shutil.rmtree(path)
            total_bytes -= size
            evicted += 1
            logger.info('Evicted clone (size cap) %s/%s', repo.owner, repo.name)

    logger.info('Clone eviction complete: %d clones removed', evicted)


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
    from apps.repositories.spotlight import apply_spotlight_watch_rollover

    apply_spotlight_watch_rollover(chosen, week_start)
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
        task = analyze_repository.delay(str(run.id))
        run.celery_task_id = task.id
        run.save(update_fields=['celery_task_id'])
        queued += 1
        logger.info('Queued re-analysis for watched repo %s/%s (run %s)', repo.owner, repo.name, run.id)

    logger.info('Watched repo re-analysis: %d/%d repos queued', queued, len(watched))


@shared_task
def cleanup_never_succeeded_repos():
    """Delete repos that have never had a completed run and are older than 1 hour.

    Catches invalid/nonexistent URLs (e.g. 404s from GitHub) that failed
    immediately and would otherwise linger in the DB indefinitely.
    """
    from datetime import timedelta

    from apps.repositories.models import Repository

    cutoff = timezone.now() - timedelta(hours=1)

    # Repos with at least one completed run are safe — skip them
    ever_completed = (
        AnalysisRun.objects.filter(repo=OuterRef('pk'), status='completed')
    )
    stale = (
        Repository.objects.annotate(has_success=Exists(ever_completed))
        .filter(has_success=False, created_at__lt=cutoff)
    )
    count, _ = stale.delete()
    logger.info('Orphan repo cleanup: %d repos deleted (never completed, older than 1 h)', count)


