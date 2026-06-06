from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Swift',
    extensions=('.swift',),
    extract_edges=extract_edges,
    lang_label='swift',
    extract_test_refs=extract_test_refs,
    parse_manifest=parse_manifest,
    tier='full',
)
