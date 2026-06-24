# Changelog

All notable changes to Atlas Insight are documented here.

## Unreleased

### Fixed

- **Spotlight gap on selection failure** — `sync_spotlight_watches` now falls back to the most recent pick when no current-week record exists, preventing the daily safety-net task from clearing watches when the weekly selection task fails or hasn't run yet. Previously this left the site with no spotlight until manual intervention.
- `select_repo_of_week` Celery task now retries up to 3 times (5 min apart) on transient failures before giving up.
