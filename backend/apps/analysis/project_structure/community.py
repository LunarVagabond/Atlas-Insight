import re
from pathlib import Path

CONTRIBUTING_PATHS = [
    'CONTRIBUTING.md', 'CONTRIBUTING.rst', 'CONTRIBUTING.txt', 'CONTRIBUTING',
    '.github/CONTRIBUTING.md', 'docs/CONTRIBUTING.md', 'docs/contributing.md',
]

LICENSE_PATHS = [
    'LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENSE.rst',
    'LICENSE-MIT', 'LICENSE-APACHE', 'LICENSE-Apache',
    'COPYING', 'COPYING.md', 'COPYING.txt',
    'license', 'license.md', 'license.txt',
]

COC_PATHS = [
    'CODE_OF_CONDUCT.md', '.github/CODE_OF_CONDUCT.md', 'docs/CODE_OF_CONDUCT.md',
]

SECURITY_POLICY_PATHS = [
    'SECURITY.md', '.github/SECURITY.md', 'docs/SECURITY.md',
]

CHANGELOG_PATHS = [
    'CHANGELOG.md', 'CHANGELOG.rst', 'CHANGELOG.txt', 'CHANGELOG',
    'CHANGES.md', 'CHANGES.rst', 'CHANGES', 'HISTORY.md', 'HISTORY.rst',
    'RELEASES.md', 'RELEASE_NOTES.md',
]

_SPDX_MAP = {
    'MIT': r'mit license|permission is hereby granted',
    'Apache-2.0': r'apache license.*2\.0',
    'GPL-3.0': r'gnu general public license.*version 3',
    'GPL-2.0': r'gnu general public license.*version 2',
    'BSD-3-Clause': r'neither the name.*nor the names',
    'BSD-2-Clause': r'redistribution and use in source.*neither',
    'ISC': r'isc license',
    'MPL-2.0': r'mozilla public license.*2\.0',
    'LGPL-2.1': r'gnu lesser general public license.*2\.1',
    'LGPL-3.0': r'gnu lesser general public license.*3',
    'Unlicense': r'this is free and unencumbered',
    'CC0-1.0': r'creative commons.*cc0',
}


def detect_license_type(path: Path) -> str | None:
    try:
        content = path.read_text(errors='ignore').lower()[:2000]
    except Exception:
        return None
    for spdx, pattern in _SPDX_MAP.items():
        if re.search(pattern, content):
            return spdx
    # Legacy simple checks for broad matches not yet in _SPDX_MAP
    if 'gnu lesser general public license' in content:
        return 'LGPL'
    if 'gnu general public license' in content:
        return 'GPL'
    return 'Other'


def parse_license_spdx_from_content(content: str) -> str | None:
    lower = content.lower()
    for spdx, pattern in _SPDX_MAP.items():
        if re.search(pattern, lower):
            return spdx
    return None


def read_community_files(
    base: Path,
    contributing: str | None,
    license_f: str | None,
    coc: str | None,
    security: str | None,
    changelog: str | None,
    max_bytes: int = 12_000,
) -> dict:
    result: dict[str, str | None] = {}
    mapping = {
        'contributing': contributing,
        'license': license_f,
        'coc': coc,
        'security': security,
        'changelog': changelog,
    }
    for key, filename in mapping.items():
        if not filename:
            result[key] = None
            continue
        try:
            content = (base / filename).read_text(errors='replace')
            if len(content) > max_bytes:
                content = content[:max_bytes] + '\n\n[… truncated …]'
            result[key] = content
        except Exception:
            result[key] = None
    return result


def parse_roadmap_file(base: Path, roadmap_file: str | None) -> dict | None:
    if not roadmap_file:
        return None
    try:
        from ..roadmap_parser import parse_roadmap
        content = (base / roadmap_file).read_text(errors='ignore')
        return parse_roadmap(content)
    except Exception:
        return None
