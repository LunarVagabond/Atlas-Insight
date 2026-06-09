from typing import Literal

from .license_analysis import _COPYLEFT_IDS, _PERMISSIVE_IDS

ScoringMode = Literal['oss', 'closed_source']

_OSI_SPDX = _PERMISSIVE_IDS | _COPYLEFT_IDS


def infer_scoring_mode(
    *,
    is_private: bool = False,
    github_meta: dict | None = None,
    structure: dict | None = None,
) -> tuple[ScoringMode, str]:
    meta = github_meta or {}
    struct = structure or {}

    if is_private or meta.get('is_private'):
        return 'closed_source', 'private repository'

    has_license = bool(
        struct.get('license_type') or struct.get('license_file') or meta.get('license_spdx')
    )
    has_contributing = bool(struct.get('has_contributing'))

    if has_license and has_contributing:
        return 'oss', 'public repository with open-source community files'

    spdx = meta.get('license_spdx')
    if spdx and spdx in _OSI_SPDX:
        return 'oss', 'public repository with OSI-recognized license'

    return 'closed_source', 'public repository without clear open-source signals'
