import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .languages import all_manifest_dep_files, ext_to_lang_name

FRONTEND_DIR_NAMES = {'frontend', 'client', 'web', 'ui', 'app'}
BACKEND_DIR_NAMES = {'backend', 'server', 'api', 'service', 'srv'}
MONOREPO_DIR_NAMES = {'packages', 'apps', 'services', 'modules', 'libs'}
WORKSPACE_CONFIG_FILES = {
    'pnpm-workspace.yaml', 'lerna.json', 'nx.json', 'turbo.json',
    'go.work', '.yarnrc.yml', '.yarnrc.yaml',
}

# Languages handled by plugins + extra display-name-only entries (no plugin needed)
_EXTRA_EXT_MAP = {
    '.ts': 'TypeScript', '.tsx': 'TypeScript',   # JS plugin covers these but under 'JavaScript'
    '.vue': 'Vue',                                 # JS plugin covers .vue but display name is Vue
    '.hs': 'Haskell', '.zig': 'Zig',
    '.sh': 'Shell', '.bash': 'Shell',
    '.nim': 'Nim', '.cr': 'Crystal',
    '.clj': 'Clojure', '.cljs': 'Clojure',
    '.erl': 'Erlang', '.hrl': 'Erlang',
}
LANG_EXT_MAP = {**ext_to_lang_name(), **_EXTRA_EXT_MAP}

_DOC_EXTENSIONS = frozenset({
    '.md', '.mdx', '.rst', '.txt', '.html', '.htm', '.adoc', '.asciidoc',
    '.tex', '.org', '.wiki', '.textile', '.pod',
})

_CODE_EXTENSIONS = frozenset(LANG_EXT_MAP)


@dataclass
class SubProject:
    name: str
    path: str       # relative, e.g. 'frontend/'
    abs_path: str
    dep_files: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


def detect_docs_only(repo_dir: str) -> bool:
    """Return True if the repo is primarily documentation with negligible code."""
    code_count = 0
    doc_count = 0
    skip_dirs = {'.git', 'node_modules', '__pycache__', 'vendor', 'dist', 'build', '.venv', 'venv'}
    try:
        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in _CODE_EXTENSIONS:
                    code_count += 1
                elif ext in _DOC_EXTENSIONS:
                    doc_count += 1
    except OSError:
        return False

    total = code_count + doc_count
    if total < 5:
        return False
    return code_count == 0 or (doc_count / total) >= 0.85


def detect_repo_type(repo_dir: str) -> dict:
    sub_roots, root_has_dep = _find_dep_roots(repo_dir)
    repo_type, detected_by = _classify(repo_dir, sub_roots, root_has_dep)

    if repo_type == 'single':
        return {'type': 'single', 'detected_by': detected_by, 'sub_projects': []}

    for sp in sub_roots:
        sp.languages = _quick_languages(sp.abs_path)

    return {
        'type': repo_type,
        'detected_by': detected_by,
        'sub_projects': [
            {
                'name': sp.name,
                'path': sp.path,
                'abs_path': sp.abs_path,
                'dep_files': sp.dep_files,
                'languages': sp.languages,
            }
            for sp in sub_roots[:20]
        ],
    }


def _find_dep_roots(repo_dir: str) -> tuple[list[SubProject], bool]:
    base = Path(repo_dir)
    root_has_dep = bool(_dep_files_in_dir(base))
    sub_roots: list[SubProject] = []

    try:
        top_entries = [e for e in base.iterdir() if e.is_dir() and not e.name.startswith('.')]
    except OSError:
        return [], root_has_dep

    for top_dir in sorted(top_entries):
        dep_files = _dep_files_in_dir(top_dir)
        if dep_files:
            rel = os.path.relpath(str(top_dir), repo_dir)
            sub_roots.append(SubProject(
                name=top_dir.name,
                path=rel + '/',
                abs_path=str(top_dir),
                dep_files=dep_files,
            ))
        else:
            # One level deeper (for packages/core, apps/web, etc.)
            try:
                second_entries = [e for e in top_dir.iterdir() if e.is_dir() and not e.name.startswith('.')]
            except OSError:
                continue
            for second_dir in sorted(second_entries):
                dep_files2 = _dep_files_in_dir(second_dir)
                if dep_files2:
                    rel = os.path.relpath(str(second_dir), repo_dir)
                    sub_roots.append(SubProject(
                        name=f'{top_dir.name}/{second_dir.name}',
                        path=rel + '/',
                        abs_path=str(second_dir),
                        dep_files=dep_files2,
                    ))

    return sub_roots, root_has_dep


