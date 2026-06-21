"""Subsystem ownership analysis — derived from static analysis data, no git blame required."""
import collections
import logging

from .arch_tours import SUBSYSTEM_LABELS, SUBSYSTEM_PATTERNS, _detect_subsystem_type
from .project_structure import SKIP_DIRS

logger = logging.getLogger(__name__)

_EXT_LANG: dict[str, str] = {
    '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript', '.tsx': 'TypeScript',
    '.jsx': 'JavaScript', '.go': 'Go', '.rs': 'Rust', '.java': 'Java',
    '.rb': 'Ruby', '.php': 'PHP', '.cs': 'C#', '.cpp': 'C++', '.c': 'C',
    '.vue': 'Vue', '.svelte': 'Svelte', '.scss': 'SCSS', '.css': 'CSS',
    '.sql': 'SQL', '.sh': 'Shell', '.yaml': 'YAML', '.yml': 'YAML',
}


def _primary_language(files: list[str]) -> str:
    counts: dict[str, int] = collections.Counter()
    for f in files:
        ext = '.' + f.rsplit('.', 1)[-1].lower() if '.' in f.split('/')[-1] else ''
        lang = _EXT_LANG.get(ext)
        if lang:
            counts[lang] += 1
    return counts.most_common(1)[0][0] if counts else ''


def analyze_ownership(structure: dict, commits: dict, graph: dict) -> dict:
    try:
        return _analyze(structure, commits, graph)
    except Exception:
        logger.exception('ownership_analysis failed — returning empty dict')
        return {}


def _analyze(structure: dict, commits: dict, graph: dict) -> dict:
    all_files: list[str] = structure.get('all_files') or []
    if not all_files:
        return {}

    hot_file_map: dict[str, int] = {h['file']: h['commit_count'] for h in structure.get('hot_files', [])}
    god_module_set: set[str] = {g['module'] for g in graph.get('god_modules', [])}
    god_in_degree: dict[str, int] = {g['module']: g['in_degree'] for g in graph.get('god_modules', [])}
    total_hot_commits = max(sum(hot_file_map.values()), 1)

    # Group files by top-level dir (monorepo heuristic matches arch_tours)
    dir_files: dict[str, list[str]] = collections.defaultdict(list)
    for f in all_files:
        parts = f.split('/')
        top = parts[0] if len(parts) > 1 else ''
        if top:
            dir_files[top].append(f)

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

    subsystems = []
    for dir_name, files in sorted(dir_files.items(), key=lambda kv: -len(kv[1])):
        top = dir_name.split('/')[0]
        if top in SKIP_DIRS or len(files) < 5:
            continue

        subsystem_set = set(files)
        stype = _detect_subsystem_type(dir_name)

        # Hot files within this subsystem
        sub_hot = [
            {'file': f, 'commit_count': hot_file_map[f]}
            for f in sorted(hot_file_map, key=lambda x: -hot_file_map[x])
            if f in subsystem_set
        ][:5]

        # Activity score: fraction of total hot-file commit activity
        activity_commits = sum(h['commit_count'] for h in sub_hot)
        activity_score = round(activity_commits / total_hot_commits, 3)

        # God modules within this subsystem
        sub_gods = [
            {'module': m, 'in_degree': god_in_degree[m]}
            for m in god_module_set
            if m in subsystem_set
        ]

        sub_name = f'{dir_name}/' if stype == 'other' else f'{SUBSYSTEM_LABELS.get(stype, dir_name)} ({dir_name}/)'
        subsystems.append({
            'id': dir_name.replace('/', '_'),
            'name': sub_name,
            'subsystem_type': stype,
            'file_count': len(files),
            'activity_score': activity_score,
            'hot_files': sub_hot,
            'god_modules': sub_gods,
            'primary_language': _primary_language(files),
        })

        if len(subsystems) >= 10:
            break

    return {
        'subsystems': subsystems,
        'top_contributors': structure.get('top_contributors', []),
        'bus_factor': structure.get('bus_factor', 0),
    }
