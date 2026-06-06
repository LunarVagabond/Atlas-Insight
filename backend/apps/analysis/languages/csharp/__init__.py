from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='C#',
    extensions=('.cs',),
    extract_edges=extract_edges,
    lang_label='csharp',
    extract_test_refs=extract_test_refs,
    manifest_filenames=(),
    parse_manifest=parse_manifest,
    vuln_ecosystem=None,
    manifest_dep_files=(),
    test_frameworks={
        'xunit': {'xunit.runner.json'},
    },
    tier='full',
)
