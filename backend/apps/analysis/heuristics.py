def compute_heuristics(
    commits: dict,
    graph: dict,
    deps: dict,
    readme: dict | None = None,
    structure: dict | None = None,
    security: dict | None = None,
) -> list[dict]:
    signals = []

    # ── Burnout ───────────────────────────────────────────────────────────────
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
            'description': (
                f'Activity decay ratio {decay}, contributor drop {contributor_drop:.0%}'
            ),
        }
    )

    # ── Abandonment ───────────────────────────────────────────────────────────
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

    # ── Monolith growth ───────────────────────────────────────────────────────
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

    # ── Dependency health ─────────────────────────────────────────────────────
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

    # ── Documentation quality ────────────────────────────────────────────────
    if readme is not None:
        doc_issues: list[str] = []
        if not readme.get('found'):
            doc_issues.append('no README found')
            doc_score = 90
        else:
            wc = readme.get('word_count', 0)
            if wc < 100:
                doc_issues.append('README too short')
            if not readme.get('has_installation'):
                doc_issues.append('no installation instructions')
            if not readme.get('has_usage'):
                doc_issues.append('no usage section')
            if not readme.get('has_changelog'):
                doc_issues.append('no changelog')
            if not readme.get('has_contributing'):
                doc_issues.append('no contributing guide')
            if structure and not structure.get('has_contributing'):
                doc_issues.append('no CONTRIBUTING file')
            doc_score = min(100, len(doc_issues) * 15)

        signals.append(
            {
                'signal': 'documentation_quality',
                'label': 'Documentation Quality',
                'score': doc_score,
                'confidence': 'high',
                'description': (
                    ', '.join(doc_issues) if doc_issues else 'Documentation looks complete'
                ),
            }
        )

    # ── CI / testing health ───────────────────────────────────────────────────
    if structure is not None:
        ci_parts: list[str] = []
        ci_score = 0
        if not structure.get('has_ci'):
            ci_score += 40
            ci_parts.append('no CI configuration')
        if not structure.get('has_lint_config'):
            ci_score += 20
            ci_parts.append('no linting config')
        test_ratio = structure.get('test_ratio', 0)
        if test_ratio < 0.05:
            ci_score += 30
            ci_parts.append(f'very low test coverage proxy ({test_ratio:.0%})')
        elif test_ratio < 0.15:
            ci_score += 15
            ci_parts.append(f'low test coverage proxy ({test_ratio:.0%})')
        elif test_ratio < 0.25:
            ci_score += 5
            ci_parts.append(f'moderate tests ({test_ratio:.1%})')

        ci_systems = structure.get('ci_systems', [])
        signals.append(
            {
                'signal': 'ci_health',
                'label': 'CI / Testing Health',
                'score': min(100, ci_score),
                'confidence': 'high',
                'description': (
                    ', '.join(ci_parts)
                    if ci_parts
                    else f'CI active via {", ".join(ci_systems)}'
                ),
            }
        )

    # ── Bus factor risk ───────────────────────────────────────────────────────
    if structure is not None:
        bus_factor = structure.get('bus_factor', 1)
        total_commits = commits.get('total_commits', 0)
        bf_score = max(0, min(100, (5 - bus_factor) * 20))
        signals.append(
            {
                'signal': 'bus_factor_risk',
                'label': 'Bus Factor Risk',
                'score': bf_score,
                'confidence': 'high' if total_commits > 50 else 'low',
                'description': (
                    f'{bus_factor} contributor(s) account for 80%+ of file changes'
                ),
            }
        )

    # ── Security hygiene ──────────────────────────────────────────────────────
    if security is not None:
        sec_score = security.get('score', 0)
        issues = security.get('issues', [])
        signals.append(
            {
                'signal': 'security_hygiene',
                'label': 'Security Hygiene',
                'score': sec_score,
                'confidence': 'medium',
                'description': (
                    '; '.join(i['detail'] for i in issues[:3])
                    if issues
                    else 'No obvious security issues detected'
                ),
            }
        )

    return signals
