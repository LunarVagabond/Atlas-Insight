import re

# Matches internal-only crate paths: use crate::, use super::, use self::
_IMPORT_RE = re.compile(r'^\s*use\s+((?:super|self|crate)(?:::\w+)+)', re.MULTILINE)


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content) if m.group(1)]
