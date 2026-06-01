import re
import logging

logger = logging.getLogger(__name__)

_ECOSYSTEM_MAP = {
    'requirements': 'PyPI',
    'requirements.txt': 'PyPI',
    'pyproject.toml': 'PyPI',
    'Pipfile': 'PyPI',
    'package.json': 'npm',
    'package-lock.json': 'npm',
    'yarn.lock': 'npm',
    'pnpm-lock.yaml': 'npm',
    'Cargo.toml': 'crates.io',
    'Gemfile': 'RubyGems',
    'go.mod': 'Go',
}

_OP_RE = re.compile(r'^[^0-9]*')


def _extract_version(spec: str) -> str:
    """Strip leading version operators to get an approximate pinned version."""
    if not spec:
        return ''
    # Take the first constraint before any comma or semicolon
    first = spec.split(',')[0].split(';')[0].strip()
    # Strip operators like ^, ~, >=, <=, >, <, !=, ==, ~=
    clean = _OP_RE.sub('', first).strip()
    # Skip wildcard / workspace specs
    if not clean or clean in ('*', 'latest'):
        return ''
    return clean


def _source_ecosystem(source: str) -> str:
    for key, eco in _ECOSYSTEM_MAP.items():
        if key in source:
            return eco
    return ''


def scan_vulnerabilities(deps: dict) -> list[dict]:
    """Query OSV.dev batch API for known CVEs in the dependency list.

    Returns list of vulnerability dicts. Empty list on any failure.
    """
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
        queries.append({'package': {'name': name, 'ecosystem': ecosystem}, 'version': version})
        query_meta.append({'name': name, 'version': version, 'ecosystem': ecosystem})

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

    results = []
    for meta, result in zip(query_meta, batch):
        for v in result.get('vulns', []):
            severity = None
            for sev in v.get('severity', []):
                if sev.get('type') == 'CVSS_V3':
                    severity = sev.get('score')
                    break
            results.append({
                'name': meta['name'],
                'version': meta['version'],
                'ecosystem': meta['ecosystem'],
                'vuln_id': v.get('id', ''),
                'summary': v.get('summary', '')[:200],
                'severity': severity,
                'url': f"https://osv.dev/vulnerability/{v.get('id', '')}",
            })

    return results
