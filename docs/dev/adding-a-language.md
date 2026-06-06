# Adding a New Language to Atlas Insight

This guide covers every place you must touch to add full language support. Work through the steps in order — each section builds on the previous one.

---

## Quick checklist

| # | File | What to add |
|---|------|-------------|
| 1 | `backend/apps/analysis/todo_scan.py` | File extension(s) in `SCAN_EXTS` |
| 2 | `backend/apps/analysis/repo_type.py` | Extension → display name in `LANG_EXT_MAP` |
| 3 | `backend/apps/analysis/repo_type.py` | Manifest filename(s) in `_dep_files_in_dir` |
| 4 | `backend/apps/analysis/import_parser.py` | Import regex pattern + elif branch + stdlib filter |
| 5 | `backend/apps/analysis/complexity.py` | Test-import regex + elif in `_extract_import_refs` |
| 6 | `backend/apps/analysis/test_coverage.py` | Test framework signature in `_FRAMEWORK_SIGNATURES` |
| 7 | `backend/apps/analysis/dep_report.py` | `_parse_<manifest>()` function + call in `analyze_dependencies` |
| 8 | `backend/apps/analysis/vuln_scan.py` | Manifest → OSV ecosystem name in `_ECOSYSTEM_MAP` |
| 9 | `backend/apps/analysis/pr_impact.py` | Manifest filename(s) in `_DEP_FILENAMES` |
| 10 | `backend/apps/analysis/project_structure/tech_stack.py` | Package names in `FRAMEWORK_SIGNALS` + config files in `_FRAMEWORK_FILE_PATTERNS` (optional but recommended) |
| 11 | `frontend/src/data/languages.ts` | Entry in `SUPPORTED_LANGUAGES` |

---

## Step 1 — Register file extensions

**File:** `backend/apps/analysis/todo_scan.py`, line 4

`SCAN_EXTS` controls which files get scanned for TODOs, complexity, and import analysis. Add every source extension for the language.

```python
# Before
SCAN_EXTS = {'.py', '.js', '.ts', ...}

# After (example: adding Kotlin)
SCAN_EXTS = {'.py', '.js', '.ts', ..., '.kt', '.kts'}
```

---

## Step 2 — Map extensions to display name

**File:** `backend/apps/analysis/repo_type.py`, line 13 (`LANG_EXT_MAP`)

This dict drives language detection in the graph, heuristics, and the "Languages" breakdown shown in the UI.

```python
LANG_EXT_MAP = {
    # ... existing ...
    '.kt':  'Kotlin',
    '.kts': 'Kotlin',
}
```

---

## Step 3 — Register dependency manifest files

**File:** `backend/apps/analysis/repo_type.py`, function `_dep_files_in_dir` (~line 158)

Add every filename that signals a dependency manifest for the language. These are used to detect sub-projects and determine repo type.

```python
_DEP_FILE_CANDIDATES = [
    # ... existing ...
    'build.gradle.kts',   # Kotlin (Gradle)
    'settings.gradle.kts',
]
```

---

## Step 4 — Import parser

**File:** `backend/apps/analysis/import_parser.py`

This is the main analysis step. Three sub-steps:

### 4a — Add the import regex pattern

Near the top of the file alongside the other `_*_IMPORT` constants:

```python
# Kotlin: import com.example.foo.Bar
KOTLIN_IMPORT = re.compile(r'^import\s+([\w.]+)', re.MULTILINE)
```

### 4b — Add the stdlib/external filter

Add a frozenset of stdlib prefixes and a helper that returns `True` for non-project imports. This prevents internal module edges from being inflated by standard library usage.

```python
_KOTLIN_STDLIB_PREFIXES = frozenset({
    'kotlin.', 'kotlinx.', 'java.', 'javax.', 'android.',
})

def _is_external_kotlin(module: str) -> bool:
    return any(module.startswith(p) for p in _KOTLIN_STDLIB_PREFIXES)
```

