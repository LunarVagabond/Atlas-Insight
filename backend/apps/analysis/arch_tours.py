"""Generate curated architecture tours from existing analysis data."""
import collections
import logging

from .project_structure import SKIP_DIRS

logger = logging.getLogger(__name__)

SUBSYSTEM_PATTERNS: dict[str, list[str]] = {
    'frontend': ['src', 'frontend', 'client', 'ui', 'app', 'web', 'pages', 'components'],
    'api':      ['api', 'routes', 'routers', 'endpoints', 'controllers', 'views', 'handlers', 'server'],
    'data':     ['models', 'db', 'database', 'migrations', 'schemas', 'entities', 'repositories'],
    'tests':    ['tests', '__tests__', 'spec', 'specs', 'test', 'e2e', 'integration'],
    'config':   ['.github', 'config', 'scripts', 'ci', 'infra', 'deploy', 'k8s', 'docker'],
    'docs':     ['docs', 'documentation', 'doc', 'wiki'],
}

SUBSYSTEM_LABELS: dict[str, str] = {
    'frontend': 'Frontend',
    'api':      'API / Backend',
    'data':     'Data / Models',
    'tests':    'Tests',
    'config':   'Config / CI',
    'docs':     'Documentation',
    'other':    'General',
}

SUBSYSTEM_DESCRIPTIONS: dict[str, str] = {
    'frontend': 'User interface components, views, and client-side logic.',
    'api':      'API routes, request handlers, and server-side business logic.',
    'data':     'Data models, database schemas, migrations, and persistence layer.',
    'tests':    'Test suites covering unit, integration, and end-to-end scenarios.',
    'config':   'Configuration files, CI/CD pipelines, and infrastructure definitions.',
    'docs':     'Project documentation, guides, and reference material.',
    'other':    'Supporting files and utilities.',
}

ENTRY_FILENAMES = frozenset({
    'index.py', 'index.js', 'index.ts', 'index.tsx', 'index.jsx',
    'main.py', 'main.js', 'main.ts',
    '__init__.py', 'app.py', 'app.js', 'app.ts', 'server.py', 'server.js', 'server.ts',
    'mod.rs', 'lib.rs', 'main.rs',
})

# These files are frequently empty or trivial boilerplate — deprioritise in tours
BORING_FILENAMES = frozenset({'__init__.py', '__main__.py'})

EXT_LABELS: dict[str, str] = {
    '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', '.tsx': 'TypeScript/JSX',
    '.jsx': 'JavaScript/JSX', '.go': 'Go', '.rs': 'Rust', '.java': 'Java',
    '.rb': 'Ruby', '.php': 'PHP', '.cs': 'C#', '.cpp': 'C++', '.c': 'C',
    '.vue': 'Vue component', '.svelte': 'Svelte component',
    '.scss': 'Styles', '.css': 'Styles', '.sql': 'SQL', '.sh': 'Shell script',
    '.md': 'Documentation', '.yaml': 'Config', '.yml': 'Config', '.toml': 'Config',
    '.json': 'Config/Data', '.xml': 'Config/Data',
}


def _is_boring(path: str) -> bool:
    return path.split('/')[-1] in BORING_FILENAMES


def _generate_description(
    dir_name: str,
    subsystem_type: str,
    files: list[str],
    key_files: list[dict],
) -> str:
    base = SUBSYSTEM_DESCRIPTIONS.get(subsystem_type, '')

    filenames_lower = [f.split('/')[-1].lower() for f in files]

    # Dominant language by file extension
    ext_counts: collections.Counter = collections.Counter(
        '.' + fn.rsplit('.', 1)[-1]
        for fn in filenames_lower
        if '.' in fn
    )
    top_ext = ext_counts.most_common(1)
    lang = EXT_LABELS.get(top_ext[0][0], '') if top_ext else ''

    # Infer specific roles from filenames
    signals: list[str] = []
    if any('migration' in fn or fn == 'migrate.py' for fn in filenames_lower):
        signals.append('database migrations')
    if any('model' in fn for fn in filenames_lower):
        signals.append('data models')
    route_names = {'router.py', 'routes.py', 'views.py', 'controllers.py', 'handlers.py'}
    if any(fn in route_names for fn in filenames_lower):
        signals.append('request handling')
    if any('task' in fn for fn in filenames_lower):
        signals.append('background tasks')
    if any('schema' in fn or 'serializer' in fn for fn in filenames_lower):
        signals.append('schemas / serializers')
    if any(fn.startswith('test_') or fn.endswith('_test.py') or '_spec.' in fn
           for fn in filenames_lower):
        signals.append('tests')

    parts = [base] if base else []

    if lang and subsystem_type == 'other':
        parts.append(f'Primarily {lang}.')

    if signals:
        parts.append(f'Contains: {", ".join(signals)}.')

    if key_files:
        top_name = key_files[0]['file'].split('/')[-1]
        top_count = key_files[0]['commit_count']
        parts.append(f'Most active file: {top_name} ({top_count} commits).')
    elif not base:
        parts.append(f'{len(files)} files in {dir_name}/.')

    return ' '.join(parts)


