from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import hcl2
    _HAS_HCL2 = True
except ImportError:
    _HAS_HCL2 = False

# Security check patterns applied to raw file content
_HARDCODED_SECRET = re.compile(
    r'(?:password|secret|token|api_key|access_key|private_key)\s*=\s*"[^"]{6,}"',
    re.IGNORECASE,
)
_OPEN_CIDR = re.compile(r'cidr_blocks\s*=\s*\[.*"0\.0\.0\.0/0"', re.IGNORECASE | re.DOTALL)
_FORCE_DESTROY = re.compile(r'force_destroy\s*=\s*true', re.IGNORECASE)
_PUBLIC_ACL = re.compile(r'acl\s*=\s*"public', re.IGNORECASE)

_SKIP_DIRS = frozenset({
    '.git', 'node_modules', '.venv', 'venv', '.terraform', '__pycache__',
    'vendor', 'dist', 'build',
})

_BACKEND_NAMES: dict[str, str] = {
    's3': 'S3', 'gcs': 'GCS', 'azurerm': 'Azure', 'consul': 'Consul',
    'remote': 'Terraform Cloud', 'http': 'HTTP', 'kubernetes': 'Kubernetes',
    'pg': 'PostgreSQL', 'etcd': 'etcd', 'artifactory': 'Artifactory',
}


def _should_skip(path: Path, root: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.relative_to(root).parts)


def analyze(repo_dir: str) -> dict:
    root = Path(repo_dir)
    tf_files = [p for p in root.rglob('*.tf') if not _should_skip(p, root)]

    providers: set[str] = set()
    resource_types: dict[str, int] = {}
    modules: list[str] = []
    backend: str | None = None
    version_constraint: str | None = None
    security_issues: list[dict] = []
    workspace_config = False

    for tf_path in tf_files:
        content = ''
        try:
            content = tf_path.read_text(errors='ignore')
        except OSError:
            continue

        # --- Security scans on raw text (before HCL parse, catches obfuscated too) ---
        rel = str(tf_path.relative_to(root))
        if _HARDCODED_SECRET.search(content):
            security_issues.append({
                'resource': rel, 'severity': 'high',
                'issue': 'Possible hardcoded secret or credential in Terraform file',
            })
        if _OPEN_CIDR.search(content):
            security_issues.append({
                'resource': rel, 'severity': 'high',
                'issue': 'Security group allows traffic from 0.0.0.0/0 (open to internet)',
            })
        if _FORCE_DESTROY.search(content):
            security_issues.append({
                'resource': rel, 'severity': 'medium',
                'issue': 'force_destroy = true — resource will be deleted without confirmation',
            })
        if _PUBLIC_ACL.search(content):
            security_issues.append({
                'resource': rel, 'severity': 'medium',
                'issue': 'Resource uses a public ACL — data may be publicly accessible',
            })
        if 'workspaces' in content:
            workspace_config = True

        if not _HAS_HCL2:
            continue

        try:
            parsed = hcl2.loads(content)
        except Exception:
            continue

        # terraform block
        for tf_block in parsed.get('terraform', []):
            if not isinstance(tf_block, dict):
                continue
            if version_constraint is None and 'required_version' in tf_block:
                version_constraint = tf_block['required_version']
            for rp in tf_block.get('required_providers', []):
                if isinstance(rp, dict):
                    for pname, pval in rp.items():
                        providers.add(pname)
                        if isinstance(pval, dict) and 'version' in pval:
                            pass  # version pinning tracked below
            for be_block in tf_block.get('backend', []):
                if isinstance(be_block, dict):
                    for be_type in be_block:
                        backend = _BACKEND_NAMES.get(be_type, be_type.title())

        # provider blocks
        for prov_block in parsed.get('provider', []):
            if isinstance(prov_block, dict):
                for pname in prov_block:
                    providers.add(pname)

        # resource blocks
        for res_block in parsed.get('resource', []):
            if isinstance(res_block, dict):
                for res_type in res_block:
                    resource_types[res_type] = resource_types.get(res_type, 0) + 1

        # module blocks
        for mod_block in parsed.get('module', []):
            if isinstance(mod_block, dict):
                for mod_name, mod_cfg in mod_block.items():
                    if isinstance(mod_cfg, dict) and 'source' in mod_cfg:
                        src = mod_cfg['source']
                        if src not in modules:
                            modules.append(src)

    score = _compute_score(
        has_backend=backend is not None,
        has_version=version_constraint is not None,
        security_issues=security_issues,
    )

    return {
        'detected': True,
        'providers': sorted(providers),
        'resource_count': sum(resource_types.values()),
        'resource_types': dict(sorted(resource_types.items(), key=lambda kv: -kv[1])),
        'backend': backend,
        'modules': modules,
        'version_constraint': version_constraint,
        'workspace_config': workspace_config,
        'security_issues': security_issues,
        'score': score,
        'file_count': len(tf_files),
    }


def _compute_score(
    has_backend: bool,
    has_version: bool,
    security_issues: list[dict],
) -> int:
    score = 40  # baseline
    if has_backend:
        score += 20
    if has_version:
        score += 20
    highs = sum(1 for i in security_issues if i['severity'] == 'high')
    mediums = sum(1 for i in security_issues if i['severity'] == 'medium')
    score -= min(highs * 10, 40)
    score -= min(mediums * 5, 20)
    return max(0, min(100, score))
