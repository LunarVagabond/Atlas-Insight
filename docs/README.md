# Atlas Insight — Documentation

Repository archaeology and static analysis platform. Paste a GitHub URL; get architecture insights, commit history analysis, dependency reports, and heuristic health scores.

---

## Who are you?

| I want to… | Go to |
|---|---|
| **Use Atlas Insight** to analyze a repo | [users/getting-started.md](users/getting-started.md) |
| **Run Atlas Insight locally** for development | [dev/setup.md](dev/setup.md) |
| **Deploy Atlas Insight** to a server | [ops/deploy.md](ops/deploy.md) |
| **Review the product roadmap** | [roadmap.md](roadmap.md) |
| **Integrate via API** | [api/reference.md](api/reference.md) |
| **Set up webhooks** | [api/webhooks.md](api/webhooks.md) |

---

## What Atlas Insight does

- **Commit analysis** — velocity trends, contributor churn, burnout signals, activity decay
- **Architecture mapping** — import graph, god modules, circular dependencies, hot files
- **Dependency health** — declared deps, Docker base image warnings, missing lockfiles
- **Security scan** — accidentally committed secrets, gitignore gaps
- **Heuristic scores** — 11 risk signals (abandonment, monolith growth, CI health, bus factor, and more)
- **OSS Score** — 0–10 summary of open-source readiness
- **Contributing path** — actionable opportunities derived from GitHub issues and structural gaps
- **Architecture tours** — guided reading paths through subsystems

Results are cached. Re-submitting a repo checks for new commits first — no redundant work done if nothing changed.
