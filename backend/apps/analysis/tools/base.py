from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

AnalyzeFn = Callable[[str], dict]   # repo_dir -> analysis result dict


@dataclass(frozen=True)
class ToolPlugin:
    # ── Identity ──────────────────────────────────────────────────────────
    name: str
    slug: str
    category: Literal['container', 'iac', 'ci', 'build', 'security'] = 'iac'

    # ── Detection — any single match = tool is present ────────────────────
    detect_files: tuple[str, ...] = field(default_factory=tuple)   # exact filenames (rglob)
    detect_exts: tuple[str, ...] = field(default_factory=tuple)    # file extensions e.g. '.tf'
    detect_dirs: tuple[str, ...] = field(default_factory=tuple)    # directory names e.g. '.terraform'

    # ── Analysis ──────────────────────────────────────────────────────────
    analyze: AnalyzeFn | None = None    # called when detected; returns tool result dict
