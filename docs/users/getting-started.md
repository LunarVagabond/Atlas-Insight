# Getting Started with Atlas Insight

Atlas Insight analyzes GitHub repositories and surfaces architecture insights, historical trends, and health signals — no setup required on your end.

---

## Analyzing a repository

1. Paste any public GitHub repository URL into the search bar
2. Click **Analyze**
3. Atlas Insight clones and inspects the repository in the background
4. Results appear automatically — most repos complete in under a minute

**Already analyzed?** Submitting the same URL again checks for new commits first. If nothing has changed, you get the cached results instantly.

---

## The repository list

Your analyzed repositories are shown in a table with:

- **Language icons** — top 3 languages by percentage of code (hover for name and %)
- **Health badge** — a quick tier label (`champion` / `thriving` / `growing` / `seedling` / `struggling` / `dormant`) derived from the OSS Score; hover for the numeric score

---

## Reading the results

### OSS Score

A single 0–10 number summarizing open-source readiness. Higher is better. It rolls up signals like documentation completeness, CI presence, bus factor, and release cadence.

### Health signals

Eleven heuristic risk signals give you a quick read on project health:

| Signal | What it means |
|---|---|
| **Abandonment risk** | Commit activity has gone quiet for an extended period |
| **Bus factor** | Most commits come from a single contributor — not flagged for solo projects |
| **Monolith growth** | Files are growing large and tightly coupled |
| **CI health** | CI configuration is absent or broken |
| **Burnout signal** | Contributor output spiked then dropped sharply |
| **Activity decay** | Commit frequency trending downward over time |
| **Architecture drift** | Import graph has grown more tangled over time |
| **Incomplete migration** | Signs of a half-finished framework or language switch |
| **God module** | One or more files depended on by a large fraction of the codebase |
| **Missing lockfile** | Dependencies declared but not pinned |
| **Secret exposure** | Credentials or tokens found in commit history |

Each signal is **deterministic and data-driven** — no AI models are used for scanning. Atlas Insight can optionally export a context block for AI tools outside the app.

### Commit history

- Velocity chart showing commits per week/month over the project's lifetime
- Contributor breakdown: who committed, how much, and when they stopped
- Periods of rapid change or sudden silence are highlighted

### Architecture map

- Import dependency graph showing which modules depend on what
- Circular dependency clusters flagged in red
- Hot files — most frequently changed files (often the riskiest to touch)
- God modules — files imported by an unusually large number of other modules

### Dependency report

- Libraries and frameworks in use, with version information where available
- Docker base image warnings (outdated or deprecated images)
- Missing lockfiles that leave dependency versions unpinned

### Contributing path

If you're looking to contribute to a project, this section surfaces:
- Open GitHub issues tagged as good first issues or help wanted
- Structural gaps where contributions would have the most impact (missing tests, undocumented modules, stale dependencies)

### Architecture tour

A guided reading path through the repository's subsystems. Instead of staring at a file tree, follow a structured walkthrough that explains what each layer does and where to start reading.

---

## Spotlight and Trending

- **Spotlight** — a weekly featured public repository with a full analysis report
- **Trending** — repositories ranked by recent scans and views across the instance

Browse both from the top navigation after signing in is optional; public instances show them on the home page.

---

## Private repositories

Private repositories require you to connect your GitHub account and grant Atlas Insight access. Look for the **Connect GitHub** button in your account settings.

Once connected, any private repo you have access to can be analyzed the same way as public repos.

---

## Embedding a health badge

Add a live OSS Score badge to your README:

```markdown
![Atlas Insight Score](https://<your-atlas-domain>/api/v1/repositories/badge/<owner>/<repo>.svg)
```

The badge updates automatically after each analysis.

---

## Frequently asked questions

**How long does analysis take?**
Most repositories finish in 30–90 seconds. Very large repositories with deep history may take a few minutes.

**Does Atlas Insight store my code?**
Atlas Insight clones the repository temporarily for analysis, then stores the results (metrics, scores, graphs). It does not retain a copy of your source files.

**Can I re-run an analysis?**
Yes. Submit the URL again — Atlas Insight checks for new commits. If the repo has new activity, a fresh analysis runs. If nothing has changed, the existing results are returned.

**What languages are supported?**
Atlas Insight supports 15+ languages and frameworks for import parsing, dependency detection, and structure analysis. See the in-app **What's Supported** page (`/supported`) or `frontend/src/data/languages.ts` for the full registry. Commit history and heuristic scoring work on any repository regardless of language.
