#!/usr/bin/env python3
"""Scaffold a new language plugin for Atlas Insight.

Usage:
    python scripts/scaffold_language.py "Kotlin"
    python scripts/scaffold_language.py "Kotlin" --tier dependencies
"""
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LANGUAGES_DIR = REPO_ROOT / 'backend' / 'apps' / 'analysis' / 'languages'
SCAN_EXTS_FILE = REPO_ROOT / 'backend' / 'apps' / 'analysis' / 'todo_scan.py'

EDGES_TEMPLATE = '''\
import re

# TODO: Regex that captures the imported module/package name.
# Example: r'^\\s*import\\s+([\\w.]+)', re.MULTILINE
_IMPORT_RE = re.compile(r'TODO', re.MULTILINE)

# TODO: List stdlib / platform module names to exclude from the import graph.
_STDLIB_PREFIXES: tuple[str, ...] = ()


def _is_external(dep: str) -> bool:
    return any(dep.startswith(p) for p in _STDLIB_PREFIXES)


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    # TODO: For complex cases (block imports, relative resolution) write custom logic.
    return [m.group(1) for m in _IMPORT_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))]
'''

TESTS_TEMPLATE = '''\
# TODO: Implement test reference extraction so the hotspot coverage heuristic
# can map test files to the source files they exercise.
# Return slash-separated path stems, e.g. "apps/analysis/tasks" (no extension).
# Return None here (and in __init__.py) if the language has no meaningful test imports.

def extract_test_refs(test_rel: str, test_dir: str, content: str) -> set[str]:
    return set()
'''

MANIFEST_TEMPLATE = '''\
from pathlib import Path

# TODO: Parse the language\'s dependency manifest file(s).
# Return list of dicts with at minimum "name" and "version_spec" keys.
# Set parse_manifest = None (and in __init__.py) if there is no manifest to parse.


def parse_manifest(path: Path) -> list[dict]:
    return []
'''

INIT_TEMPLATE = '''\
from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name=\'{NAME}\',
    extensions=(),                 # TODO: e.g. (\'.kt\', \'.kts\')
    extract_edges=extract_edges,
    lang_label=\'{SLUG}\',
    extract_test_refs=extract_test_refs,
    manifest_filenames=(),         # TODO: e.g. (\'build.gradle.kts\',)
    parse_manifest=parse_manifest,
    vuln_ecosystem=None,           # TODO: OSV name e.g. \'Maven\', \'PyPI\', \'npm\'
    manifest_dep_files=(),         # TODO: subset of manifest_filenames for sub-project detection
    test_frameworks={{}},           # TODO: e.g. {{\'kotest\': {{\'kotest.gradle.kts\'}}}}
    tier=\'{TIER}\',
)
'''


def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def devicon_url(slug: str) -> str:
    return f'https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{slug}/{slug}-original.svg'


def main() -> None:
    parser = argparse.ArgumentParser(description='Scaffold a new language plugin.')
    parser.add_argument('name', help='Display name, e.g. "Kotlin"')
    parser.add_argument('--tier', choices=['full', 'dependencies'], default='full',
                        help='Analysis tier (default: full)')
    args = parser.parse_args()

    name: str = args.name.strip()
    tier: str = args.tier
    slug = slugify(name)

    dest_dir = LANGUAGES_DIR / slug
    if dest_dir.exists():
        print(f'ERROR: backend/apps/analysis/languages/{slug}/ already exists. Aborting.')
        sys.exit(1)

    dest_dir.mkdir(parents=True)
    (dest_dir / 'edges.py').write_text(EDGES_TEMPLATE)
    (dest_dir / 'tests.py').write_text(TESTS_TEMPLATE)
    (dest_dir / 'manifest.py').write_text(MANIFEST_TEMPLATE)
    (dest_dir / '__init__.py').write_text(
        INIT_TEMPLATE.format(NAME=name, SLUG=slug, TIER=tier)
    )

    icon_slug = slug.replace('_', '')
    icon_url = devicon_url(icon_slug)
    ts_entry = (
        f"  {{ name: '{name}', "
        f"iconUrl: '{icon_url}', "
        f"tier: '{tier}', kind: 'language', maturity: 'early' }},"
    )

    print()
    print(f'Scaffolded: backend/apps/analysis/languages/{slug}/')
    print(f'  edges.py       import graph extraction')
    print(f'  tests.py       test reference extraction')
    print(f'  manifest.py    dependency manifest parsing')
    print(f'  __init__.py    plugin assembly (LanguagePlugin)')
    print()
    print('Next steps:')
    print()
    print('  1. Fill in the generated files:')
    print(f'     edges.py    — set _IMPORT_RE, _STDLIB_PREFIXES, extract_edges()')
    print(f'     tests.py    — implement extract_test_refs() (or set = None if n/a)')
    print(f'     manifest.py — implement parse_manifest() (or set = None if n/a)')
    print(f'     __init__.py — set extensions, manifest_filenames, vuln_ecosystem, etc.')
    print()
    print('  2. Add file extension(s) to SCAN_EXTS in:')
    print(f'       backend/apps/analysis/todo_scan.py')

    try:
        scan_line = next(
            line.rstrip() for line in SCAN_EXTS_FILE.read_text().splitlines()
            if line.strip().startswith('SCAN_EXTS')
        )
        print(f'     Current: {scan_line}')
    except (StopIteration, OSError):
        pass

    print()
    print('  3. Add frontend entry to:')
    print(f'       frontend/src/data/languages.ts')
    print(f'     Entry (start with maturity: "early", promote as support matures):')
    print(f'       {ts_entry}')
    print(f'     Icon URL (verify at https://devicon.dev — may need -plain.svg):')
    print(f'       {icon_url}')
    print(f'     This entry drives the home page marquee, About page, and /supported page.')
    print()
    print('  4. Run tests:')
    print('       cd backend && make test')
    print()


if __name__ == '__main__':
    main()
