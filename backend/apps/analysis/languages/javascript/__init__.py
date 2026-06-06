from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='JavaScript',
    extensions=('.js', '.ts', '.jsx', '.tsx', '.mjs', '.vue'),
    extract_edges=extract_edges,
    lang_label='js',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('package.json',),
    parse_manifest=parse_manifest,
    vuln_ecosystem='npm',
    manifest_dep_files=('package.json',),
    test_frameworks={
        'jest':    {'jest.config.js', 'jest.config.ts', 'jest.config.cjs'},
        'vitest':  {'vitest.config.ts', 'vitest.config.js'},
        'mocha':   {'.mocharc.js', '.mocharc.yml', '.mocharc.json'},
    },
    tier='full',
)
