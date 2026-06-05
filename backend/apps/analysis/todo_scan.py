import re
from pathlib import Path

SCAN_EXTS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.java', '.rb', '.rs', '.php', '.cs', '.cpp', '.c', '.lua'}
SKIP_DIRS = {'node_modules', '.git', 'venv', '.venv', 'dist', 'build', '__pycache__', '.next', '.nuxt', 'coverage'}
MARKER_RE = re.compile(r'(?:#|//)\s*(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)\b[:\s]*(.*)', re.IGNORECASE)
# Strips trailing code artifacts that appear when the marker was inside a string literal:
# e.g. "# HACK: msg\n')" captured from raise Exception('# HACK: msg\n')
_ARTIFACT_RE = re.compile(r'(\\[nrt]|[\'\")\];,>])+$')
MAX_FILE_BYTES = 512 * 1024
MAX_ITEMS = 500


def scan_todos(repo_dir: str) -> dict:
    """Scan source files for inline code markers (TODO, FIXME, HACK, etc.).

    Returns {total, by_type, items: [{file, line, type, text}]}.
    """
    root = Path(repo_dir)
    items: list[dict] = []
    by_type: dict[str, int] = {}
    total = 0

    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix not in SCAN_EXTS:
            continue
        # Skip any path component that is a skip dir
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue

        rel = str(path.relative_to(root))
        try:
            with open(path, errors='ignore') as fh:
                for lineno, line in enumerate(fh, start=1):
                    m = MARKER_RE.search(line)
                    if not m:
                        continue
                    marker_type = m.group(1).upper()
                    raw = m.group(2).strip()
                    # Truncate at literal \n — signals we matched inside a string literal
                    if '\\n' in raw:
                        raw = raw.split('\\n')[0]
                    text = _ARTIFACT_RE.sub('', raw).strip()[:120]
                    total += 1
                    by_type[marker_type] = by_type.get(marker_type, 0) + 1
                    if len(items) < MAX_ITEMS:
                        items.append({'file': rel, 'line': lineno, 'type': marker_type, 'text': text})
        except (OSError, UnicodeDecodeError):
            continue

    return {'total': total, 'by_type': by_type, 'items': items}
