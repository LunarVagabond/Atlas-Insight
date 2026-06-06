from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='PHP',
    extensions=('.php',),
    extract_edges=extract_edges,
    lang_label='php',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('composer.json',),
    parse_manifest=parse_manifest,
    vuln_ecosystem='Packagist',
    manifest_dep_files=('composer.json',),
    test_frameworks={
        'phpunit': {'phpunit.xml', 'phpunit.xml.dist'},
    },
    tier='full',
)
