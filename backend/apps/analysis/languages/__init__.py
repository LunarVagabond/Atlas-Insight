from __future__ import annotations

import importlib
import pkgutil
from functools import lru_cache
from pathlib import Path

from .base import LanguagePlugin

_PLUGINS: list[LanguagePlugin] | None = None


def _load_plugins() -> list[LanguagePlugin]:
    global _PLUGINS
    if _PLUGINS is not None:
        return _PLUGINS
    plugins: list[LanguagePlugin] = []
    pkg_dir = Path(__file__).parent
    for _finder, name, _ispkg in pkgutil.iter_modules([str(pkg_dir)]):
        if name == 'base':
            continue
        mod = importlib.import_module(f'.{name}', package=__name__)
        if hasattr(mod, 'plugin') and isinstance(mod.plugin, LanguagePlugin):
            plugins.append(mod.plugin)
    _PLUGINS = plugins
    return plugins


# ── Public API ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _ext_index() -> dict[str, LanguagePlugin]:
    return {ext: p for p in _load_plugins() for ext in p.extensions}


def get_plugin(ext: str) -> LanguagePlugin | None:
    """Return the plugin for a file extension (e.g. '.py'), or None."""
    return _ext_index().get(ext)


def all_plugins() -> list[LanguagePlugin]:
    return list(_load_plugins())


@lru_cache(maxsize=None)
def all_manifest_filenames() -> frozenset[str]:
    """Union of manifest_filenames across all plugins — replaces _DEP_FILENAMES in pr_impact.py."""
    return frozenset(f for p in _load_plugins() for f in p.manifest_filenames)


@lru_cache(maxsize=None)
def all_manifest_dep_files() -> frozenset[str]:
    """Union of manifest_dep_files across all plugins — replaces hardcoded list in _dep_files_in_dir."""
    return frozenset(f for p in _load_plugins() for f in p.manifest_dep_files)


@lru_cache(maxsize=None)
def ext_to_lang_name() -> dict[str, str]:
    """Replacement for LANG_EXT_MAP in repo_type.py."""
    return {ext: p.name for p in _load_plugins() for ext in p.extensions}
