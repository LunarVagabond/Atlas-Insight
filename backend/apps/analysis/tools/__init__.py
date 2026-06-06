from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from .base import ToolPlugin

logger = logging.getLogger(__name__)

_PLUGINS: list[ToolPlugin] | None = None


def _load_plugins() -> list[ToolPlugin]:
    global _PLUGINS
    if _PLUGINS is not None:
        return _PLUGINS
    plugins: list[ToolPlugin] = []
    pkg_dir = Path(__file__).parent
    for _finder, name, _ispkg in pkgutil.iter_modules([str(pkg_dir)]):
        if name == 'base':
            continue
        mod = importlib.import_module(f'.{name}', package=__name__)
        if hasattr(mod, 'plugin') and isinstance(mod.plugin, ToolPlugin):
            plugins.append(mod.plugin)
    _PLUGINS = plugins
    return plugins


def all_plugins() -> list[ToolPlugin]:
    return list(_load_plugins())


def _is_present(plugin: ToolPlugin, root: Path) -> bool:
    for fname in plugin.detect_files:
        if next(root.rglob(fname), None):
            return True
    for ext in plugin.detect_exts:
        if next(root.rglob(f'*{ext}'), None):
            return True
    for dname in plugin.detect_dirs:
        if next(root.rglob(dname), None):
            return True
    return False


def detect_tools(repo_dir: str) -> dict[str, dict]:
    """Detect and analyze all tools present in repo_dir. Returns {slug: result_dict}."""
    root = Path(repo_dir)
    results: dict[str, dict] = {}
    for plugin in _load_plugins():
        try:
            if _is_present(plugin, root) and plugin.analyze is not None:
                results[plugin.slug] = plugin.analyze(repo_dir)
        except Exception:
            logger.warning('Tool plugin %s failed', plugin.slug, exc_info=True)
    return results
