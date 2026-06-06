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


from apps.analysis.diff_analysis import compute_run_diff as _compute_run_diff  # noqa: E402


class SimilarRunOut(Schema):
    run_id: str
    owner: str
    name: str
    repo_url: str
    oss_score: float
    health_key: str
    primary_language: Optional[str]
    stars: int


class IssueOut(Schema):
    number: int
    title: str
    url: str
    labels: list[str]
    body_excerpt: str


class PrsOut(Schema):
    pr_issue_refs: list[int]
    open_prs: int


class HeuristicDeltaOut(Schema):
    signal: str
    label: str
    before: float
    after: float
    delta: float
    direction: str


class DepDeltaOut(Schema):
    added: list[str]
    removed: list[str]
    added_count: int
    removed_count: int


class ContribDeltaOut(Schema):
    before: int
    after: int
    delta: int


class GraphDeltaOut(Schema):
    nodes_before: int
    nodes_after: int
    nodes_delta: int
    god_modules_before: int
    god_modules_after: int
    god_modules_delta: int


class StructDeltaOut(Schema):
    files_before: int
    files_after: int
    files_delta: int
    test_ratio_before: float
    test_ratio_after: float


class ClassDeltaItem(Schema):
    before_label: Optional[str]
    after_label: Optional[str]
    delta: float
    changed: bool


class ClassDeltaOut(Schema):
    project_health: Optional[ClassDeltaItem] = None
    contribution_difficulty: Optional[ClassDeltaItem] = None
    documentation_grade: Optional[ClassDeltaItem] = None
    code_complexity: Optional[ClassDeltaItem] = None


class DiffOut(Schema):
    available: bool
    previous_run_id: Optional[str] = None
    previous_triggered_at: Optional[str] = None
    heuristics: list[HeuristicDeltaOut] = []
    dependencies: Optional[DepDeltaOut] = None
    contributors: Optional[ContribDeltaOut] = None
    graph: Optional[GraphDeltaOut] = None
    structure: Optional[StructDeltaOut] = None
    classification: Optional[ClassDeltaOut] = None


class FileCommitOut(Schema):
    sha: str
    full_sha: str
    message: str
    date: str
    author: str
    url: str
    issue_refs: list[int]


class FileHistoryOut(Schema):
    path: str
    commits: list[FileCommitOut]


class VulnOut(Schema):
    name: str
    version: str
    ecosystem: str
    vuln_id: str
    summary: str
    severity: Optional[str]
    severity_score: Optional[float]
    url: str


class VulnerabilitiesOut(Schema):
    checked: int
    vulnerable: list[VulnOut]


class AiSummaryOut(Schema):
    summary: str


class SubsystemHitOut(Schema):
    id: str
    name: str
    subsystem_type: str
    activity_score: float
    has_god_modules: bool
    matched_files: int


class ReviewerOut(Schema):
    author: str
    email: str
    pr_files_touched: int
    match_reason: str


class PrImpactOut(Schema):
    pr_number: int
    title: str
    state: str
    pr_url: str
    author: str
    additions: int
    deletions: int
    files_changed: int
    complexity_score: float
    complexity_label: str
    touches_god_module: bool
    touches_deps: bool
    complexity_notes: list[str]
    affected_subsystems: list[SubsystemHitOut]
    suggested_reviewers: list[ReviewerOut]


class ConstellationEdgeOut(Schema):
    repo_id: str
    owner: str
    name: str
    run_id: str
    ref_type: str
    evidence: str


class ConstellationOut(Schema):
    related: list[ConstellationEdgeOut]


@router.get('/runs/{run_id}/issues', response=list[IssueOut])
@ratelimit(key='user_or_ip', rate='30/m', method='GET', block=False)
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


@router.get('/runs/{run_id}/prs', response=PrsOut)
@ratelimit(key='user_or_ip', rate='30/m', method='GET', block=False)
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


@router.get('/runs/{run_id}/diff', response=DiffOut)
@ratelimit(key='user_or_ip', rate='60/m', method='GET', block=False)
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
        .filter(
            repo=run.repo, status='completed',
            branch=run.branch,
            triggered_at__lt=run.triggered_at,
        )
        .exclude(id=run.id)
        .order_by('-triggered_at')
        .first()
    )
    if not prev_run or not prev_run.result:
        return {'available': False}

    return _compute_run_diff(run.result, prev_run.result, prev_run.id, prev_run.triggered_at)


