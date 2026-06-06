import re
from pathlib import Path


def parse_manifest(path: Path) -> list[dict]:
    if path.name == 'pom.xml':
        return _parse_pom(path)
    return _parse_gradle(path)


def _parse_gradle(path: Path) -> list[dict]:
    deps = []
    for line in path.read_text(errors='ignore').splitlines():
        line = line.strip()
        m = re.search(
            r"""(?:implementation|api|compile|testImplementation|runtimeOnly)\s+['"]([^'"]+)['"]""",
            line,
        )
        if m:
            coords = m.group(1).split(':')
            if len(coords) >= 2:
                name = f'{coords[0]}/{coords[1]}'
                deps.append({'name': name, 'version_spec': coords[2] if len(coords) > 2 else '', 'source': path.name})
    return deps


def _parse_pom(path: Path) -> list[dict]:
    deps = []
    try:
        content = path.read_text(errors='ignore')
        for m in re.finditer(
            r'<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>(?:\s*<version>([^<]+)</version>)?',
            content,
        ):
            name = f'{m.group(1).strip()}/{m.group(2).strip()}'
            deps.append({'name': name, 'version_spec': (m.group(3) or '').strip(), 'source': 'pom.xml'})
    except Exception:
        pass
    return deps
