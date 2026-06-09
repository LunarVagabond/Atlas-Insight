# Analysis Pipeline

`analyze_repository` in `apps/analysis/tasks.py` orchestrates repository analysis. Progress steps exposed to the UI: `cloning` → `parsing` → `metadata` → `heuristics` → `finalizing`.

## Flow

1. **Clone/fetch** — `clone_or_fetch()` blocks all downstream work. Fresh clones can take several minutes.
2. **Parsing** — import graph, dependency report, structure scan, security scan, todos. Partially parallel (see below).
3. **Metadata** — GitHub REST/GraphQL for stars, languages, contributors, issues. Sequential HTTP calls.
4. **Heuristics** — seven extra analyzers run in a thread pool; composite score and classification follow.
5. **Finalizing** — arch tours, ownership, contribution opportunities (parallel). Diff vs previous run and similar repos computed in parallel.
6. **Post-save** — constellation detection runs inline; webhook and email notifications are deferred to `notify_run_complete`.

## Parallel today

| Phase | Parallel work | Workers |
|-------|---------------|---------|
| Parsing | `analyze_graph` + `scan_todos`; then `scan_security` + `analyze_structure` + `scan_vulnerabilities` | 2, then 3 |
| Heuristics extras | license, complexity, dead_code, test_coverage, tools, cicd, changelog | 7 |
| Finalizing | arch_tours, ownership, contribution_opportunities | 3 |
| Tail | diff, similar_runs | 2 |
| Vuln CVE detail | inside `scan_vulnerabilities` | 6 |

## Known sequential bottlenecks

- **Git clone/fetch** — must complete before any local analysis.
- **Pre-clone privacy check** — extra GitHub round-trip before clone (duplicated in metadata fetch).
- **Repeated repo walks** — each analyzer traverses the tree independently (`import_parser`, structure, todos, complexity, etc.). Merging walks would help but is a larger refactor.
- **Sub-project monorepos** — `_analyze_sub_projects` loops sequentially per sub-project.
- **GitHub metadata** — contributor and issue fetches are sequential after GraphQL.
- **Constellation detection** — runs inline after save (small DB work).

## Deferred (higher risk)

- Single merged repo walk shared across analyzers
- Celery task decomposition (clone vs analyze chain)
- Parallel sub-project loop (memory pressure on large monorepos)
