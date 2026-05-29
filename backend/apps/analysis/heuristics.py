def compute_heuristics(commits: dict, graph: dict, deps: dict) -> list[dict]:
    signals = []

    # Burnout signal
    decay = commits.get('activity_decay_ratio', 1.0)
    churn = commits.get('contributor_churn', [])
    if len(churn) >= 2:
        recent = churn[-1].get('active', 0)
        peak = max((c.get('active', 0) for c in churn), default=1)
        contributor_drop = 1 - (recent / max(peak, 1))
    else:
        contributor_drop = 0
    burnout_score = int(min(100, (contributor_drop * 50) + (max(0, 1 - decay) * 50)))
    signals.append(
        {
            'signal': 'burnout',
            'label': 'Team Burnout Risk',
            'score': burnout_score,
            'confidence': 'high' if len(churn) >= 6 else 'medium',
            'description': f'Activity decay ratio {decay}, contributor drop {contributor_drop:.0%}',
        }
    )

    # Abandonment
    days_silent = commits.get('days_since_last_commit') or 0
    abandoned = commits.get('abandoned', False)
    abandon_score = min(100, int(max(0, days_silent - 180) / 3)) if days_silent else 0
    signals.append(
        {
            'signal': 'abandonment_risk',
            'label': 'Abandonment Risk',
            'score': abandon_score,
            'confidence': 'high' if abandoned else 'medium',
            'description': (
                f'Last commit {days_silent} days ago' if days_silent else 'No commit history'
            ),
        }
    )

    # Monolith growth
    node_count = graph.get('node_count', 0)
    god_count = len(graph.get('god_modules', []))
    cycle_count = graph.get('cycle_count', 0)
    monolith_score = min(100, (god_count * 10) + (cycle_count * 5))
    signals.append(
        {
            'signal': 'monolith_growth',
            'label': 'Monolith Growth',
            'score': monolith_score,
            'confidence': 'high' if node_count > 50 else 'low',
            'description': f'{god_count} god modules, {cycle_count} dependency cycles',
        }
    )

    # Dependency health
    docker_issues = len(deps.get('docker_issues', []))
    lockfile_warnings = len(deps.get('missing_lockfile_warnings', []))
    dep_score = min(100, (docker_issues * 15) + (lockfile_warnings * 20))
    signals.append(
        {
            'signal': 'dependency_health',
            'label': 'Dependency Health',
            'score': dep_score,
            'confidence': 'high',
            'description': (
                f'{docker_issues} deprecated Docker bases, '
                f'{lockfile_warnings} missing lockfiles'
            ),
        }
    )

    return signals
