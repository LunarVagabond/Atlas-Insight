from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Dart',
    extensions=('.dart',),
    extract_edges=extract_edges,
    lang_label='dart',
    extract_test_refs=extract_test_refs,
    parse_manifest=parse_manifest,
    manifest_dep_files=('pubspec.yaml',),
    tier='full',
)
