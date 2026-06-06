from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Elixir',
    extensions=('.ex', '.exs'),
    extract_edges=extract_edges,
    lang_label='elixir',
    extract_test_refs=extract_test_refs,
    parse_manifest=parse_manifest,
    manifest_dep_files=('mix.exs',),
    test_frameworks={
        'exunit': {'test/test_helper.exs'},
    },
    tier='full',
)