def _dep_files_in_dir(directory: Path) -> list[str]:
    candidates = all_manifest_dep_files()
    # Also include Haskell/non-plugin manifest files not registered in any plugin
    extra = {'stack.yaml', 'cabal.project', 'mix.exs'}
    found = [f for f in (candidates | extra) if (directory / f).exists()]

    pkg_json = directory / 'package.json'
    if pkg_json.exists() and _is_real_package_json(pkg_json) and 'package.json' not in found:
        found.append('package.json')

    return found


def _is_real_package_json(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(errors='ignore'))
    except Exception:
        return False
    has_deps = bool(data.get('dependencies') or data.get('devDependencies') or data.get('name'))
    is_workspace_only = bool(data.get('workspaces')) and not has_deps
    return has_deps and not is_workspace_only


def _classify(
    repo_dir: str,
    sub_roots: list[SubProject],
    root_has_dep: bool,
) -> tuple[str, list[str]]:
    if not sub_roots:
        return 'single', []

    names_lower = {sp.name.lower() for sp in sub_roots}
    top_names_lower = {sp.name.split('/')[0].lower() for sp in sub_roots}

    # 1. fullstack: frontend-like + backend-like dirs with dep files
    has_front = bool(names_lower & FRONTEND_DIR_NAMES or top_names_lower & FRONTEND_DIR_NAMES)
    has_back = bool(names_lower & BACKEND_DIR_NAMES or top_names_lower & BACKEND_DIR_NAMES)
    if has_front and has_back:
        return 'fullstack', ['frontend_backend_dirs', 'dep_files']

    # 2. monorepo: workspace config file at root OR known monorepo dir with ≥2 sub-deps
    base = Path(repo_dir)
    for cfg in WORKSPACE_CONFIG_FILES:
        if (base / cfg).exists():
            return 'monorepo', ['workspace_config']

    for sp in sub_roots:
        top_name = sp.name.split('/')[0].lower()
        if top_name in MONOREPO_DIR_NAMES:
            siblings = [s for s in sub_roots if s.name.split('/')[0].lower() == top_name]
            if len(siblings) >= 2:
                return 'monorepo', ['packages_dir']

    # More than 3 sub-projects = likely monorepo
    if len(sub_roots) >= 3:
        return 'monorepo', ['multiple_dep_roots']

    # 3. microservices: docker-compose with ≥3 services + ≥2 sub-project roots
    if len(sub_roots) >= 2 and _count_docker_compose_services(repo_dir) >= 3:
        return 'microservices', ['docker_compose_services', 'dep_files']

    # 4. single (2 sub-roots but none of the above patterns)
    return 'single', []


def _count_docker_compose_services(repo_dir: str) -> int:
    base = Path(repo_dir)
    for name in ('docker-compose.yml', 'docker-compose.yaml'):
        path = base / name
        if not path.exists():
            continue
        try:
            import yaml  # pyyaml is in backend deps
            data = yaml.safe_load(path.read_text(errors='ignore'))
            if isinstance(data, dict) and isinstance(data.get('services'), dict):
                return len(data['services'])
        except Exception:
            # Fallback: count indented service keys
            try:
                text = path.read_text(errors='ignore')
                count = 0
                in_services = False
                for line in text.splitlines():
                    if line.strip() == 'services:':
                        in_services = True
                        continue
                    if in_services:
                        if line and not line[0].isspace():
                            break
                        if line.startswith('  ') and not line.startswith('    ') and line.strip() and not line.strip().startswith('#'):
                            count += 1
                return count
            except Exception:
                pass
    return 0


def _quick_languages(sub_path: str) -> list[str]:
    counts: dict[str, int] = {}
    try:
        for root, dirs, files in os.walk(sub_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'vendor', 'dist', 'build', '.venv', 'venv')]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                lang = LANG_EXT_MAP.get(ext)
                if lang:
                    counts[lang] = counts.get(lang, 0) + 1
    except OSError:
        pass

    if not counts:
        return []

    total = sum(counts.values())
    # Return languages covering at least 10% of files, sorted by count desc
    return [lang for lang, cnt in sorted(counts.items(), key=lambda x: -x[1]) if cnt / total >= 0.10]
