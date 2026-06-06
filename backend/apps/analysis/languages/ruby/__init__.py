from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Ruby',
    extensions=('.rb',),
    extract_edges=extract_edges,
    lang_label='ruby',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('Gemfile',),
    parse_manifest=parse_manifest,
    vuln_ecosystem='RubyGems',
    manifest_dep_files=('Gemfile',),
    test_frameworks={
        'rspec':    {'.rspec', 'spec/spec_helper.rb'},
        'minitest': {'test/test_helper.rb'},
    },
    tier='full',
)
