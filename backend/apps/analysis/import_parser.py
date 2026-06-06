import os
from pathlib import Path

from .languages import get_plugin

MAX_FILE_SIZE = 500_000  # 500KB

SKIP_DIRS = {'.git', 'node_modules', '.venv', '__pycache__', 'vendor', 'dist'}


def _rel(base: str, path: str) -> str:
    return os.path.relpath(path, base)


def parse_imports(repo_dir: str) -> list[dict]:
    edges = []
    base = repo_dir
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                fsize = os.path.getsize(fpath)
            except OSError:
                continue
            if fsize > MAX_FILE_SIZE:
                continue
            ext = Path(fname).suffix.lower()
            plugin = get_plugin(ext)
            if plugin is None or plugin.extract_edges is None:
                continue
            source = _rel(base, fpath)
            try:
                with open(fpath, encoding='utf-8', errors='ignore') as _f:
                    content = _f.read()
            except Exception:
                continue
            for dep in plugin.extract_edges(fpath, content, base):
                edges.append({'source': source, 'target': dep, 'lang': plugin.lang_label})
    return edges
