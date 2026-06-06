# Adding a New Language to Atlas Insight

Language support is a single plugin file. All the old multi-file edits are gone — the registry auto-discovers your plugin at startup and wires it into import parsing, test coverage detection, dependency scanning, vulnerability scanning, and PR impact analysis automatically.

---

## Four steps

| # | Where | What |
|---|-------|------|
| 1 | Terminal | `make new-language` (or `make new-language LANG=kotlin`) |
| 2 | Generated plugin files | Fill in `edges.py`, `tests.py`, `manifest.py`, `__init__.py` |
| 3 | `todo_scan.py` | Add extension(s) to `SCAN_EXTS` |
| 4 | `frontend/src/data/languages.ts` | Add one entry to the language registry |

---

## Step 1 — Scaffold

```bash
make new-language
# prompts: Language name (e.g. Kotlin):

# Or bypass the prompt:
make new-language LANG=Kotlin
```

This creates `backend/apps/analysis/languages/kotlin/__init__.py` with a documented template and prints the exact snippets you need for steps 3 and 4.

---

## Step 2 — Fill in the plugin files

The scaffold generates four files. Each has a single responsibility:

| File | Purpose |
|------|---------|
| `edges.py` | Import graph extraction — regex, stdlib filter, `extract_edges()` |
| `tests.py` | Test coverage — `extract_test_refs()` (set `= None` if not applicable) |
| `manifest.py` | Dependency parsing — `parse_manifest()` (set `= None` if not applicable) |
| `__init__.py` | Plugin assembly — imports from the three above, defines `plugin` |

Fill in `__init__.py` last (after the other three work). Every `TODO` in `__init__.py` maps directly to something you already implemented in one of the other files.

### `LanguagePlugin` field reference

Fields are set in `__init__.py`; the implementations live in the sub-modules shown.

| Field | File | Type | Purpose |
|-------|------|------|---------|
| `name` | `__init__.py` | `str` | Display name, e.g. `'Kotlin'` |
| `extensions` | `__init__.py` | `tuple[str, ...]` | Source file extensions, e.g. `('.kt', '.kts')` |
| `extract_edges` | `edges.py` | `fn(fpath, content, repo_dir) → list[str]` | Build import graph edges. For simple cases use the regex template; for complex cases (block imports, relative resolution, Vue script stripping) write custom logic. |
| `lang_label` | `__init__.py` | `str` | Short label on each graph edge, e.g. `'kotlin'` |
| `extract_test_refs` | `tests.py` | `fn(test_rel, test_dir, content) → set[str]` | Return slash-path stems imported by a test file so the hotspot test-coverage heuristic can match them to source files. Normalize to `'apps/analysis/tasks'` style. Set `None` if not applicable. |
| `manifest_filenames` | `__init__.py` | `tuple[str, ...]` | Exact filenames of dependency manifests, e.g. `('build.gradle.kts',)` |
| `parse_manifest` | `manifest.py` | `fn(Path) → list[dict]` | Parse one manifest; return list of `{name, version_spec, dev?}` dicts. Dispatch by `path.name` internally for multiple manifest types. Set `None` if not applicable. |
| `vuln_ecosystem` | `__init__.py` | `str \| None` | [OSV.dev ecosystem name](https://osv.dev/docs/#tag/vulnerability/operation/OSV_QueryAffected): `'Maven'`, `'PyPI'`, `'npm'`, `'crates.io'`, `'RubyGems'`, `'Go'`, `'NuGet'`, `'Packagist'`, `'Hex'`, `'Pub'`. `None` if OSV doesn't support the ecosystem. |
| `manifest_dep_files` | `__init__.py` | `tuple[str, ...]` | Subset of `manifest_filenames` used for sub-project detection. Usually the same. |
| `test_frameworks` | `__init__.py` | `dict[str, set[str]]` | `{'framework_name': {'marker_file', ...}}` — files whose presence identifies the test framework. |
| `tier` | `__init__.py` | `'full' \| 'dependencies'` | `'full'` = import graph + dep scanning. `'dependencies'` = dep scanning only. No runtime effect; drives scaffold checklist. |

### Example — Kotlin

```python
plugin = LanguagePlugin(
    name='Kotlin',
    extensions=('.kt', '.kts'),
    extract_edges=_extract_edges,
    lang_label='kotlin',
    extract_test_refs=_extract_test_refs,
    manifest_filenames=('build.gradle.kts', 'settings.gradle.kts'),
    parse_manifest=_parse_manifest,
    vuln_ecosystem='Maven',
    manifest_dep_files=('build.gradle.kts',),
    test_frameworks={'kotest': {'kotest.gradle.kts', 'src/test/kotlin'}},
    tier='full',
)
```

### Complex `extract_edges`

For languages with block imports (Go), relative resolution (JS/TS), or embedded script tags (Vue), `extract_edges` handles everything in one function instead of using `import_re` + `is_external`. See the Go and JavaScript plugins for reference implementations.

### Test ref normalization

`extract_test_refs` must return strings that can be matched against real file paths via a suffix index. Use slash separators and drop the file extension:

```python
# Good: 'apps/analysis/tasks'
# Good: 'com/mycompany/model/User'
# Bad:  'com.mycompany.model.User'  (dots, not slashes)
# Bad:  'apps/analysis/tasks.py'   (has extension)
```

For relative imports (JS/TS style), resolve with `os.path.normpath(os.path.join(test_dir, import_str))`.

---

## Step 3 — Add extension(s) to `SCAN_EXTS`

**File:** `backend/apps/analysis/todo_scan.py`

`SCAN_EXTS` controls which files get scanned for TODOs and complexity. The scaffold prints the current line — add your extension(s) to the set.

```python
SCAN_EXTS = {'.py', '.js', '.ts', ..., '.kt', '.kts'}
```

This is intentionally manual — SCAN_EXTS scope affects performance and is a deliberate human decision.

---

## Step 4 — Add frontend entry

**File:** `frontend/src/data/languages.ts`

The scaffold prints the exact entry to add. Paste it into the array.

```typescript
{ name: 'Kotlin', iconUrl: 'https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/kotlin/kotlin-original.svg', tier: 'full', kind: 'language' },
```

- **tier**: `'full'` if you implemented `extract_edges` and `extract_test_refs`; `'dependencies'` if you only implemented `parse_manifest`.
- **kind**: `'language'`, `'framework'`, or `'tool'`.
- **iconUrl**: from [devicon.dev](https://devicon.dev). CDN pattern: `https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/<slug>/<slug>-original.svg`. Some icons need `-plain.svg` — verify on the site.

This drives the home page marquee, About page language list, and docs.

---

## Step 5 — Run tests

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest apps/analysis/tests/ -v
```

Then manually submit a GitHub URL for a repo that uses the new language and verify:

- Language appears in the "Languages" breakdown
- Import graph includes edges for the language's files
- Hotspot files show `Has Test: Yes` when tests exist
- Dependency tab lists packages
- Tech stack shows framework names (if you added `test_frameworks`)

---

## What stays manual

| Item | Where | Why |
|------|-------|-----|
| `SCAN_EXTS` | `todo_scan.py` | Scanner scope; deliberate human decision, affects perf |
| `frontend/src/data/languages.ts` | Frontend | Different runtime; scaffold prints the reminder |
| `FRAMEWORK_SIGNALS` | `tech_stack.py` | 200+ cross-language entries that grow independently — not per-plugin |
| Ext→name for Haskell, Zig, Shell, Nim, etc. | `_EXTRA_EXT_MAP` in `repo_type.py` | Display-name-only langs with no import analysis or manifests — no plugin needed |
