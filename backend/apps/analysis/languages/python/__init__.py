from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='Python',
    extensions=('.py',),
    extract_edges=extract_edges,
    lang_label='python',
    extract_test_refs=extract_test_refs,
    manifest_filenames=('requirements.txt', 'requirements-dev.txt', 'requirements-test.txt',
                        'pyproject.toml'),
    parse_manifest=parse_manifest,
    vuln_ecosystem='PyPI',
    manifest_dep_files=('requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg'),
    test_frameworks={
        'pytest':   {'conftest.py', 'pytest.ini', 'pyproject.toml', 'setup.cfg'},
        'unittest': {'test_*.py'},
    },
    tier='full',
)
