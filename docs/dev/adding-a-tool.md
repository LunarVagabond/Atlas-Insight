# Adding a New Infrastructure Tool to Atlas Insight

Tool plugins auto-discover at startup — no registry edits needed. One folder per tool, same pattern as language plugins.

---

## Four steps

| # | Where | What |
|---|-------|------|
| 1 | Terminal | `make new-tool` (or `make new-tool TOOL=kubernetes`) |
| 2 | `analysis.py` | Implement detection + analysis logic |
| 3 | `__init__.py` | Set detection signals (`detect_files`, `detect_exts`, `detect_dirs`) |
| 4 | `frontend/src/data/languages.ts` | Register the tool so it appears on `/supported` and the home marquee |
| 5 | Frontend | Add TypeScript types + conditional UI section in `DevOpsPanel.vue` |

---

## Step 1 — Scaffold

```bash
make new-tool
# prompts: Tool name (e.g. Kubernetes):

# Or bypass the prompt:
make new-tool TOOL=Kubernetes
```

Creates `backend/apps/analysis/tools/kubernetes/` with:
- `analysis.py` — stubbed `analyze(repo_dir: str) -> dict`
- `__init__.py` — stubbed `ToolPlugin` assembly

---

## Step 2 — Implement `analysis.py`

`analyze(repo_dir)` is called only when the tool is detected. It should:

1. Walk relevant config files (use `root.rglob(pattern)`)
2. Parse config (regex, TOML, YAML, JSON — whatever fits)
3. Run security/hygiene checks
4. Return a result dict

**Required keys in the result dict:**

| Key | Type | Description |
|-----|------|-------------|
| `detected` | `bool` | Always `True` (only called when detected) |
| `security_issues` | `list[dict]` | Each: `{resource, severity, issue}` where severity is `low/medium/high` |
| `score` | `int` | 0–100 hygiene/quality score |

Add any tool-specific keys beyond those. They flow straight to the frontend via `result['tools']['<slug>']`.

**Score pattern** (from Terraform for reference):
```python
score = 40   # baseline
if has_some_good_practice: score += 20
score -= min(high_severity_count * 10, 40)
score -= min(medium_severity_count * 5, 20)
return max(0, min(100, score))
```

### Reference implementations

- **Docker** (`docker/analysis.py`) — wraps an existing analyzer. Use this pattern when porting existing logic.
- **Terraform** (`terraform/analysis.py`) — full from-scratch analysis with HCL parsing, security scans, and scoring. Use this as the gold standard.

---

## Step 3 — Fill in `__init__.py`

Set the detection signals. The registry calls `_is_present()` before running analysis — at least one signal must match.

```python
plugin = ToolPlugin(
    name='Kubernetes',
    slug='kubernetes',
    category='iac',                          # container | iac | ci | build | security
    detect_files=('kubernetes.yaml',),        # exact filenames (searched recursively)
    detect_exts=('.yaml',),                   # extensions — use only if distinctive
    detect_dirs=('k8s', 'manifests'),         # directory names
    analyze=analyze,
)
```

**Detection priority:** Any single match triggers analysis. Be specific — don't use `.yaml` alone as it matches too broadly.

---

## Step 4 — Register in `languages.ts`

Add an entry so the tool appears on the `/supported` page, the home page marquee, and any future registry-driven UI:

```typescript
// frontend/src/data/languages.ts
{ name: 'Kubernetes', iconUrl: DEVICON('kubernetes'), tier: 'full', kind: 'tool', maturity: 'early' },
```

Set `maturity` to `'early'` when first added — promote to `'good'` or `'mature'` as coverage improves. Check [devicon.dev](https://devicon.dev) for the correct icon slug and variant (some need `-plain.svg`).

---

## Step 5 — Frontend

### TypeScript types (`frontend/src/types/run.ts`)

Add an interface for the tool's result dict and register it in `ToolsData`:

```typescript
export interface KubernetesData {
  detected: boolean
  namespace_count: number
  security_issues: { resource: string; severity: string; issue: string }[]
  score: number
  // ... other tool-specific fields
}

// In ToolsData:
export interface ToolsData {
  docker?: ContainerData
  terraform?: TerraformData
  kubernetes?: KubernetesData   // add here
  [key: string]: unknown
}
```

### DevOpsPanel section (`frontend/src/components/analysis/DevOpsPanel.vue`)

Add a section guarded by `v-if` — it only renders when the tool was detected:

```html
<section v-if="tools?.kubernetes" class="devops-panel__section devops-panel__section--kubernetes">
  <h2 class="devops-panel__section-title">Kubernetes</h2>
  <!-- score badge, namespace count, security issues table, etc. -->
</section>
```

SASS for the section goes in `frontend/src/styles/` — no `<style>` block in the `.vue` file.

### Badge count (`frontend/src/views/ResultsView.vue`)

If the tool has security issues, add them to the DevOps tab badge:

```typescript
const kubernetesIssues = r.tools?.kubernetes?.security_issues?.length ?? 0
// Include in the existing badge total alongside container and terraform issues
```

---

## Step 5 — Run tests

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings.development .venv/bin/pytest apps/analysis/tests/ -v
```

Then manually submit a GitHub URL for a repo that uses the new tool and verify:

- Tool section appears in the DevOps tab
- Repos without the tool show no section
- Security issues (if any) are reflected in the tab badge count

---

## What the registry does automatically

When you create the plugin folder:
- `detect_tools(repo_dir)` in `tasks.py` picks it up via `pkgutil`
- Result lands in `result['tools']['<slug>']`
- Available to frontend via `run.result.tools.<slug>`

No manual registration in any dispatch file.

---

## What stays manual

| Item | Why |
|------|-----|
| TypeScript types | Different runtime |
| `DevOpsPanel.vue` section | Tool-specific UI varies too much to auto-generate |
| Tab badge logic in `ResultsView.vue` | Deliberate — keep badge count under human control |
