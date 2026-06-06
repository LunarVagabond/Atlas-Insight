from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Kotlin',
    extensions=('.kt', '.kts'),
    extract_edges=extract_edges,
    lang_label='kotlin',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('build.gradle.kts',),
    parse_manifest=parse_manifest,
    vuln_ecosystem='Maven',
    manifest_dep_files=('build.gradle.kts',),
    test_frameworks={
        'kotest': {'kotest.gradle.kts'},
    },
    tier='full',
)
