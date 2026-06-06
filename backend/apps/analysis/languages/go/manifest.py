from pathlib import Path


def parse_manifest(path: Path) -> list[dict]:
    deps = []
    in_require = False
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        if line.startswith('require ('):
            in_require = True
            continue
        if in_require and line == ')':
            in_require = False
            continue
        if in_require or line.startswith('require '):
            line = line.removeprefix('require ').strip()
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith('//'):
                deps.append({'name': parts[0], 'version_spec': parts[1], 'source': 'go.mod'})
    return deps
