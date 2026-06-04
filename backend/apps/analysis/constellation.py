"""Cross-repo constellation detection — finds links between analyzed repos."""
import logging
import re

logger = logging.getLogger(__name__)

_GITHUB_URL_RE = re.compile(
    r'https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)',
    re.IGNORECASE,
)


def _norm(name: str) -> str:
    return re.sub(r'[-_./]', '', name.lower())


def _common_prefix(a: str, b: str) -> str:
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i]


def detect_refs(run) -> list[dict]:
    """
    Return edges from this run to other analyzed repos in the DB.

    Each edge: {repo_id, owner, name, run_id, ref_type, evidence}
    ref_type: 'readme_link' | 'dep_match' | 'same_org_pattern'
    """
    from apps.repositories.models import Repository

    result = run.result or {}
    self_owner = run.repo.owner.lower()
    self_name = run.repo.name.lower()

    other_repos = list(
        Repository.objects
        .exclude(pk=run.repo_id)
        .filter(runs__status='completed')
        .distinct()
    )
    if not other_repos:
        return []

    # Build lookup tables
    by_owner_name: dict[tuple[str, str], Repository] = {}
    by_norm_name: dict[str, list[Repository]] = {}
    for r in other_repos:
        key = (r.owner.lower(), r.name.lower())
        by_owner_name[key] = r
        by_norm_name.setdefault(_norm(r.name), []).append(r)

    edges: list[dict] = []
    seen: set[str] = set()

    def _latest_run_id(repo: Repository) -> str:
        run_obj = repo.runs.filter(status='completed').order_by('-triggered_at').first()
        return str(run_obj.id) if run_obj else ''

    def _add(repo: Repository, ref_type: str, evidence: str) -> None:
        rid = str(repo.pk)
        if rid in seen:
            return
        seen.add(rid)
        edges.append({
            'repo_id': rid,
            'owner': repo.owner,
            'name': repo.name,
            'run_id': _latest_run_id(repo),
            'ref_type': ref_type,
            'evidence': evidence,
        })

    # 1. README github links
    readme_content = (result.get('readme') or {}).get('content') or ''
    for m in _GITHUB_URL_RE.finditer(readme_content):
        link_owner = m.group(1).lower()
        link_name = m.group(2).lower()
        if link_owner == self_owner and link_name == self_name:
            continue
        repo = by_owner_name.get((link_owner, link_name))
        if repo:
            _add(repo, 'readme_link', f'github.com/{m.group(1)}/{m.group(2)} linked in README')

    # 2. Dependency name matches a known repo name
    dep_list = (result.get('dependencies') or {}).get('dependencies') or []
    for dep in dep_list:
        dep_name = dep.get('name') or ''
        if not dep_name:
            continue
        for repo in by_norm_name.get(_norm(dep_name), []):
            _add(repo, 'dep_match', f'dependency "{dep_name}" matches repo name')

    # 3. Same-org naming pattern (common prefix ≥4 chars)
    same_org = [r for (o, _), r in by_owner_name.items() if o == self_owner]
    my_norm = _norm(self_name)
    for repo in same_org:
        if str(repo.pk) in seen:
            continue
        prefix = _common_prefix(my_norm, _norm(repo.name))
        if len(prefix) >= 4:
            _add(repo, 'same_org_pattern', f'same org, name prefix "{prefix}"')

    return edges


def upsert_constellation(run, edges: list[dict]) -> None:
    """Create or update a Constellation grouping for this run's detected edges."""
    from apps.repositories.models import Constellation, Repository

    if not edges:
        return

    repo_ids = {str(run.repo_id)} | {e['repo_id'] for e in edges}

    # Find existing constellation that already contains any of these repos
    existing = (
        Constellation.objects
        .filter(repos__id__in=repo_ids)
        .first()
    )

    if existing is None:
        existing = Constellation(
            name=f'{run.repo.owner} constellation',
            org=run.repo.owner,
        )
        existing.save()

    existing.repos.set(Repository.objects.filter(id__in=repo_ids))
    existing.edges = [
        {
            'from_repo_id': str(run.repo_id),
            'to_repo_id': e['repo_id'],
            'ref_type': e['ref_type'],
            'evidence': e['evidence'],
        }
        for e in edges
    ]
    existing.save(update_fields=['edges'])
