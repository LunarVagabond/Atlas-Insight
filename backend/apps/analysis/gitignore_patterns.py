GITIGNORE_RECOMMENDED = [
    '.env', '*.pem', '*.key', 'id_rsa', 'node_modules',
    '__pycache__', '.venv', 'venv', '*.log', 'dist/',
]

GITIGNORE_SHOULD_NOT_TRACK = [
    '.env', '*.pem', '*.key', 'id_rsa', 'node_modules',
    '__pycache__', '.venv', 'venv', '*.log', 'dist/',
    'build/', 'coverage/', '*.tmp', '*.bak', '.DS_Store',
    'Thumbs.db', '*.swp', '*.swo',
]


def gitignore_covers(pattern: str, gi_lines_lower: list[str]) -> bool:
    pat = pattern.rstrip('/')
    for raw in gi_lines_lower:
        line = raw.rstrip('/')
        if line.startswith('**/'):
            line = line[3:]
        if line.startswith('/'):
            line = line[1:]

        if line == pat:
            return True
        if line.endswith(f'/{pat}'):
            return True
        if pat.startswith('*.') and line.endswith(pat[1:]):
            return True
        if pat.startswith('.') and (line == pat or line.startswith(f'{pat}.')):
            return True
    return False


def path_matches_gitignore_pattern(path: str, pattern: str) -> bool:
    path_lower = path.lower()
    pattern_lower = pattern.lower()

    if pattern_lower.endswith('/'):
        dir_name = pattern_lower.rstrip('/')
        return f'/{dir_name}/' in f'/{path_lower}/' or path_lower.startswith(f'{dir_name}/')

    pat = pattern_lower
    if pat.startswith('*.'):
        return path_lower.endswith(pat[1:])

    if '/' in pat:
        return pat in path_lower or path_lower.endswith(f'/{pat}')

    name = path_lower.rsplit('/', 1)[-1]
    if pat.startswith('.'):
        return name == pat or name.startswith(f'{pat}.')
    return name == pat
