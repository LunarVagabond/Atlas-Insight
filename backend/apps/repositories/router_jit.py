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
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
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
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
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
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
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
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
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
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
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
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
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


@router.get('/runs/{run_id}/ai-summary')
@ratelimit(key='user_or_ip', rate='60/h', method='GET', block=False)
def get_ai_summary(request, run_id: uuid.UUID):
    """AI onboarding brief — paste this at the start of a chat to orient the AI to the project."""
    _assert_not_limited(request)
    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id, status='completed')
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found or not completed')
    if run.repo.is_private:
        if not request.user.is_authenticated or run.user != request.user:
            raise HttpError(403, 'Access denied')

    r = run.result or {}
    owner, name = run.repo.owner, run.repo.name
    meta = r.get('github_meta') or {}
    commits = r.get('commits') or {}
    structure = r.get('structure') or {}
    deps = r.get('dependencies') or {}
    graph = r.get('graph') or {}
    security = r.get('security') or {}
    repo_type = r.get('repo_type') or {}
    arch_tours = r.get('arch_tours') or []
    opportunities = r.get('contribution_opportunities') or []
    commit_conventions = (r.get('commits') or {}).get('commit_conventions') or {}

    # Languages — pct already 0-100
    all_langs = [
        f"{l['name']} ({round(l['pct'])}%)"
        for l in (structure.get('languages') or [])
        if l.get('pct', 0) >= 1
    ]

    prod_deps = [d for d in (deps.get('dependencies') or []) if not d.get('dev')]
    dev_deps  = [d for d in (deps.get('dependencies') or []) if d.get('dev')]
    key_deps  = [d['name'] for d in prod_deps[:10]]

    hot_files    = [f.get('file', '') for f in (structure.get('hot_files') or [])[:8] if f.get('file')]
    god_modules  = [m.get('module', '') for m in (graph.get('god_modules') or [])[:8] if m.get('module')]
    top_contribs = [c['author'] for c in (commits.get('top_contributors') or [])[:5]]

    sec_issues = security.get('issues') or []
    vuln_count = len(security.get('vulnerabilities') or [])
    cycle_count = graph.get('cycle_count', 0)
    active_90d  = commits.get('active_contributor_count_90d')

    sub_projects = repo_type.get('sub_projects') or []
    repo_kind    = repo_type.get('type', 'single')

    lines: list[str] = []

    description = (meta.get('description') or '').strip()
    primary_lang = meta.get('primary_language') or (all_langs[0].split(' ')[0] if all_langs else '')

    # ── Opening sentence ─────────────────────────────────────────────────────
    # "<name> is a <description>. It uses:"
    if description:
        opener = f"{name} is a project at {run.repo.url}\n{description}\n\nIt uses:"
    else:
        opener = f"{name} is a {primary_lang} project at {run.repo.url}\n\nIt uses:"
    lines += [opener]
    for lang in all_langs:
        lines.append(f"  - {lang}")
    lines.append("")

    # ── Size + structure ─────────────────────────────────────────────────────
    size_parts = []
    if structure.get('total_files'):
        size_parts.append(f"{structure['total_files']:,} files")
    if structure.get('total_loc'):
        size_parts.append(f"{structure['total_loc']:,} lines of code")
    if size_parts:
        lines.append(f"The codebase is {' and '.join(size_parts)}.")

    if graph.get('node_count'):
        arch_sentence = f"There are {graph['node_count']} modules in the architecture with {graph.get('edge_count', 0)} import edges"
        if cycle_count:
            arch_sentence += f" and {cycle_count} circular dependencies that should be resolved before large refactors"
        arch_sentence += "."
        lines.append(arch_sentence)
    lines.append("")

    # ── Sub-projects (monorepo) ───────────────────────────────────────────────
    if sub_projects:
        lines.append(f"This is a {repo_kind} with the following sub-projects:")
        for sp in sub_projects:
            sp_langs = ', '.join(sp.get('languages') or []) or '—'
            sp_stack = ', '.join(sp.get('tech_stack') or [])
            sp_line = f"  - {sp['name']}/ ({sp_langs}"
            if sp_stack:
                sp_line += f", {sp_stack}"
            sp_line += ")"
            lines.append(sp_line)
        lines.append("")

    # ── Key files — core + hot ────────────────────────────────────────────────
    if god_modules or hot_files:
        lines.append("Key files to understand this codebase:")
        if god_modules:
            lines.append("  Core files (imported widely — read these first):")
            for f in god_modules:
                lines.append(f"    - {f}")
        if hot_files:
            lines.append("  Most actively changed files:")
            for f in hot_files:
                lines.append(f"    - {f}")
        lines.append("")

    # ── Architecture tours ────────────────────────────────────────────────────
    if arch_tours:
        lines.append("Suggested entry points by subsystem:")
        for tour in arch_tours[:5]:
            entry = (tour.get('entry_files') or [])[:3]
            if entry:
                lines.append(f"  {tour['name']}: {', '.join(entry)}")
        lines.append("")

    # ── Dependencies ─────────────────────────────────────────────────────────
    if key_deps:
        dep_line = f"Key dependencies: {', '.join(key_deps)}"
        remaining = len(prod_deps) - len(key_deps)
        if remaining > 0:
            dep_line += f" (plus {remaining} more production deps and {len(dev_deps)} dev deps)"
        lines.append(dep_line + ".")
        lines.append("")

    # ── Contributors ─────────────────────────────────────────────────────────
    if top_contribs:
        c_line = f"Main contributors: {', '.join(top_contribs)}"
        if active_90d is not None:
            c_line += f" — {active_90d} active in the last 90 days"
        lines.append(c_line + ".")
        lines.append("")

    # ── Commit convention ─────────────────────────────────────────────────────
    style = commit_conventions.get('style', '')
    template = commit_conventions.get('format_template', '')
    if style and style != 'mixed' and template:
        lines.append(f"Commit convention: {style} — format: {template}")
        lines.append("")

    # ── Open tasks ────────────────────────────────────────────────────────────
    open_opps = [o for o in opportunities if not o.get('has_open_pr')]
    if open_opps:
        lines.append("Open tasks and known issues:")
        for opp in open_opps:
            diff = opp.get('difficulty', 'unknown')
            title = opp.get('title', '')
            issue = f" (#{opp['issue_number']})" if opp.get('issue_number') else ''
            lines.append(f"  - [{diff}] {title}{issue}")
        lines.append("")

    # ── Security ─────────────────────────────────────────────────────────────
    vulns = security.get('vulnerabilities') or []
    if vulns or sec_issues:
        if vulns:
            lines.append(f"⚠ Dependency CVEs ({len(vulns)} total) — check before adding or upgrading packages:")
            for v in vulns:
                pkg = v.get('name', '?')
                ver = v.get('version', '')
                vid = v.get('vuln_id', '')
                sev = v.get('severity', '')
                parts = [f"  - {pkg}"]
                if ver:
                    parts[0] += f"@{ver}"
                if vid:
                    parts[0] += f" — {vid}"
                if sev:
                    parts[0] += f" ({sev})"
                lines.append(parts[0])
        if sec_issues:
            lines.append(f"⚠ {len(sec_issues)} security patterns flagged (possible accidental secrets or gitignore gaps).")
        lines.append("")

    summary = '\n'.join(lines).rstrip()
    return {'summary': summary}


