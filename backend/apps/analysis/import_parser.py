import os
import re
from pathlib import Path

PYTHON_IMPORT = re.compile(
    r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))', re.MULTILINE
)
JS_IMPORT = re.compile(
    r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))"""
)
GO_IMPORT = re.compile(r'"([^"]+)"')

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
            if os.path.getsize(fpath) > MAX_FILE_SIZE:
                continue
            ext = Path(fname).suffix.lower()
            source = _rel(base, fpath)
            try:
                content = open(fpath, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            if ext == '.py':
                for m in PYTHON_IMPORT.finditer(content):
                    dep = m.group(1) or m.group(2)
                    if dep:
                        for d in dep.split(','):
                            d = d.strip().split()[0]
                            if d:
                                edges.append({'source': source, 'target': d, 'lang': 'python'})
            elif ext in {'.js', '.ts', '.jsx', '.tsx', '.mjs'}:
                for m in JS_IMPORT.finditer(content):
                    dep = m.group(1) or m.group(2)
                    if dep:
                        edges.append({'source': source, 'target': dep, 'lang': 'js'})
            elif ext == '.go':
                in_block = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('import ('):
                        in_block = True
                        continue
                    if in_block:
                        if stripped == ')':
                            in_block = False
                            continue
                        m = GO_IMPORT.search(stripped)
                        if m:
                            edges.append({'source': source, 'target': m.group(1), 'lang': 'go'})
                    elif stripped.startswith('import '):
                        m = GO_IMPORT.search(stripped)
                        if m:
                            edges.append({'source': source, 'target': m.group(1), 'lang': 'go'})
    return edges
