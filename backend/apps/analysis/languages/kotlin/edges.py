import re

# Kotlin uses same import syntax as Java but semicolons are optional
_IMPORT_RE = re.compile(r'^\s*import\s+(?:static\s+)?([\w.]+(?:\.\w+)+)\s*;?', re.MULTILINE)

_STDLIB_PREFIXES = ('java.', 'javax.', 'sun.', 'com.sun.', 'kotlin.', 'kotlinx.',
                    'android.', 'androidx.')


def _is_external(dep: str) -> bool:
    return any(dep.startswith(p) for p in _STDLIB_PREFIXES)


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))]
