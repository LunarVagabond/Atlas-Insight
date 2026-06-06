from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

IsExternalFn = Callable[[str], bool]
ExtractEdgesFn = Callable[[str, str, str], list[str]]      # fpath, content, repo_dir -> dep strings
ExtractTestRefsFn = Callable[[str, str, str], set[str]]    # test_rel, test_dir, content -> path stems
ParseManifestFn = Callable[[Path], list[dict]]             # manifest path -> [{name, version_spec, ...}]


@dataclass(frozen=True)
class LanguagePlugin:
    # ── Identity ──────────────────────────────────────────────────────────
    name: str
    extensions: tuple[str, ...]

    # ── import_parser.py ──────────────────────────────────────────────────
    # Simple languages: set import_re + is_external; dispatcher uses them directly.
    # Complex languages (Go block imports, JS relative resolution, Vue extraction):
    # set extract_edges instead — it receives (fpath, content, repo_dir) and returns
    # the raw dep strings to emit. import_re and is_external are ignored when
    # extract_edges is set.
    import_re: re.Pattern | None = None
    is_external: IsExternalFn | None = None
    extract_edges: ExtractEdgesFn | None = None
    lang_label: str = ''

    # ── complexity.py ─────────────────────────────────────────────────────
    # (test_rel, test_dir, content) -> set of normalized path stems referenced
    # by imports in the test file. Used to detect whether a hotspot file is tested.
    extract_test_refs: ExtractTestRefsFn | None = None

    # ── dep_report.py ─────────────────────────────────────────────────────
    # All manifest filenames this language uses (exact basenames).
    # parse_manifest dispatches internally by path.name if multiple formats exist.
    manifest_filenames: tuple[str, ...] = field(default_factory=tuple)
    parse_manifest: ParseManifestFn | None = None

    # ── vuln_scan.py ──────────────────────────────────────────────────────
    vuln_ecosystem: str | None = None   # OSV ecosystem name: PyPI, npm, crates.io, etc.

    # ── repo_type.py ──────────────────────────────────────────────────────
    # Subset of manifest_filenames that indicate a real project root (used by
    # _dep_files_in_dir to decide whether a directory is a sub-project).
    manifest_dep_files: tuple[str, ...] = field(default_factory=tuple)

    # ── test_coverage.py ──────────────────────────────────────────────────
    # {framework_name: {signature_file_or_pattern, ...}}
    test_frameworks: dict[str, set[str]] = field(default_factory=dict)

    # ── tech_stack.py augmentation ────────────────────────────────────────
    # New-language entries only; the 200+ existing FRAMEWORK_SIGNALS entries
    # stay flat in tech_stack.py. These are merged in at module load.
    framework_signals: dict[str, str] = field(default_factory=dict)
    framework_file_patterns: dict[str, str] = field(default_factory=dict)

    # ── scaffold reminder (not used by backend logic) ─────────────────────
    tier: Literal['full', 'dependencies'] = 'full'
