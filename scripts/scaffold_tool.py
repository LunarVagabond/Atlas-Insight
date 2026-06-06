#!/usr/bin/env python3
"""Scaffold a new tool plugin for Atlas Insight.

Usage:
    python scripts/scaffold_tool.py "Kubernetes"
    python scripts/scaffold_tool.py "Kubernetes" --category iac
"""
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / 'backend' / 'apps' / 'analysis' / 'tools'

ANALYSIS_TEMPLATE = '''\
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SKIP_DIRS = frozenset({{
    '.git', 'node_modules', '.venv', 'venv', '__pycache__', 'vendor', 'dist', 'build',
}})


def _should_skip(path: Path, root: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.relative_to(root).parts)


def analyze(repo_dir: str) -> dict:
    """Analyze {NAME} configuration in the repo.

    TODO: Implement detection and analysis logic.

    Return dict shape:
        {{
            'detected': True,
            # ... tool-specific fields
            'security_issues': [{{'resource': str, 'severity': str, 'issue': str}}],
            'score': int,   # 0-100 hygiene/quality score
        }}
    """
    root = Path(repo_dir)
    # TODO: walk relevant files, parse config, build result dict
    return {{
        'detected': True,
        'security_issues': [],
        'score': 0,
    }}
'''

INIT_TEMPLATE = '''\
from ..base import ToolPlugin
from .analysis import analyze

plugin = ToolPlugin(
    name=\'{NAME}\',
    slug=\'{SLUG}\',
    category=\'{CATEGORY}\',
    detect_files=(),    # TODO: e.g. (\'kubernetes.yaml\', \'k8s/\')
    detect_exts=(),     # TODO: e.g. (\'.yaml\',) if extension is distinctive
    detect_dirs=(),     # TODO: e.g. (\'.kube\', \'k8s\')
    analyze=analyze,
)
'''


def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def main() -> None:
    parser = argparse.ArgumentParser(description='Scaffold a new tool plugin.')
    parser.add_argument('name', help='Display name, e.g. "Kubernetes"')
    parser.add_argument(
        '--category',
        choices=['container', 'iac', 'ci', 'build', 'security'],
        default='iac',
        help='Tool category (default: iac)',
    )
    args = parser.parse_args()

    name: str = args.name.strip()
    category: str = args.category
    slug = slugify(name)

    dest_dir = TOOLS_DIR / slug
    if dest_dir.exists():
        print(f'ERROR: backend/apps/analysis/tools/{slug}/ already exists. Aborting.')
        sys.exit(1)

    dest_dir.mkdir(parents=True)
    (dest_dir / 'analysis.py').write_text(ANALYSIS_TEMPLATE.format(NAME=name))
    (dest_dir / '__init__.py').write_text(
        INIT_TEMPLATE.format(NAME=name, SLUG=slug, CATEGORY=category)
    )

    print()
    print(f'Scaffolded: backend/apps/analysis/tools/{slug}/')
    print(f'  analysis.py    detection + analysis logic')
    print(f'  __init__.py    plugin assembly (ToolPlugin)')
    print()
    print('Next steps:')
    print()
    print('  1. Fill in analysis.py:')
    print(f'       Implement analyze(repo_dir) → dict')
    print(f'       Include "score" (0–100) and "security_issues" list')
    print()
    print('  2. Fill in __init__.py:')
    print(f'       Set detect_files, detect_exts, detect_dirs to identify the tool')
    print()
    print('  3. Register in frontend supported-technologies list:')
    print(f'       frontend/src/data/languages.ts')
    print(f'       Add entry:')
    print(f'         {{ name: \'{name}\', iconUrl: \'<devicon-url>\', tier: \'full\', kind: \'tool\', maturity: \'early\' }},')
    print(f'       This drives the /supported page and the home page marquee.')
    print()
    print('  4. Add TypeScript types in:')
    print(f'       frontend/src/types/run.ts')
    print(f'       Add interface {name.replace(" ", "")}Data and add to ToolsData')
    print()
    print('  5. Add frontend section in:')
    print(f'       frontend/src/components/analysis/DevOpsPanel.vue')
    print(f'       Use v-if="tools?.{slug}" to show only when detected')
    print()
    print('  6. Run tests:')
    print('       cd backend && make test')
    print()


if __name__ == '__main__':
    main()
