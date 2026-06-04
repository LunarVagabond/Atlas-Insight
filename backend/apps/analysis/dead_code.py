import os
from pathlib import Path

_ENTRY_FILENAMES = {
    'main.py', 'main.go', 'main.js', 'main.ts', 'main.rs',
    'app.py', 'app.js', 'app.ts',
    'server.py', 'server.js', 'server.ts',
    'index.js', 'index.ts', 'index.mjs',
    '__main__.py', 'manage.py', 'wsgi.py', 'asgi.py',
    'setup.py', 'setup.cfg', 'conftest.py',
    'cli.py', 'run.py',
    'vite.config.ts', 'vite.config.js',
    'webpack.config.js', 'rollup.config.js',
    'jest.config.js', 'jest.config.ts',
    'tailwind.config.js', 'tailwind.config.ts',
    'postcss.config.js',
}

_ENTRY_DIRS = {
    'scripts', 'bin', 'cmd', 'migrations', 'fixtures',
    'examples', 'docs', 'tests', 'test', '__tests__',
}
_SKIP_SUFFIXES = {'.test.ts', '.test.js', '.test.py', '.spec.ts', '.spec.js', '.d.ts', '.min.js'}
_MIN_EDGES_FOR_SIGNAL = 20
_MAX_RESULTS = 100

_LANG_MAP = {
    '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
    '.tsx': 'TypeScript', '.jsx': 'JavaScript',
    '.go': 'Go', '.rs': 'Rust', '.rb': 'Ruby',
    '.java': 'Java', '.php': 'PHP', '.cs': 'C#',
}


def _is_entry_point(rel_path: str) -> bool:
    p = Path(rel_path)
    if p.name in _ENTRY_FILENAMES:
        return True
    parts = set(p.parts[:-1])
    if parts & _ENTRY_DIRS:
        return True
    name_lower = p.name.lower()
    for suffix in _SKIP_SUFFIXES:
        if name_lower.endswith(suffix):
            return True
    if 'test' in name_lower or 'spec' in name_lower or 'mock' in name_lower:
        return True
    return False


def analyze_dead_code(edges: list[dict], repo_dir: str) -> dict:
    if len(edges) < _MIN_EDGES_FOR_SIGNAL:
        return {
            'unreferenced': [],
            'count': 0,
            'filtered_entry_points': 0,
            'note': (
                f'Import graph too sparse ({len(edges)} edges)'
                ' — dead code signal unreliable for this repo'
            ),
        }

    in_degree: dict[str, int] = {}
    all_sources: set[str] = set()

    for edge in edges:
        src = edge.get('source', '')
        tgt = edge.get('target', '')
        if src:
            all_sources.add(src)
            in_degree.setdefault(src, 0)
        if tgt:
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    root = Path(repo_dir)
    existing_files: set[str] = set()
    try:
        for p in root.rglob('*'):
            if p.is_file():
                existing_files.add(str(p.relative_to(root)))
    except OSError:
        pass

    unreferenced = []
    filtered_count = 0

    for filepath, degree in in_degree.items():
        if degree > 0:
            continue
        if filepath not in all_sources:
            continue
        if filepath not in existing_files:
            continue
        if _is_entry_point(filepath):
            filtered_count += 1
            continue

        ext = os.path.splitext(filepath)[1]
        lang = _LANG_MAP.get(ext, ext.lstrip('.').upper() if ext else 'Unknown')
        unreferenced.append({'file': filepath, 'lang': lang})

        if len(unreferenced) >= _MAX_RESULTS:
            break

    unreferenced.sort(key=lambda x: x['file'])

    return {
        'unreferenced': unreferenced,
        'count': len(unreferenced),
        'filtered_entry_points': filtered_count,
        'note': None,
    }
