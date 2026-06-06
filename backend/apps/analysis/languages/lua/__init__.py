from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Lua',
    extensions=('.lua',),
    extract_edges=extract_edges,
    lang_label='lua',
    extract_test_refs=extract_test_refs,
    parse_manifest=parse_manifest,
    test_frameworks={
        'busted': {'.busted', 'spec/'},
    },
    tier='full',
)
