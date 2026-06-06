# Tool Plugins

Each sub-folder is one infrastructure tool plugin. The registry (`__init__.py` in this directory) auto-discovers them at startup via `pkgutil.iter_modules` — no manual registration needed.

## Folder structure

```
tools/
  <tool>/
    analysis.py   # Detection + analysis logic, returns result dict
    __init__.py   # Assembles plugin = ToolPlugin(...)
  base.py         # ToolPlugin dataclass + type aliases
  __init__.py     # Registry: all_plugins(), detect_tools()
```

`detect_tools(repo_dir)` runs every plugin whose detection signals match, returns `{slug: result_dict}`. Results land in `result['tools']` with `result['containers']` as a backward-compat alias for Docker.

## Reference implementations

**Docker** (`docker/`) — minimal plugin: `analysis.py` delegates entirely to the existing `container_analysis.py`. Good reference for wrapping an existing analyzer.

**Terraform** (`terraform/`) — full plugin: HCL file walking via `python-hcl2`, provider/resource extraction, security regex scans, hygiene scoring. Good reference for a new analysis from scratch.

## Adding a new tool

```bash
make new-tool               # interactive prompt
make new-tool TOOL=Helm     # bypass prompt
```

See `docs/dev/adding-a-tool.md` for the full step-by-step guide.