@router.get('/runs/{run_id}/similar', response=list[SimilarRunOut])
@ratelimit(key='user_or_ip', rate='60/m', method='GET', block=False)
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

    lang = run.primary_language or None
    score = run.oss_score if run.oss_score is not None else 5

    qs = AnalysisRun.objects.select_related('repo').filter(
        status='completed',
        branch='',
        repo__is_private=False,
    ).exclude(repo=run.repo).order_by('-completed_at')

    if lang:
        qs = qs.filter(primary_language=lang)

    results = []
    for candidate in qs[:50]:
        if candidate.oss_score is None:
            continue
        cand_score = candidate.oss_score
        if abs(cand_score - score) > 2:
            continue
        health_key = (
            (candidate.classification_data or {})
            .get('project_health', {})
            .get('key', '')
        )
        stars = candidate.github_stars or 0
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


@router.get('/runs/{run_id}/file-history', response=FileHistoryOut)
@ratelimit(key='user_or_ip', rate='30/m', method='GET', block=False)
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
    branch_slug = run.branch.replace('/', '_')[:20] if run.branch else 'default'
    cache_key = f'jit_{run_id}_fh_{branch_slug}_{path_hash}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    token = _jit_token(run)
    headers = _jit_headers(token)
    url = f'https://api.github.com/repos/{run.repo.owner}/{run.repo.name}/commits'
    params: dict = {'path': path, 'per_page': 10}
    if run.branch:
        params['sha'] = run.branch
    resp = _requests.get(url, headers=headers, params=params, timeout=10)

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


@router.get('/runs/{run_id}/vulnerabilities', response=VulnerabilitiesOut)
@ratelimit(key='user_or_ip', rate='30/m', method='GET', block=False)
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


@router.get('/runs/{run_id}/ai-summary', response=AiSummaryOut)
@ratelimit(key='user_or_ip', rate='60/m', method='GET', block=False)
def get_ai_summary(request, run_id: uuid.UUID):
    """Export deterministic run context for external AI tools; Atlas Insight does not use AI for scanning."""
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
    complexity = r.get('complexity') or {}
    dead_code = r.get('dead_code') or {}
    test_coverage = r.get('test_coverage') or {}
    cicd = r.get('cicd') or {}
    containers = r.get('containers') or {}
    changelog = r.get('changelog') or {}
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

    if run.branch:
        lines.append(f"Branch: {run.branch}")
        lines.append("")

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

    # ── Code quality ────────────────────────────────────────────────────────
    cq_parts: list[str] = []
    if complexity:
                cq_parts.append(f"{complexity.get('files_over_threshold', 0)} complexity hotspots")
    if dead_code:
                cq_parts.append(f"{dead_code.get('count', 0)} unreferenced files")
    if test_coverage:
                ratio = test_coverage.get('test_ratio')
                if isinstance(ratio, (int, float)):
                        cq_parts.append(f"test ratio {round(ratio * 100)}%")
                framework = test_coverage.get('framework_detected')
                if framework:
                        cq_parts.append(f"framework {framework}")
    if cq_parts:
                lines.append(f"Code Quality: {', '.join(cq_parts)}.")
                untested = test_coverage.get('untested_dirs') or []
                if untested:
                        sample = ', '.join(d.get('path', '') for d in untested[:5] if d.get('path'))
                        if sample:
                                lines.append(f"  Likely under-tested areas: {sample}.")
                lines.append("")

    # ── DevOps ──────────────────────────────────────────────────────────────
    devops_parts: list[str] = []
    if cicd:
        devops_parts.append(f"{cicd.get('workflow_count', 0)} CI workflow(s)")
        summary = cicd.get('summary') or {}
        checks = []
        if summary.get('has_tests'):
            checks.append('tests')
        if summary.get('has_lint'):
            checks.append('lint')
        if summary.get('has_deploy'):
            checks.append('deploy')
        if checks:
            devops_parts.append(f"checks: {', '.join(checks)}")
    if containers:
        devops_parts.append(
            f"{containers.get('dockerfile_count', 0)} Dockerfile(s), {containers.get('total_issues', 0)} container issue(s)"
        )
    if changelog:
        status = 'present' if changelog.get('found') else 'missing'
        fmt = changelog.get('format') or 'none'
        devops_parts.append(f"changelog {status} ({fmt})")
    if devops_parts:
        lines.append(f"DevOps: {', '.join(devops_parts)}.")
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


@router.get('/runs/{run_id}/pr-impact', response=PrImpactOut)
@ratelimit(key='user_or_ip', rate='30/m', method='GET', block=False)
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


@router.get('/runs/{run_id}/constellation', response=ConstellationOut)
@ratelimit(key='user_or_ip', rate='60/m', method='GET', block=False)
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
