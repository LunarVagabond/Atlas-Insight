from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Rust',
    extensions=('.rs',),
    extract_edges=extract_edges,
    lang_label='rust',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('Cargo.toml',),
    parse_manifest=parse_manifest,
    vuln_ecosystem='crates.io',
    manifest_dep_files=('Cargo.toml',),
    test_frameworks={
        'cargo test': {'#[cfg(test)]'},
    },
    tier='full',
)
