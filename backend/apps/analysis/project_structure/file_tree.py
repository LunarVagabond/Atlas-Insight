from pathlib import Path

EXT_LANG: dict[str, str] = {
    '.py': 'Python', '.pyw': 'Python',
    '.js': 'JavaScript', '.mjs': 'JavaScript', '.cjs': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript', '.jsx': 'JavaScript',
    '.go': 'Go',
    '.rs': 'Rust',
    '.java': 'Java',
    '.kt': 'Kotlin', '.kts': 'Kotlin',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.cs': 'C#',
    '.cpp': 'C++', '.cxx': 'C++', '.cc': 'C++',
    '.c': 'C',
    '.h': 'C/C++ Header', '.hpp': 'C++ Header',
    '.swift': 'Swift',
    '.scala': 'Scala',
    '.vue': 'Vue',
    '.svelte': 'Svelte',
    '.dart': 'Dart',
    '.r': 'R',
    '.sh': 'Shell', '.bash': 'Shell', '.zsh': 'Shell',
    '.html': 'HTML', '.htm': 'HTML',
    '.css': 'CSS', '.scss': 'SCSS', '.sass': 'SASS', '.less': 'Less',
    '.sql': 'SQL',
    '.tf': 'Terraform', '.hcl': 'Terraform',
    '.proto': 'Protobuf',
    '.lua': 'Lua',
    '.ex': 'Elixir', '.exs': 'Elixir',
    '.clj': 'Clojure',
    '.hs': 'Haskell',
    '.elm': 'Elm',
    '.gleam': 'Gleam',
    '.zig': 'Zig',
}

SKIP_DIRS = {
    '.git', 'node_modules', '.venv', 'venv', 'env', '__pycache__',
    '.mypy_cache', '.pytest_cache', 'dist', 'build', '.next', '.nuxt',
    'target', 'vendor', '.cargo', '.gradle', 'coverage', '.nyc_output',
    '.tox', 'htmlcov', '.eggs', '*.egg-info',
}

NON_SOURCE_LANGS = {'YAML', 'JSON', 'HTML', 'CSS', 'SCSS', 'SASS', 'Less', 'Shell', 'SQL'}


def walk_files(base: Path, max_files: int = 25000):
    count = 0
    for path in base.rglob('*'):
        if count >= max_files:
            break
        if path.is_file():
            rel = path.relative_to(base)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            count += 1
            yield path


def is_test_file(path: Path, base: Path) -> bool:
    rel = path.relative_to(base)
    name = path.stem.lower()
    parts_lower = [p.lower() for p in rel.parts]
    if any(p in ('test', 'tests', '__tests__', 'spec', 'specs', 'e2e') for p in parts_lower):
        return True
    return (
        name.startswith('test_')
        or name.endswith('_test')
        or name.endswith('.test')
        or name.endswith('.spec')
        or name.endswith('_spec')
        or name.startswith('spec_')
    )


def find_file(base: Path, candidates: list[str]) -> str | None:
    for name in candidates:
        if (base / name).exists():
            return name
    return None
