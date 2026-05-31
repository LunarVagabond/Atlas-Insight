# Atlas Insight — Task Backlog

## In Progress / Recent
- LOC metrics display
- Date filtering on history tab
- Ownership UX improvements

## Next Features

### High Value
- [ ] Contributor graph — visualize commit activity per author over time
- [ ] Dependency vulnerability scan — flag known CVEs in detected deps
- [ ] Health score breakdown UI — show which heuristics drove the score
- [ ] Stale branch detection — branches with no commits in 90+ days

### UX
- [ ] Side-by-side diff view for run comparisons
- [ ] Shareable permalink per analysis run
- [ ] Export report as PDF/JSON

### Backend
- [ ] Webhook support — auto-reanalyze on GitHub push events
- [ ] Rate limit dashboard — surface GitHub API quota usage
- [ ] Background re-analysis scheduler for watched repos


### Thoughts

- Should we limit when re-runs can happen? If there is 1000+ users looking at this we need to be able to stop repetive re-runs of repos so we don't crash our system
- Security should be looked at / audited we are storing OAuth logins and PAT's I just want to be extra cautios here.