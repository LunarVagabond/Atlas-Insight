from ..base import LanguagePlugin
from .edges import extract_edges
from .manifest import parse_manifest
from .tests import extract_test_refs

plugin = LanguagePlugin(
    name='C/C++',
    extensions=('.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx'),
    extract_edges=extract_edges,
    lang_label='c_cpp',
    extract_test_refs=extract_test_refs,
    parse_manifest=parse_manifest,
    manifest_dep_files=('CMakeLists.txt', 'conanfile.txt', 'conanfile.py', 'vcpkg.json'),
    tier='dependencies',
)
