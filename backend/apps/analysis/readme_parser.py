import re
from pathlib import Path

README_CANDIDATES = [
    'README.md', 'README.rst', 'README.txt', 'README',
    'readme.md', 'readme.rst', 'readme.txt', 'readme',
    'Readme.md', 'Readme.rst',
]

DOC_LINK_PATTERNS = [
    (r'(^|\.)docs\.', 'Docs Site', 'Documentation website'),
    (r'readthedocs\.io', 'Read the Docs', 'Read the Docs hosted documentation'),
    (r'confluence\.', 'Confluence', 'Confluence knowledge base'),
    (r'notion\.so', 'Notion', 'Notion docs workspace'),
    (r'/wiki(/|$)', 'Wiki', 'Project wiki'),
    (r'/docs(/|$)', 'Docs', 'Documentation section'),
    (r'/documentation(/|$)', 'Documentation', 'Documentation section'),
]

SOCIAL_LINK_PATTERNS = [
    (r'discord\.gg|discord\.com/invite', 'Discord', 'Community chat'),
    (r'slack\.com|slack\.com/invite', 'Slack', 'Team and community chat'),
    (r'twitter\.com|x\.com', 'X', 'Project updates and announcements'),
    (r'linkedin\.com', 'LinkedIn', 'Organization profile'),
    (r'reddit\.com/r/', 'Reddit', 'Community forum'),
    (r'youtube\.com|youtu\.be', 'YouTube', 'Video content and demos'),
    (r't\.me|telegram\.me|telegram\.org', 'Telegram', 'Community channel'),
    (r'matrix\.to|matrix\.org', 'Matrix', 'Open chat network'),
    (r'gitter\.im', 'Gitter', 'Developer chat room'),
    (r'mastodon\.', 'Mastodon', 'Decentralized social profile'),
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
            'content': None,
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
            'docs_links': [],
            'social_links': [],
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
    links = _extract_links(content)

    code_block_count = len(re.findall(r'```', content)) // 2
    has_external_links = any(
        link for link in links
        if not re.search(r'github\.com|shields\.io|badge|img\.shields', link, re.IGNORECASE)
    )
    section_word_counts = _compute_section_word_counts(content)
    shallow_sections = [
        s for s, wc in section_word_counts.items() if wc < 20
    ]

    return {
        'found': True,
        'filename': readme_path.name,
        'content': content[:50_000] if content else None,
        'description': description,
        'sections': sections[:30],
        'badge_count': badge_count,
        'word_count': len(content.split()),
        'code_block_count': code_block_count,
        'has_external_links': has_external_links,
        'shallow_sections': shallow_sections[:10],
        'has_installation': bool(re.search(r'\binstall', lower)),
        'has_usage': bool(re.search(r'\busage\b|\bgetting.started\b', lower)),
        'has_contributing': bool(re.search(r'\bcontribut', lower)),
        'has_changelog': bool(re.search(r'\bchangelog\b|\bhistory\b|\brelease.notes\b', lower)),
        'has_license': bool(re.search(r'\blicen[sc]e\b', lower)),
        'has_api_docs': bool(re.search(r'\bapi\b|\bapi.reference\b|\bendpoints\b', lower)),
        'docs_links': _detect_docs_links(links),
        'social_links': _detect_social_links(links),
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


def _extract_links(content: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()

    def _add(url: str) -> None:
        clean = url.strip().rstrip(').,;!\"\'')
        if clean.startswith('http://') or clean.startswith('https://'):
            if clean not in seen:
                seen.add(clean)
                links.append(clean)

    for match in re.finditer(r'\[[^\]]+\]\((https?://[^)\s]+)\)', content):
        _add(match.group(1))

    for match in re.finditer(r'https?://[^\s<>)\]]+', content):
        _add(match.group(0))

    return links[:150]


def _detect_docs_links(links: list[str]) -> list[dict]:
    results: list[dict] = []
    for url in links:
        low = url.lower()
        for pattern, label, description in DOC_LINK_PATTERNS:
            if re.search(pattern, low):
                results.append({
                    'label': label,
                    'url': url,
                    'source': 'readme',
                    'description': description,
                })
                break
    return _dedupe_link_dicts(results)


def _detect_social_links(links: list[str]) -> list[dict]:
    results: list[dict] = []
    for url in links:
        low = url.lower()
        for pattern, platform, description in SOCIAL_LINK_PATTERNS:
            if re.search(pattern, low):
                results.append({
                    'platform': platform,
                    'label': platform,
                    'url': url,
                    'source': 'readme',
                    'description': description,
                })
                break
    return _dedupe_link_dicts(results)


def _compute_section_word_counts(content: str) -> dict[str, int]:
    """Return word count per top-level section heading."""
    result: dict[str, int] = {}
    current_section: str | None = None
    current_words: list[str] = []

    for line in content.splitlines():
        m = re.match(r'^#{1,3}\s+(.+)$', line)
        if m:
            if current_section is not None:
                result[current_section] = len(current_words)
            current_section = m.group(1).strip()
            current_words = []
        elif current_section is not None:
            current_words.extend(line.split())

    if current_section is not None:
        result[current_section] = len(current_words)

    return result


def _dedupe_link_dicts(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        url = item.get('url')
        if not isinstance(url, str) or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped
