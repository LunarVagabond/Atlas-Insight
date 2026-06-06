# Language Plugins

Each sub-folder is one language plugin. The registry (`__init__.py` in this directory) auto-discovers them at startup via `pkgutil.iter_modules` — no manual registration needed.

## Folder structure

```
languages/
  <lang>/
    edges.py      # Import graph: regex, stdlib filter, extract_edges()
    tests.py      # Test coverage: extract_test_refs()  (or = None)
    manifest.py   # Dep parsing:  parse_manifest()       (or = None)
    __init__.py   # Assembles plugin = LanguagePlugin(...)
  base.py         # LanguagePlugin dataclass + type aliases
  __init__.py     # Registry: get_plugin(), all_plugins(), derived helpers
```

Each file has exactly one responsibility. `__init__.py` is a thin assembler — it imports from the three modules and defines the `plugin` object. The registry picks up `plugin` automatically.

## Reference implementation

**Go** (`go/`) is the gold standard for a complex language:
- `edges.py` — block-import state machine, per-repo module path caching with `@lru_cache`
- `tests.py` — string-literal import scanning
- `manifest.py` — `go.mod` block/single `require` parsing

**Python** (`python/`) is the gold standard for a language with multiple manifest formats:
- `manifest.py` — dispatches by filename to `_parse_requirements` or `_parse_pyproject`

**JavaScript** (`javascript/`) covers multi-extension + embedded scripts:
- `edges.py` — Vue `<script>` stripping, relative-import filtering

For simple languages with no manifest or test refs, see **Lua** (`lua/`) — `tests.py` and `manifest.py` are just `= None` stubs.

## Adding a new language

```bash
make new-language          # interactive prompt
make new-language LANG=Zig # bypass prompt
```

See `docs/dev/adding-a-language.md` for the full step-by-step guide.