def _detect_subsystem_type(dir_name: str) -> str:
    lower = dir_name.lower()
    for stype, patterns in SUBSYSTEM_PATTERNS.items():
        if lower in patterns:
            return stype
    return 'other'


def _kahn_topo(nodes: set[str], internal_edges: list[tuple[str, str]]) -> list[str]:
    """Kahn's BFS topological sort. Gracefully handles cycles by appending remainder."""
    in_degree: dict[str, int] = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for src, tgt in internal_edges:
        if src in nodes and tgt in nodes:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    queue = collections.deque(n for n in nodes if in_degree[n] == 0)
    result: list[str] = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Append any nodes stuck in cycles (alphabetically for stability)
    remaining = sorted(n for n in nodes if n not in set(result))
    result.extend(remaining)
    return result


def _file_note(file: str, subsystem_files: set[str], internal_in_degree: dict[str, int], graph_in_degree: dict[str, int]) -> str:
    basename = file.split('/')[-1].lower()
    if basename in ENTRY_FILENAMES:
        return 'Entry point'
    if any(kw in basename for kw in ('util', 'helper', 'common', 'shared', 'base', 'mixin')):
        return 'Utilities'
    if internal_in_degree.get(file, 0) == 0 and len(subsystem_files) > 3:
        return 'Entry point'
    if graph_in_degree.get(file, 0) == max((graph_in_degree.get(f, 0) for f in subsystem_files), default=0):
        if graph_in_degree.get(file, 0) > 0:
            return 'Core logic'
    # Fallback: file type label so no step is completely unlabelled
    ext = '.' + basename.rsplit('.', 1)[-1] if '.' in basename else ''
    return EXT_LABELS.get(ext, '')


def generate_arch_tours(structure: dict, graph: dict, commits: dict) -> list[dict]:
    """Return up to 9 architecture tours (1 overview + up to 8 subsystems)."""
    try:
        return _generate(structure, graph, commits)
    except Exception:
        logger.exception('arch_tours generation failed — returning empty list')
        return []


