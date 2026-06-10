# Atlas Insight Roadmap

This page captures the post-FOSS direction for Atlas Insight. It is intentionally directional, not deadline-driven, and can change as the product and community evolve.

Items are grouped by theme. Nothing here is a commitment — it is a backlog of ideas worth revisiting as we learn what users actually need.

---

## How to read this

- **Near-term** — builds on code that already exists; likely the next few iterations.
- **Medium-term** — meaningful new surface area; needs design and scoping.
- **Exploratory** — worth investigating; may never ship if the signal-to-noise ratio is wrong.

Atlas Insight stays deterministic for core analysis. Optional AI features (context export, summaries) remain separate from scanning and scoring.

---

## OSS launch & polish

Gate work that makes the public repo and hosted instance trustworthy before we call the release done.

- Finish the pre-OSS checklist in `TASKS.md` (secrets audit, deployment hardening, backups, docs polish).
- Add screenshots and a short demo flow to the README and docs.
- Review community files: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates.
- Announce release with a clear "what Atlas is / is not" message (deterministic archaeology, not an AI code reviewer).

---

## Self-hosted & feature flags

Some installs only analyze private org repos; others want public discovery features.

- **Done:** Spotlight and Trending are behind feature flags; default instance keeps both enabled.
- Extend flag plumbing to other optional surfaces (public trending feed, constellation graph, AI summary tab).
- Document a "minimal self-hosted" profile: which flags to disable, which env vars matter, expected resource use.
- First-run setup wizard or health-check page for new deployments (DB, Redis, Celery, GitHub token, webhook secret).
- Org-scoped installs: restrict analysis to an allowlist of GitHub orgs without breaking the single-tenant model.

---

## Analysis depth & language coverage

The language registry (`frontend/src/data/languages.ts`) is the contract — every new parser should land there too.

**Near-term**

- Promote early-tier languages (Swift, Dart, Elixir, Scala, Lua) toward `good` / `mature` with broader import-graph tests.
- Add full import-graph support for C/C++ where CMake/`compile_commands.json` is available.
- Haskell, Zig: move from manifest-only toward import/ module edges where feasible.
- Framework-aware subgraphs: highlight Django apps, Rails engines, Nest modules, React feature folders in architecture views.

**Medium-term**

- Monorepo awareness: detect workspaces (npm/pnpm, Cargo, Bazel labels) and score complexity per package, not just per repo root.
- Generated-code exclusion profiles (protobuf, OpenAPI clients, `vendor/`, `node_modules/` already partially handled — extend and make configurable).
- Binary and asset inventory: large blobs, LFS usage, checked-in build artifacts.

**Exploratory**

- Polyglot repos: cross-language boundary detection (FFI, JNI, WASM bindings).
- Historical language drift: when did Python 2 → 3 migration happen, when did TypeScript adoption cross 50%?

---

## Architecture & code quality

Import graphs, god modules, circular deps, and hotspot LOC are in place — room to go deeper without adding noise.

- **Change-impact maps:** for a selected file or directory, show downstream importers and blast radius (feeds PR Impact Preview).
- **Subsystem health cards:** per detected subsystem — test ratio, churn, bus factor, open issues tagged to that area.
- **Refactor candidates:** rank god modules and circular dependency cycles by churn × centrality, not just size.
- **Dead code with confidence tiers:** unreferenced files today; add "likely dead" vs "entrypoint-adjacent" vs "dynamic import" buckets.
- **Architecture drift:** compare import graph shape between two runs (branch compare or time-series) — new cycles, new hubs.
- **Test gap map improvements:** link hotspot files to nearest test file with one-click path navigation.

---

## Security & dependencies

Secrets scan, gitignore hygiene, and CVE lookup exist via JIT endpoints.

- SBOM export (CycloneDX/SPDX) from the dependency inventory.
- License policy profiles for orgs ("no AGPL in production path", "warn on unknown licenses").
- Supply-chain signals: unpinned deps, typosquat-style name warnings, abandoned packages (no releases in N years).
- Container depth: multi-stage Dockerfile scoring, non-root user checks, `latest` tag usage, image age.
- Secret scan: reduce false positives with entropy + context rules; surface rotation guidance, not just "found a key".
- `.gitignore` and `.dockerignore` gap reports with copy-paste fix snippets.

---

## Community, contributing & onboarding

Contribution opportunities, architecture tours, README quality, and the Learn guide are strong foundations.

