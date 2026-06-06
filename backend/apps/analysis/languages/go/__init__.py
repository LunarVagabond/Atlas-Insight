from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Go',
    extensions=('.go',),
    extract_edges=extract_edges,
    lang_label='go',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('go.mod',),
    parse_manifest=parse_manifest,
    vuln_ecosystem='Go',
    manifest_dep_files=('go.mod',),
    test_frameworks={
        'go test': {'_test.go'},
    },
    tier='full',
)
