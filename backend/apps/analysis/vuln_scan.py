import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

def _build_ecosystem_map() -> dict[str, str]:
    from .languages import all_plugins
    eco: dict[str, str] = {
        # Partial-name keys used by _source_ecosystem's substring match
        'requirements': 'PyPI',
        'package-lock.json': 'npm',
        'yarn.lock': 'npm',
        'pnpm-lock.yaml': 'npm',
        'Pipfile': 'PyPI',
    }
    for p in all_plugins():
        if p.vuln_ecosystem:
            for fname in p.manifest_filenames:
                eco.setdefault(fname, p.vuln_ecosystem)
    return eco

_ECOSYSTEM_MAP = _build_ecosystem_map()

_OP_RE = re.compile(r'^[^0-9]*')
_OPEN_RANGE_RE = re.compile(r'^(>=|>|~=|~|\^)')

_SEVERITY_SCORE = {
    'critical': 9.5,
    'high': 7.5,
    'moderate': 5.5,
    'medium': 5.5,
    'low': 2.5,
}


def _extract_version(spec: str) -> str:
    if not spec:
        return ''
    first = spec.split(',')[0].split(';')[0].strip()
    clean = _OP_RE.sub('', first).strip()
    if not clean or clean in ('*', 'latest'):
        return ''
    return clean


def _is_open_range(spec: str) -> bool:
    """True when spec allows a range of versions rather than a single pinned version.

    Exact pins (==x.y.z or bare x.y.z) return False.
    Loose specs (>=, >, ~=, ~, ^) return True — the CVE may only affect
    some versions within the range, not necessarily the installed one.
    """
    if not spec:
        return False
    first = spec.split(',')[0].split(';')[0].strip()
    if first.startswith('=='):
        return False
    return bool(_OPEN_RANGE_RE.match(first))


def _source_ecosystem(source: str) -> str:
    for key, eco in _ECOSYSTEM_MAP.items():
        if key in source:
            return eco
    return ''


def _fetch_vuln_detail(vuln_id: str) -> dict:
    import requests as _requests
    try:
        r = _requests.get(
            f'https://api.osv.dev/v1/vulns/{vuln_id}',
            timeout=10,
        )
        if not r.ok:
            return {}
        v = r.json()
        summary = (v.get('summary') or v.get('details') or '')[:200]
        # Prefer database_specific.severity (GitHub Advisory string label)
        db_sev = (v.get('database_specific') or {}).get('severity', '')
        severity_label = db_sev.upper() if db_sev else None
        # Numeric score for heuristic use — map label or parse CVSS vector
        severity_score = _SEVERITY_SCORE.get((db_sev or '').lower())
        if severity_score is None:
            for sev in v.get('severity') or []:
                score_str = sev.get('score', '')
                # CVSS vector string → skip numeric parse; use label fallback
                if sev.get('type') in ('CVSS_V3', 'CVSS_V4') and score_str:
                    # Try raw float first (unlikely but handle it)
                    try:
                        severity_score = float(score_str)
                        break
                    except ValueError:
                        pass
        return {
            'summary': summary,
            'severity': severity_label,
            'severity_score': severity_score,
        }
    except Exception:
        return {}


def _enrich_vulns(vuln_ids: list[str]) -> dict[str, dict]:
    unique_ids = list(dict.fromkeys(vuln_ids))[:30]
    details: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_vuln_detail, vid): vid for vid in unique_ids}
        for future in as_completed(futures):
            vid = futures[future]
            result = future.result()
            if result:
                details[vid] = result
    return details


def scan_vulnerabilities(deps: dict) -> list[dict]:
    import requests as _requests

    dep_list = deps.get('dependencies', [])
    queries = []
    query_meta = []

    for dep in dep_list:
        name = dep.get('name', '')
        version = _extract_version(dep.get('version_spec', ''))
        ecosystem = _source_ecosystem(dep.get('source', ''))
        if not name or not version or not ecosystem:
            continue
        version_spec = dep.get('version_spec', '')
        queries.append({'package': {'name': name, 'ecosystem': ecosystem}, 'version': version})
        query_meta.append({
            'name': name,
            'version': version,
            'version_spec': version_spec,
            'ecosystem': ecosystem,
            'is_range': _is_open_range(version_spec),
        })

    if not queries:
        return []

    try:
        resp = _requests.post(
            'https://api.osv.dev/v1/querybatch',
            json={'queries': queries},
            timeout=20,
        )
        resp.raise_for_status()
        batch = resp.json().get('results', [])
    except Exception:
        logger.warning('OSV.dev vulnerability scan failed — skipping')
        return []

    # Collect all vuln IDs first, then enrich in parallel
    raw: list[dict] = []
    all_ids: list[str] = []
    for meta, result in zip(query_meta, batch):
        for v in result.get('vulns', []):
            vid = v.get('id', '')
            if not vid:
                continue
            raw.append({'meta': meta, 'id': vid})
            all_ids.append(vid)

    details = _enrich_vulns(all_ids)

    results = []
    for item in raw:
        vid = item['id']
        meta = item['meta']
        d = details.get(vid, {})
        is_range = meta['is_range']
        results.append({
            'name': meta['name'],
            'version': meta['version_spec'] if is_range else meta['version'],
            'ecosystem': meta['ecosystem'],
            'vuln_id': vid,
            'summary': d.get('summary', ''),
            'severity': d.get('severity'),
            'severity_score': d.get('severity_score'),
            'url': f'https://osv.dev/vulnerability/{vid}',
            'version_is_range': is_range,
            'note': (
                f"CVE affects some versions within the declared range "
                f"({meta['version_spec']}). Verify your installed version is not affected."
            ) if is_range else None,
        })

    return results