- **Issue readiness score:** rate how complete a new issue is against repo templates, labels, and similar closed issues (from existing roadmap idea).
- **Issue draft workflow:** compose an issue on Atlas first, then open on GitHub with pre-filled title/body/labels.
- **Good-first-issue ranking:** combine label, age, comment count, linked PRs, and structural "easy win" heuristics.
- **Rotating spotlight notes** on the home card — short, reusable copy that cycles (see `TASKS.md` #14).
- Expand Learn guide with Atlas-specific walkthroughs ("read this tab first for a 10k-star monorepo").
- Maintainer playbook export: printable PDF section for "if you only fix three things this quarter".

---

## Ownership, bus factor & team health

Bus factor and file ownership exist; the roadmap called out a richer view.

- **Bus factor dashboard:** who holds 80% of the codebase, which subsystems are single-owner, trend over re-analyses.
- **Knowledge spread recommendations:** suggest who should review or pair on a subsystem based on ownership gaps (not HR — heuristic hints only).
- **Reviewer suggestions for PR Impact:** intersect changed files with ownership map and recent contributors.
- **Contributor burnout panel:** connect commit velocity heuristics to named contributors with privacy-conscious defaults on public instances.
- **Solo-maintainer mode:** different copy and scoring weights when bus factor is effectively 1.

---

## GitHub integration & workflows

JIT endpoints already cover issues, PRs, diff, file history, PR impact, and vulnerabilities.

- Expand GitHub API usage in small, useful slices — don't boil the ocean.
- **PR checklist:** before opening a PR, show impacted subsystems, missing tests, and CODEOWNERS coverage.
- **Stale branch hygiene actions:** link branch list to "safe to delete?" heuristics (merged, no commits in N months).
- **Release readiness:** tags, changelog presence, CI green on default branch, open release-blocking issues.
- **Webhook ergonomics:** auto-register webhooks for watched repos when user has admin scope; inbound event log in admin UI.
- **Branch comparison:** analyze two branches side-by-side without two full runs where a shallow diff suffices.

---

## Discovery, spotlight & constellation

Spotlight, Trending, and the constellation JIT endpoint support community discovery.

- Spotlight history page improvements: filter by language, OSS score band, theme weeks.
- Trending explanations: why is this repo trending (views, rescans, score delta)?
- Constellation UI: interactive graph of related repos (dependencies, forks, same org, similar heuristic profile).
- **Similar repos** (`/similar` JIT): surface on results page as "repos like this" with diff highlights.
- Curated collections: "best documented Django apps", "rust CLI tools with great CI" — editorial, not algorithmic spam.

---

## Compare, history & trends over time

Compare view and run diff exist; longitudinal story is underdeveloped.

- **Repo timeline:** OSS score, heuristic highlights, and dependency CVE count across all archived runs for one repo.
- **Regression alerts:** webhook or email when bus factor drops, new critical CVE, or score falls below a threshold.
- **Org dashboard:** aggregate health across all repos a user has analyzed (mean score, worst deps, stalest repo).
- **Export time-series JSON** for BI tools from run history.

---

## UI, UX & accessibility

- Deep-link every sub-tab and panel (share "Architecture → import graph" URL).
- Keyboard navigation and focus order across the results tab strip.
- Mobile-friendly results layout (architecture graph is the hard part — progressive disclosure).
- Print/PDF presets: "executive summary", "security audit", "contributor onboarding pack".
- Dark mode polish pass on charts and graph edges.
- Empty states that teach: every panel explains what signal would appear and how to improve it.

---

## API, webhooks & integrations

OpenAPI docs, inbound/outbound webhooks, and JSON export are documented.

- Stable public API versioning policy (`/v1` freeze, deprecation window).
- API keys for machine clients (scoped: read runs, trigger analyze, webhook admin).
- Slack/Discord notifications on analysis complete (outbound webhook templates).
- CI integration: GitHub Action that posts OSS score badge + fails on score regression or new critical CVE.
- Terraform provider or minimal `atlas-cli` for `analyze`, `wait`, `export-json`.

---

## AI context layer (optional)

Core product does not call LLMs. The `ai-summary` JIT endpoint and context export are the boundary.

- Structured context packs tuned for common tools (Cursor rules snippet, Claude project brief, generic markdown).
- User-controlled "what to include" toggles before export (omit secrets scan raw hits, include arch tour only).
- On-device or bring-your-own-key summaries — never mandatory, never on by default for self-hosted.
- Clear labeling everywhere: "generated summary" vs "deterministic score".

---

## Performance & scale

- Incremental re-analysis: only re-run analyzers affected by changed files when commit delta is small.
- Shallow clone options for huge repos with explicit "depth limited" badge on results.
- Parallel analyzer tuning; per-repo timeout budgets with partial results instead of full failure.
- Archive cold runs to object storage; keep metadata hot in Postgres.
- Rate-limit dashboard for GitHub API quota visibility on busy instances.

---

## Platform expansion (exploratory)

GitHub-only today by design. Any expansion needs a clear value prop and avoids duplicating host-native tools.

- GitLab / Gitea / Bitbucket: read-only URL analyze if git clone + API metadata is available.
- Local path / uploaded tarball analyze for air-gapped self-hosted (no phone-home).
- Azure DevOps, SourceHut — only if community demand is real.

---

## Working notes

- This roadmap is a living document. When an idea graduates to active work, track it in `TASKS.md` with acceptance criteria.
- If something matters mainly for self-hosted users, document it here before making it a default-on feature.
- Prefer small shippable slices over large "2.0" releases — Atlas Insight wins by being specific and trustworthy.