If the language has no meaningful stdlib distinction (e.g., Lua), just return `False` always.

### 4c — Add the elif branch in `parse_imports`

Find the main dispatch block in `parse_imports()` and add a branch. Follow the same return shape as existing branches — a list of `{'module': str, 'is_external': bool}` dicts.

```python
elif ext in ('.kt', '.kts'):
    for m in KOTLIN_IMPORT.finditer(content):
        module = m.group(1)
        imports.append({
            'module': module,
            'is_external': _is_external_kotlin(module),
        })
```

---

## Step 5 — Test coverage detection

**File:** `backend/apps/analysis/complexity.py`

When a large file appears as a hotspot, the system checks whether any test file imports it. Two sub-steps:

### 5a — Add the import regex

Near the top of the file alongside `_RE_PY`, `_RE_GO`, etc.:

```python
# Kotlin
_RE_KT = re.compile(r'^import\s+([\w.]+)', re.MULTILINE)
```

### 5b — Add the elif branch in `_extract_import_refs`

```python
elif ext in ('.kt', '.kts'):
    for m in _RE_KT.finditer(content):
        refs.add(m.group(1).replace('.', '/'))
```

The refs should be normalized to slash-separated path stems (same as Python's `apps.analysis.tasks` → `apps/analysis/tasks`). The suffix index in `_build_tested_set` will match them against actual source file paths regardless of where in the tree they sit.

For relative imports (JS/TS style), resolve them with `os.path.normpath(os.path.join(test_dir, import_str))`. See the `.js`/`.ts` branch for the pattern.

---

## Step 6 — Test framework detection

**File:** `backend/apps/analysis/test_coverage.py`, dict `_FRAMEWORK_SIGNATURES` (~line 11)

Add an entry whose value is a set of filenames or glob patterns that uniquely identify the test framework. The system looks for these files (or patterns like `_test.go`) in the repo to name the testing setup.

```python
_FRAMEWORK_SIGNATURES = {
    # ... existing ...
    'kotest':  {'kotest.gradle.kts', 'src/test/kotlin'},
    'junit5':  {'junit-platform.properties'},   # also used for Java
}
```

If the language uses a convention-based approach (e.g., Go's `_test.go` suffix), the value can be a bare filename pattern — the detection code handles both exact filenames and glob-style `*` patterns.

---

## Step 7 — Dependency parsing

**File:** `backend/apps/analysis/dep_report.py`

### 7a — Write a parser function

Follow the shape of `_parse_requirements_txt` or `_parse_package_json`. Return a list of dicts with at minimum `name` and `version` keys. Extras like `dev` (bool) are optional but surfaced in the UI.

```python
def _parse_build_gradle_kts(path: Path) -> list[dict]:
    deps = []
    content = path.read_text(errors='ignore')
    # implementation("com.squareup.okhttp3:okhttp:4.12.0")
    pattern = re.compile(
        r'''(?:implementation|api|testImplementation|runtimeOnly)\s*\(\s*['"]([^'"]+)['"]\s*\)'''
    )
    for m in pattern.finditer(content):
        parts = m.group(1).split(':')
        if len(parts) >= 2:
            deps.append({'name': parts[1], 'version': parts[2] if len(parts) > 2 else '', 'dev': False})
    return deps
```

### 7b — Call it in `analyze_dependencies`

Inside the `analyze_dependencies` function (~line 185), add the manifest lookup and parser call:

```python
for grad in repo_path.rglob('build.gradle.kts'):
    if any(part in SKIP_DIRS for part in grad.parts):
        continue
    all_deps.extend(_parse_build_gradle_kts(grad))
```

---

## Step 8 — Vulnerability scanning

**File:** `backend/apps/analysis/vuln_scan.py`, dict `_ECOSYSTEM_MAP` (line 7)

Map every manifest filename to its [OSV.dev ecosystem name](https://osv.dev/docs/#tag/vulnerability/operation/OSV_QueryAffected). If OSV doesn't support the ecosystem yet, omit it rather than guessing.

```python
_ECOSYSTEM_MAP = {
    # ... existing ...
    'build.gradle.kts': 'Maven',
    'build.gradle':     'Maven',
}
```

OSV ecosystem names to use: `PyPI`, `npm`, `crates.io`, `RubyGems`, `Go`, `Maven`, `NuGet`, `Packagist`, `Hex`, `Pub`.

---

## Step 9 — PR impact dependency file list

**File:** `backend/apps/analysis/pr_impact.py`, frozenset `_DEP_FILENAMES` (line 6)

Any PR that touches one of these files is flagged as a "dependency change" in the PR impact card. Add the manifest and lockfile names.

```python
_DEP_FILENAMES = frozenset({
    # ... existing ...
    'build.gradle.kts',
    'settings.gradle.kts',
    'gradle.lockfile',
})
```

---

## Step 10 — Tech stack detection (optional but recommended)

**File:** `backend/apps/analysis/project_structure/tech_stack.py`

This is where popular frameworks and libraries for the language get detected and surfaced in the "Tech Stack" section of the report. Two sub-steps:

### 10a — Package name → framework display name (`FRAMEWORK_SIGNALS`)

Add entries under a new key for the language. The key is the dependency name exactly as it appears in the manifest; the value is the display name shown in the UI.

```python
FRAMEWORK_SIGNALS = {
    # ... existing Python, JS, etc. ...
    # Kotlin / JVM
    'spring-boot-starter-web':  'Spring Boot',
    'ktor-server-core':         'Ktor',
    'io.ktor:ktor-server-netty': 'Ktor',
    'exposed':                  'Jetbrains Exposed',
}
```

### 10b — Config file → framework display name (`_FRAMEWORK_FILE_PATTERNS`)

For frameworks detected by config files rather than dep names:

```python
_FRAMEWORK_FILE_PATTERNS = {
    # ... existing ...
    'android/AndroidManifest.xml': 'Android',
}
```

---

## Step 11 — Frontend language registry

**File:** `frontend/src/data/languages.ts`, array `SUPPORTED_LANGUAGES`

This drives the home page marquee, About page language list, and docs. Add one entry. Choose:

- **tier**: `'full'` if you implemented import graph analysis (Steps 4–5); `'dependencies'` if you only implemented dependency scanning (Steps 7–9).
- **kind**: `'language'`, `'framework'`, or `'tool'`.
- **iconUrl**: grab the SVG URL from [devicon.dev](https://devicon.dev). CDN pattern: `https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/<slug>/<slug>-original.svg`. Some need `-plain.svg` — check the site.

```typescript
{ name: 'Kotlin',  iconUrl: 'https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/kotlin/kotlin-original.svg',  tier: 'full', kind: 'language' },
```

---

## Testing your changes

After completing all steps, run:

```bash
# Backend unit tests
cd backend
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest apps/analysis/tests/ -v

# Spot-check import parsing against a real repo
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/python - <<'EOF'
from pathlib import Path
from apps.analysis.import_parser import parse_imports

# Point at a cloned repo with your new language
sample = Path('/tmp/my-kotlin-repo/src/main/kotlin/Main.kt')
print(parse_imports(str(sample), sample.read_text()))
EOF

# Frontend type check
cd ../frontend && node_modules/.bin/vue-tsc --noEmit
```

Manually submit a GitHub URL for a repo that uses the new language and verify:
- Language appears in the "Languages" breakdown
- Import graph includes edges for the language's files
- Hotspot files show `Has Test: Yes` when tests exist
- Dependency tab lists packages
- Tech stack shows the right framework names

---

## Future direction — plugin architecture

Right now, language support is spread across ~10 files. A plugin system (one folder per language, auto-discovered at startup) would let `make new-language LANG=kotlin` scaffold all the boilerplate. That refactor is tracked separately; this doc reflects the current structure and is kept up to date.