def _generate(structure: dict, graph: dict, commits: dict) -> list[dict]:
    all_files: list[str] = structure.get('all_files') or []
    if not all_files:
        return []

    # Build graph lookup structures
    graph_in_degree: dict[str, int] = {n['id']: n['in_degree'] for n in graph.get('nodes', [])}
    graph_edges: list[tuple[str, str]] = [(e['source'], e['target']) for e in graph.get('edges', [])]

    # Hot files lookup: file path → commit_count
    hot_file_map: dict[str, int] = {h['file']: h['commit_count'] for h in structure.get('hot_files', [])}

    # Group files by top-level dir
    dir_files: dict[str, list[str]] = collections.defaultdict(list)
    for f in all_files:
        parts = f.split('/')
        top = parts[0] if len(parts) > 1 else ''
        if top:
            dir_files[top].append(f)

    # Monorepo heuristic: if ≥3 top dirs, no single dir holds >40% → use parts[:2]
    top_dirs = [d for d in dir_files if d not in SKIP_DIRS and len(dir_files[d]) >= 3]
    total_files = len(all_files)
    is_monorepo = (
        len(top_dirs) >= 3
        and total_files > 0
        and all(len(dir_files[d]) / total_files <= 0.40 for d in top_dirs)
    )
    if is_monorepo:
        dir_files2: dict[str, list[str]] = collections.defaultdict(list)
        for f in all_files:
            parts = f.split('/')
            key = '/'.join(parts[:2]) if len(parts) > 2 else parts[0] if parts else ''
            if key:
                dir_files2[key].append(f)
        dir_files = dir_files2

    # Build tours for qualifying subsystems
    tours: list[dict] = []

    for dir_name, files in sorted(dir_files.items(), key=lambda kv: -len(kv[1])):
        top = dir_name.split('/')[0]
        if top in SKIP_DIRS:
            continue
        if len(files) < 3:
            continue

        subsystem_type = _detect_subsystem_type(dir_name)
        subsystem_set = set(files)

        # Entry files: highest graph in-degree within subsystem, skip boring boilerplate
        with_degree = sorted(files, key=lambda f: -graph_in_degree.get(f, 0))
        entry_files = [
            f for f in with_degree if graph_in_degree.get(f, 0) > 0 and not _is_boring(f)
        ][:5]
        if not entry_files:
            # Retry including boring files (all __init__.py may be the only option)
            entry_files = [f for f in with_degree if graph_in_degree.get(f, 0) > 0][:5]
        if not entry_files:
            entry_files = [
                f for f in files if f.split('/')[-1] in ENTRY_FILENAMES and not _is_boring(f)
            ][:5]
        if not entry_files:
            entry_files = [f for f in files if f.split('/')[-1] in ENTRY_FILENAMES][:5]
        if not entry_files:
            entry_files = sorted(f for f in files if not _is_boring(f))[:3] or sorted(files)[:3]

        # Key files: hot files within this subsystem
        key_files = [
            {'file': f, 'commit_count': hot_file_map[f]}
            for f in sorted(hot_file_map, key=lambda f: -hot_file_map[f])
            if f in subsystem_set
        ][:5]

        # Reading order: topo sort on internal edges
        internal_edges = [(s, t) for s, t in graph_edges if s in subsystem_set and t in subsystem_set]
        if internal_edges:
            ordered = _kahn_topo(subsystem_set, internal_edges)
        else:
            seen: set[str] = set()
            ordered = []
            for f in entry_files:
                if f not in seen:
                    ordered.append(f)
                    seen.add(f)
            for f in (kf['file'] for kf in key_files):
                if f not in seen:
                    ordered.append(f)
                    seen.add(f)
            ordered.extend(sorted(f for f in files if f not in seen))

        # Build internal in-degree for note annotation
        internal_in_deg: dict[str, int] = collections.defaultdict(int)
        for _, tgt in internal_edges:
            if tgt in subsystem_set:
                internal_in_deg[tgt] += 1

        # Prefer substantive files; fall back to full list only if too few remain
        interesting = [f for f in ordered if not _is_boring(f)]
        ordered_filtered = interesting if len(interesting) >= 3 else ordered

        reading_order = []
        for f in ordered_filtered[:10]:
            note = _file_note(f, subsystem_set, internal_in_deg, graph_in_degree)
            reading_order.append({'file': f, 'note': note})

        label = SUBSYSTEM_LABELS.get(subsystem_type, dir_name)
        desc = _generate_description(dir_name, subsystem_type, files, key_files)

        tours.append({
            'id': f'tour_{dir_name.replace("/", "_")}',
            'name': f'{label} ({dir_name}/)',
            'description': desc,
            'subsystem_type': subsystem_type,
            'file_count': len(files),
            'entry_files': entry_files,
            'key_files': key_files,
            'reading_order': reading_order,
        })

        if len(tours) >= 8:
            break

    if not tours:
        return []

    # Prepend a "Full Repository Overview" tour using top-level dirs as steps
    def _overview_note(d: str) -> str:
        stype = _detect_subsystem_type(d.split('/')[0])
        label = SUBSYSTEM_LABELS.get(stype, '')
        count = len(dir_files[d])
        return f'{label} · {count} files' if label else f'{count} files'

    overview_steps = [
        {'file': f'{d}/', 'note': _overview_note(d)}
        for d in sorted(dir_files, key=lambda k: -len(dir_files[k]))
        if d.split('/')[0] not in SKIP_DIRS and len(dir_files[d]) >= 3
    ][:10]

    # Global entry points: top files by graph in-degree (= most depended-upon)
    all_files_set = set(all_files)
    global_entry_files = [
        f for f in sorted(graph_in_degree, key=lambda x: -graph_in_degree[x])
        if f in all_files_set
        and not any(part in SKIP_DIRS for part in f.split('/'))
        and graph_in_degree[f] > 0
        and not _is_boring(f)
    ][:8]
    # Also include canonical entry filenames if not already present
    entry_set = set(global_entry_files)
    for f in sorted(all_files_set):
        if len(global_entry_files) >= 8:
            break
        if f not in entry_set and f.split('/')[-1] in ENTRY_FILENAMES and not _is_boring(f):
            global_entry_files.append(f)
            entry_set.add(f)

    overview = {
        'id': 'tour_overview',
        'name': 'Full Repository Overview',
        'description': 'Top-level structure of the repository — a map of all major subsystems and primary entry points.',
        'subsystem_type': 'overview',
        'file_count': total_files,
        'entry_files': global_entry_files,
        'key_files': [],
        'reading_order': overview_steps,
    }

    return [overview] + tours