@router.get('/runs/{run_id}/pr-impact')
@ratelimit(key='user_or_ip', rate='30/h', method='GET', block=False)
def get_pr_impact(request, run_id: uuid.UUID, pr: int):
    _assert_not_limited(request)
    import requests as _requests
    from apps.analysis.pr_impact import affected_subsystems, suggest_reviewers, compute_complexity

    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        raise HttpError(422, 'Analysis not yet complete')

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_pr_impact_{pr}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    headers = _jit_headers(token)
    owner, name = run.repo.owner, run.repo.name
    base = f'https://api.github.com/repos/{owner}/{name}'

    pr_resp = _requests.get(f'{base}/pulls/{pr}', headers=headers, timeout=10)
    if pr_resp.status_code == 404:
        raise HttpError(404, 'Pull request not found')
    if not pr_resp.ok:
        raise HttpError(502, 'Failed to fetch PR from GitHub')

    files_resp = _requests.get(
        f'{base}/pulls/{pr}/files', headers=headers,
        params={'per_page': 100}, timeout=10,
    )
    if not files_resp.ok:
        raise HttpError(502, 'Failed to fetch PR files from GitHub')

    pr_data = pr_resp.json()
    files_data = files_resp.json() if isinstance(files_resp.json(), list) else []
    changed_files = [f['filename'] for f in files_data if isinstance(f, dict) and 'filename' in f]

    # Fetch recent committers for the most-changed files in this PR (max 8 files)
    def _sort_key(f):
        return (f.get('additions', 0) or 0) + (f.get('deletions', 0) or 0)
    top_files = sorted(
        [f for f in files_data if isinstance(f, dict) and 'filename' in f],
        key=_sort_key, reverse=True,
    )[:8]
    # author email → set of PR files they've committed to
    author_pr_files: dict[str, set] = {}
    author_names: dict[str, str] = {}
    for file_obj in top_files:
        path = file_obj['filename']
        c_resp = _requests.get(
            f'{base}/commits', headers=headers,
            params={'path': path, 'per_page': 10}, timeout=10,
        )
        if not c_resp.ok:
            continue
        for commit in c_resp.json():
            if not isinstance(commit, dict):
                continue
            author_info = commit.get('commit', {}).get('author') or {}
            email = author_info.get('email', '')
            display = author_info.get('name', '') or email
            if email and not email.endswith('@users.noreply.github.com') and display:
                author_pr_files.setdefault(email, set()).add(path)
                author_names[email] = display

    result = run.result
    hit_subsystems = affected_subsystems(changed_files, result)
    reviewers = suggest_reviewers(changed_files, hit_subsystems, result, author_pr_files, author_names)
    complexity = compute_complexity(
        pr_data.get('additions', 0),
        pr_data.get('deletions', 0),
        changed_files,
        hit_subsystems,
        result,
    )

    impact = {
        'pr_number': pr,
        'title': pr_data.get('title', ''),
        'state': pr_data.get('state', ''),
        'pr_url': pr_data.get('html_url', ''),
        'author': (pr_data.get('user') or {}).get('login', ''),
        'additions': pr_data.get('additions', 0),
        'deletions': pr_data.get('deletions', 0),
        'files_changed': len(changed_files),
        'complexity_score': complexity['score'],
        'complexity_label': complexity['label'],
        'touches_god_module': complexity['touches_god_module'],
        'touches_deps': complexity['touches_deps'],
        'complexity_notes': complexity['notes'],
        'affected_subsystems': hit_subsystems,
        'suggested_reviewers': reviewers,
    }

    cache.set(cache_key, impact, 900)
    return impact


@router.get('/runs/{run_id}/constellation')
@ratelimit(key='user_or_ip', rate='60/h', method='GET', block=False)
def get_constellation(request, run_id: uuid.UUID):
    _assert_not_limited(request)

    try:
        run = AnalysisRun.objects.select_related('repo').get(id=run_id)
    except AnalysisRun.DoesNotExist:
        raise HttpError(404, 'Run not found')
    if run.repo.is_private and (not request.user.is_authenticated or run.user != request.user):
        raise HttpError(403, 'Access denied')
    if run.status != 'completed' or not run.result:
        return {'related': []}

    from django.core.cache import cache
    cache_key = f'jit_{run_id}_constellation'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from apps.analysis.constellation import detect_refs
    edges = detect_refs(run)
    result = {'related': edges}
    cache.set(cache_key, result, 900)
    return result
