from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Java',
    extensions=('.java',),
    extract_edges=extract_edges,
    lang_label='java',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('pom.xml', 'build.gradle'),
    parse_manifest=parse_manifest,
    vuln_ecosystem='Maven',
    manifest_dep_files=('pom.xml', 'build.gradle', 'build.sbt'),
    test_frameworks={
        'junit': {'pom.xml'},
        'xunit': {'xunit.runner.json'},
    },
    tier='full',
)
