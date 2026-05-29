import re
from pathlib import Path

README_CANDIDATES = [
    'README.md', 'README.rst', 'README.txt', 'README',
    'readme.md', 'readme.rst', 'readme.txt', 'readme',
    'Readme.md', 'Readme.rst',
]


def parse_readme(repo_dir: str) -> dict:
    base = Path(repo_dir)
    readme_path = None
    for name in README_CANDIDATES:
        p = base / name
        if p.exists():
            readme_path = p
            break

    if readme_path is None:
        return {
            'found': False,
            'filename': None,
            'description': None,
            'sections': [],
            'badge_count': 0,
            'word_count': 0,
            'has_installation': False,
            'has_usage': False,
            'has_contributing': False,
            'has_changelog': False,
            'has_license': False,
            'has_api_docs': False,
        }

    try:
        content = readme_path.read_text(errors='ignore')
    except Exception:
        content = ''

    description = _extract_description(content)
    sections = [
        m.group(1).strip()
        for m in re.finditer(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
    ]
    badge_count = len(re.findall(r'\[!\[', content))
    lower = content.lower()

    return {
        'found': True,
        'filename': readme_path.name,
        'description': description,
        'sections': sections[:30],
        'badge_count': badge_count,
        'word_count': len(content.split()),
        'has_installation': bool(re.search(r'\binstall', lower)),
        'has_usage': bool(re.search(r'\busage\b|\bgetting.started\b', lower)),
        'has_contributing': bool(re.search(r'\bcontribut', lower)),
        'has_changelog': bool(re.search(r'\bchangelog\b|\bhistory\b|\brelease.notes\b', lower)),
        'has_license': bool(re.search(r'\blicen[sc]e\b', lower)),
        'has_api_docs': bool(re.search(r'\bapi\b|\bapi.reference\b|\bendpoints\b', lower)),
    }


def _extract_description(content: str) -> str | None:
    lines = content.splitlines()
    paragraph_lines: list[str] = []
    in_para = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            if in_para and paragraph_lines:
                break
            continue
        if re.match(r'^\[!\[|^!\[', stripped):
            if in_para and paragraph_lines:
                break
            continue
        if not stripped:
            if in_para and paragraph_lines:
                break
            continue
        in_para = True
        paragraph_lines.append(stripped)
        if len(' '.join(paragraph_lines)) > 600:
            break

    if not paragraph_lines:
        return None

    result = ' '.join(paragraph_lines)
    if len(result) > 350:
        truncated = result[:350]
        last_period = truncated.rfind('.')
        if last_period > 100:
            result = truncated[: last_period + 1]
        else:
            result = truncated.rstrip() + '…'
    return result
