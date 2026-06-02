"""JIT (just-in-time) data endpoints: issues, prs, diff, similar, file-history, vulnerabilities."""
import uuid
from typing import Optional

from django_ratelimit.decorators import ratelimit
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.analysis.github_meta import fetch_contribution_data

from .models import AnalysisRun

router = Router()


def _assert_not_limited(request):
    if getattr(request, 'limited', False):
        raise HttpError(429, 'Rate limit exceeded. Please try again later.')


def _jit_token(run: AnalysisRun) -> str:
    from django.conf import settings as _s
    return run.repo.auth_token or getattr(_s, 'GITHUB_TOKEN', '') or ''


def _jit_headers(token: str) -> dict:
    h = {'Accept': 'application/vnd.github+json'}
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h


def _compute_run_diff(curr: dict, prev: dict, prev_run_id, prev_triggered_at) -> dict:
    curr_h = {h['signal']: h for h in curr.get('heuristics', [])}
    prev_h = {h['signal']: h for h in prev.get('heuristics', [])}
    heuristic_deltas = []
    for signal, ch in curr_h.items():
        ph = prev_h.get(signal)
        if ph:
            delta = ch['score'] - ph['score']
            heuristic_deltas.append({
                'signal': signal,
                'label': ch['label'],
                'before': ph['score'],
                'after': ch['score'],
                'delta': delta,
                'direction': 'up' if delta > 2 else 'down' if delta < -2 else 'same',
            })

    curr_dep_names = {d['name'] for d in curr.get('dependencies', {}).get('dependencies', [])}
    prev_dep_names = {d['name'] for d in prev.get('dependencies', {}).get('dependencies', [])}

    curr_struct = curr.get('structure', {})
    prev_struct = prev.get('structure', {})
    curr_graph = curr.get('graph', {})
    prev_graph = prev.get('graph', {})
    curr_cls = curr.get('classification', {})
    prev_cls = prev.get('classification', {})

    def cls_delta(key):
        c = curr_cls.get(key, {})
        p = prev_cls.get(key, {})
        if not c or not p:
            return None
        return {
            'before_label': p.get('label'),
            'after_label': c.get('label'),
            'delta': c.get('score', 0) - p.get('score', 0),
            'changed': c.get('key') != p.get('key'),
        }

    added_deps = sorted(curr_dep_names - prev_dep_names)[:20]
    removed_deps = sorted(prev_dep_names - curr_dep_names)[:20]

    return {
        'available': True,
        'previous_run_id': str(prev_run_id),
        'previous_triggered_at': prev_triggered_at.isoformat(),
        'heuristics': heuristic_deltas,
        'dependencies': {
            'added': added_deps,
            'removed': removed_deps,
            'added_count': len(curr_dep_names - prev_dep_names),
            'removed_count': len(prev_dep_names - curr_dep_names),
        },
        'contributors': {
            'before': prev.get('commits', {}).get('total_contributors', 0),
            'after': curr.get('commits', {}).get('total_contributors', 0),
            'delta': curr.get('commits', {}).get('total_contributors', 0) - prev.get('commits', {}).get('total_contributors', 0),
        },
        'graph': {
            'nodes_before': prev_graph.get('node_count', 0),
            'nodes_after': curr_graph.get('node_count', 0),
            'nodes_delta': curr_graph.get('node_count', 0) - prev_graph.get('node_count', 0),
            'god_modules_before': len(prev_graph.get('god_modules', [])),
            'god_modules_after': len(curr_graph.get('god_modules', [])),
            'god_modules_delta': len(curr_graph.get('god_modules', [])) - len(prev_graph.get('god_modules', [])),
        },
        'structure': {
            'files_before': prev_struct.get('total_files', 0),
            'files_after': curr_struct.get('total_files', 0),
            'files_delta': curr_struct.get('total_files', 0) - prev_struct.get('total_files', 0),
            'test_ratio_before': round(prev_struct.get('test_ratio', 0), 3),
            'test_ratio_after': round(curr_struct.get('test_ratio', 0), 3),
        },
        'classification': {
            'project_health': cls_delta('project_health'),
            'contribution_difficulty': cls_delta('contribution_difficulty'),
            'documentation_grade': cls_delta('documentation_grade'),
            'code_complexity': cls_delta('code_complexity'),
        },
    }


class SimilarRunOut(Schema):
    run_id: str
    owner: str
    name: str
    repo_url: str
    oss_score: float
    health_key: str
    primary_language: Optional[str]
    stars: int


