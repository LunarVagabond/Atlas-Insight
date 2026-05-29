from datetime import datetime, timezone


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
    if burnout_score < 20:
        burnout_desc = 'Contributor activity is stable'
    elif contributor_drop > 0.5:
        burnout_desc = (
            f'Active contributor count dropped {contributor_drop:.0%} from peak'
            + (f'; commit frequency down {(1-decay):.0%}' if decay < 0.7 else '')
        )
    else:
        burnout_desc = (
            f'Commit frequency at {decay:.0%} of historical pace'
            + (f', contributor count down {contributor_drop:.0%}' if contributor_drop > 0.1 else '')
        )
    signals.append({
        'signal': 'burnout',
        'label': 'Team Burnout Risk',
        'score': burnout_score,
        'confidence': 'high' if len(churn) >= 6 else 'medium',
        'description': burnout_desc,
    })

    # ── Abandonment ───────────────────────────────────────────────────────────
    days_silent = commits.get('days_since_last_commit') or 0
    abandoned = commits.get('abandoned', False)
    if days_silent == 0:
        abandon_score = 0
    elif days_silent < 30:
        abandon_score = 0
    elif days_silent < 90:
        abandon_score = 5
    elif days_silent < 180:
        abandon_score = 20
    elif days_silent < 365:
        abandon_score = 45
    elif days_silent < 730:
        abandon_score = 70
    else:
        abandon_score = 90

    if days_silent < 30:
        abandon_desc = 'Actively maintained — committed within the last month'
    elif days_silent < 90:
        abandon_desc = f'Last commit {days_silent} days ago — still active'
    elif days_silent < 180:
        abandon_desc = f'No commits in {days_silent} days — activity slowing'
    elif days_silent < 365:
        abandon_desc = f'Silent for {days_silent} days — possible reduced maintenance'
    else:
        years = days_silent // 365
        abandon_desc = f'No commits in {years}+ year{"s" if years > 1 else ""} — likely abandoned'

    signals.append({
        'signal': 'abandonment_risk',
        'label': 'Abandonment Risk',
        'score': abandon_score,
        'confidence': 'high' if abandoned or days_silent > 180 else 'medium',
        'description': abandon_desc,
    })

    # ── Monolith growth ───────────────────────────────────────────────────────
    node_count = graph.get('node_count', 0)
    god_count = len(graph.get('god_modules', []))
    cycle_count = graph.get('cycle_count', 0)
    # Gentler scaling: 20 god modules = 80, 20 cycles = 60 (additive, capped at 100)
    monolith_score = min(100, (god_count * 4) + (cycle_count * 3))
    if monolith_score < 15:
        mono_desc = 'Healthy module boundaries with few architectural concerns'
    else:
        parts = []
        if god_count:
            parts.append(f'{god_count} highly-imported module{"s" if god_count > 1 else ""}')
        if cycle_count:
            parts.append(f'{cycle_count} circular dependenc{"ies" if cycle_count > 1 else "y"}')
        mono_desc = ', '.join(parts)
    signals.append({
        'signal': 'monolith_growth',
        'label': 'Monolith Growth',
        'score': monolith_score,
        'confidence': 'high' if node_count > 50 else 'low',
        'description': mono_desc,
    })

    # ── Dependency health ─────────────────────────────────────────────────────
    docker_issues = len(deps.get('docker_issues', []))
    lockfile_warnings = len(deps.get('missing_lockfile_warnings', []))
    dep_count = deps.get('dependency_count', 0)
    dep_bloat = max(0, (dep_count - 50) // 50) if dep_count > 50 else 0
    dep_score = min(100, (docker_issues * 15) + (lockfile_warnings * 20) + min(20, dep_bloat * 4))
    dep_parts = []
    if docker_issues:
        dep_parts.append(f'{docker_issues} deprecated Docker base image{"s" if docker_issues > 1 else ""}')
    if lockfile_warnings:
        dep_parts.append(f'{lockfile_warnings} missing lockfile{"s" if lockfile_warnings > 1 else ""}')
    if dep_count > 200:
        dep_parts.append(f'{dep_count} total dependencies (large surface area)')
    signals.append({
        'signal': 'dependency_health',
        'label': 'Dependency Health',
        'score': dep_score,
        'confidence': 'high',
        'description': ', '.join(dep_parts) if dep_parts else f'{dep_count} dependencies — no obvious issues',
    })

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

        signals.append({
            'signal': 'documentation_quality',
            'label': 'Documentation Quality',
            'score': doc_score,
            'confidence': 'high',
            'description': ', '.join(doc_issues) if doc_issues else 'Documentation looks complete',
        })

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
            ci_parts.append(f'very few test files ({test_ratio:.0%} ratio)')
        elif test_ratio < 0.15:
            ci_score += 15
            ci_parts.append(f'low test file ratio ({test_ratio:.0%})')
        elif test_ratio < 0.25:
            ci_score += 5

        ci_systems = structure.get('ci_systems', [])
        signals.append({
            'signal': 'ci_health',
            'label': 'CI / Testing Health',
            'score': min(100, ci_score),
            'confidence': 'high',
            'description': (
                ', '.join(ci_parts)
                if ci_parts
                else f'CI active via {", ".join(ci_systems)}'
            ),
        })

    # ── Bus factor risk ───────────────────────────────────────────────────────
    if structure is not None:
        bus_factor = structure.get('bus_factor', 1)
        total_commits = commits.get('total_commits', 0)
        bf_score = max(0, min(100, (5 - bus_factor) * 20))
        if bus_factor == 1:
            bf_desc = '1 contributor accounts for 80%+ of all file changes'
        elif bus_factor <= 2:
            bf_desc = f'{bus_factor} contributors account for 80%+ of file changes — low redundancy'
        else:
            bf_desc = f'{bus_factor} contributors needed to cover 80% of the codebase'
        signals.append({
            'signal': 'bus_factor_risk',
            'label': 'Bus Factor Risk',
            'score': bf_score,
            'confidence': 'high' if total_commits > 50 else 'low',
            'description': bf_desc,
        })

    # ── Security hygiene ──────────────────────────────────────────────────────
    def _fmt_sec_item(issue: dict) -> str:
        detail = issue['detail']
        sha = issue.get('commit_sha')
        author = issue.get('commit_author')
        if sha and author:
            return f'{detail} · {sha} by {author}'
        if sha:
            return f'{detail} · {sha}'
        return detail

    if security is not None:
        sec_score = security.get('score', 0)
        issues = security.get('issues', [])
        sec_items = [_fmt_sec_item(i) for i in issues[:5]] if issues else []
        signals.append({
            'signal': 'security_hygiene',
            'label': 'Security Hygiene',
            'score': sec_score,
            'confidence': 'medium',
            'description': (
                f'{len(issues)} security issue{"s" if len(issues) != 1 else ""} detected'
                if issues
                else 'No obvious security issues detected'
            ),
            'items': sec_items,
        })

    # ── Release cadence ───────────────────────────────────────────────────────
    if structure is not None:
        release_count = structure.get('release_count', 0)
        last_release = structure.get('last_release')
        days_since_release: int | None = None
        if last_release and last_release.get('date'):
            try:
                rel_dt = datetime.fromisoformat(last_release['date'])
                if rel_dt.tzinfo is None:
                    rel_dt = rel_dt.replace(tzinfo=timezone.utc)
                days_since_release = (datetime.now(timezone.utc) - rel_dt).days
            except Exception:
                pass

        if release_count == 0:
            rel_score = 35
            rel_desc = 'No tagged releases — difficult to track stable versions'
        elif days_since_release is None:
            rel_score = 20
            rel_desc = f'{release_count} releases — last release date unavailable'
        elif days_since_release < 90:
            rel_score = 0
            rel_desc = f'{release_count} releases, last {days_since_release} days ago — active cadence'
        elif days_since_release < 365:
            rel_score = 15
            rel_desc = f'{release_count} releases, last {days_since_release} days ago'
        elif days_since_release < 730:
            rel_score = 50
            rel_desc = f'Last release {days_since_release} days ago — release pace slowing'
        else:
            years = days_since_release // 365
            rel_score = 75
            rel_desc = f'Last release {years}+ year{"s" if years > 1 else ""} ago — stale release cadence'

        signals.append({
            'signal': 'release_cadence',
            'label': 'Release Cadence',
            'score': rel_score,
            'confidence': 'high' if release_count >= 3 else 'low',
            'description': rel_desc,
        })

    # ── Community health ──────────────────────────────────────────────────────
    if structure is not None:
        community_issues: list[str] = []
        comm_score = 0
        if not structure.get('license_type') and not structure.get('license_file'):
            comm_score += 30
            community_issues.append('no license')
        if not structure.get('has_contributing'):
            comm_score += 20
            community_issues.append('no CONTRIBUTING guide')
        if not structure.get('has_security_policy'):
            comm_score += 15
            community_issues.append('no SECURITY policy')
        if not structure.get('has_coc'):
            comm_score += 10
            community_issues.append('no code of conduct')
        if not structure.get('has_changelog'):
            comm_score += 10
            community_issues.append('no CHANGELOG')

        signals.append({
            'signal': 'community_health',
            'label': 'Community Health',
            'score': min(100, comm_score),
            'confidence': 'high',
            'description': (
                'Missing: ' + ', '.join(community_issues)
                if community_issues
                else 'License, contributing guide, and community files all present'
            ),
        })

    # ── Commit velocity trend ─────────────────────────────────────────────────
    monthly = commits.get('monthly_frequency', [])
    if len(monthly) >= 6:
        recent_months = [m.get('count', 0) for m in monthly[-3:]]
        prior_months = [m.get('count', 0) for m in monthly[-6:-3]]
        recent_avg = sum(recent_months) / 3
        prior_avg = sum(prior_months) / max(3, 1)
        if prior_avg == 0:
            velocity_ratio = 1.0
        else:
            velocity_ratio = recent_avg / prior_avg

        if velocity_ratio >= 1.0:
            vel_score = 0
            vel_desc = f'Commit pace stable or growing ({recent_avg:.0f} commits/month recently)'
        elif velocity_ratio >= 0.7:
            vel_score = 20
            vel_desc = f'Slight slowdown — {recent_avg:.0f} vs {prior_avg:.0f} commits/month prior'
        elif velocity_ratio >= 0.4:
            vel_score = 50
            vel_desc = f'Noticeable slowdown — {recent_avg:.0f} vs {prior_avg:.0f} commits/month prior'
        else:
            vel_score = 75
            vel_desc = f'Sharp decline — {recent_avg:.0f} vs {prior_avg:.0f} commits/month prior'

        signals.append({
            'signal': 'commit_velocity',
            'label': 'Commit Velocity Trend',
            'score': vel_score,
            'confidence': 'medium' if len(monthly) >= 12 else 'low',
            'description': vel_desc,
        })

    return signals