@router.get('/runs/{run_id}/issues')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_run_issues(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_issues'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    data = fetch_contribution_data(run.repo.owner, run.repo.name, _jit_headers(token))
    issues = data['issues'] if data else []
    cache.set(cache_key, issues, 900)
    return issues


@router.get('/runs/{run_id}/prs')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_run_prs(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_prs'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    data = fetch_contribution_data(run.repo.owner, run.repo.name, _jit_headers(token))
    pr_refs = data['pr_issue_refs'] if data else []
    result = {
        'pr_issue_refs': pr_refs,
        'open_prs': run.result.get('github_meta', {}).get('open_prs', 0) if run.result else 0,
    }
    cache.set(cache_key, result, 900)
    return result


@router.get('/runs/{run_id}/diff')
@ratelimit(key='user_or_ip', rate='60/h', method='GET', block=False)
def get_run_diff(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        return {'available': False}

    prev_run = (
        AnalysisRun.objects
        .filter(repo=run.repo, status='completed', triggered_at__lt=run.triggered_at)
        .exclude(id=run.id)
        .order_by('-triggered_at')
        .first()
    )
    if not prev_run or not prev_run.result:
        return {'available': False}

    return _compute_run_diff(run.result, prev_run.result, prev_run.id, prev_run.triggered_at)


@router.get('/runs/{run_id}/similar', response=list[SimilarRunOut])
@ratelimit(key='user_or_ip', rate='60/h', method='GET', block=False)
def get_similar_runs(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        return []

    lang = (run.result.get('github_meta') or {}).get('primary_language')
    score = (run.result.get('oss_score') or {}).get('score', 5)

    qs = AnalysisRun.objects.select_related('repo').filter(
        status='completed',
        repo__is_private=False,
    ).exclude(repo=run.repo).order_by('-completed_at')

    if lang:
        qs = qs.filter(result__github_meta__primary_language=lang)

    results = []
    for candidate in qs[:50]:
        if not candidate.result:
            continue
        cand_score = (candidate.result.get('oss_score') or {}).get('score', 5)
        if abs(cand_score - score) > 2:
            continue
        health_key = (
            (candidate.result.get('classification') or {})
            .get('project_health', {})
            .get('key', '')
        )
        stars = (candidate.result.get('github_meta') or {}).get('stars', 0)
        results.append(SimilarRunOut(
            run_id=str(candidate.id),
            owner=candidate.repo.owner,
            name=candidate.repo.name,
            repo_url=candidate.repo.url,
            oss_score=round(cand_score, 1),
            health_key=health_key,
            primary_language=lang,
            stars=stars,
        ))
        if len(results) >= 5:
            break

    return results


@router.get('/runs/{run_id}/file-history')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_file_history(request, run_id: uuid.UUID, path: str = ''):
    _assert_not_limited(request)
    import hashlib
    import re as _re
    import requests as _requests

    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if not path:
        raise HttpError(422, 'path parameter required')

    from django.core.cache import cache
    path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
    cache_key = f'jit_{run_id}_fh_{path_hash}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    headers = _jit_headers(token)
    url = f'https://api.github.com/repos/{run.repo.owner}/{run.repo.name}/commits'
    resp = _requests.get(url, headers=headers, params={'path': path, 'per_page': 10}, timeout=10)

    if not resp.ok:
        raise HttpError(502, 'Failed to fetch file history from GitHub')

    commits = []
    for c in resp.json():
        if not isinstance(c, dict):
            continue
        message = c.get('commit', {}).get('message', '').split('\n')[0][:120]
        refs = [int(m) for m in _re.findall(r'#(\d+)', message)][:5]
        commits.append({
            'sha': c['sha'][:7],
            'full_sha': c['sha'],
            'message': message,
            'date': c.get('commit', {}).get('author', {}).get('date', ''),
            'author': c.get('commit', {}).get('author', {}).get('name', ''),
            'url': c.get('html_url', ''),
            'issue_refs': refs,
        })

    result = {'path': path, 'commits': commits}
    cache.set(cache_key, result, 900)
    return result


@router.get('/runs/{run_id}/vulnerabilities')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_run_vulnerabilities(request, run_id: uuid.UUID):
    _assert_not_limited(request)
    import requests as _requests

    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and not request.user.is_authenticated:
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        return {'checked': 0, 'vulnerable': []}

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_vulns'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    deps = run.result.get('dependencies', {}).get('dependencies', [])
    queries = []
    for dep in deps:
        name = dep.get('name', '')
        version = dep.get('version', '')
        ecosystem = dep.get('ecosystem', '')
        if not name or not version or not ecosystem:
            continue
        osv_eco = {'npm': 'npm', 'pip': 'PyPI', 'cargo': 'crates.io', 'gem': 'RubyGems'}.get(ecosystem, ecosystem)
        queries.append({'package': {'name': name, 'ecosystem': osv_eco}, 'version': version})

    if not queries:
        result = {'checked': 0, 'vulnerable': []}
        cache.set(cache_key, result, 900)
        return result

    try:
        resp = _requests.post(
            'https://api.osv.dev/v1/querybatch',
            json={'queries': queries},
            timeout=15,
        )
        resp.raise_for_status()
        batch_results = resp.json().get('results', [])
    except Exception:
        raise HttpError(502, 'Failed to reach OSV vulnerability database')

    from apps.analysis.vuln_scan import _enrich_vulns

    raw_vulns = []
    all_ids = []
    for query, batch_result in zip(queries, batch_results):
        for v in batch_result.get('vulns', []):
            vid = v.get('id', '')
            if not vid:
                continue
            raw_vulns.append({'query': query, 'id': vid})
            all_ids.append(vid)

    details = _enrich_vulns(all_ids)

    vulnerable = []
    for item in raw_vulns:
        vid = item['id']
        q = item['query']
        d = details.get(vid, {})
        vulnerable.append({
            'name': q['package']['name'],
            'version': q['version'],
            'ecosystem': q['package']['ecosystem'],
            'vuln_id': vid,
            'summary': d.get('summary', ''),
            'severity': d.get('severity'),
            'severity_score': d.get('severity_score'),
            'url': f'https://osv.dev/vulnerability/{vid}',
        })

    result = {'checked': len(queries), 'vulnerable': vulnerable}
    cache.set(cache_key, result, 900)
    return result
