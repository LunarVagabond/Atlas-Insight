import math
from datetime import datetime, timezone

from .scoring_mode import ScoringMode


def compute_heuristics(
    commits: dict,
    graph: dict,
    deps: dict,
    readme: dict | None = None,
    structure: dict | None = None,
    security: dict | None = None,
    license_data: dict | None = None,
    complexity_data: dict | None = None,
    test_coverage_data: dict | None = None,
    cicd_data: dict | None = None,
    container_data: dict | None = None,
    scoring_mode: ScoringMode = 'oss',
) -> list[dict]:
    signals = []

    # ── Burnout ───────────────────────────────────────────────────────────────
    decay = commits.get('activity_decay_ratio', 1.0)
    churn = commits.get('contributor_churn', [])
    if len(churn) >= 2:
        recent = churn[-1].get('active', 0)
        peak = max((c.get('active', 0) for c in churn), default=1)
        contributor_drop = 1 - (recent / max(peak, 1))
        # Larger teams absorb proportionally more attrition before risk rises.
        # sqrt(2/peak) dampener: at peak=2 → 1.0x, peak=10 → 0.45x, peak=50 → 0.2x.
        if peak <= 1:
            normalized_drop = 0.0
        else:
            size_dampener = math.sqrt(2.0 / max(2, peak))
            normalized_drop = min(1.0, contributor_drop * size_dampener)
    else:
        contributor_drop = 0
        normalized_drop = 0.0
        peak = 1
    burnout_score = int(min(100, (normalized_drop * 50) + (max(0, 1 - decay) * 50)))
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
    if days_silent == 0 or days_silent < 30:
        abandon_score = 0
    else:
        # Smooth log curve: 30d→5, 90d→35, 180d→52, 365d→68, 730d→84, 1095d+→90
        abandon_score = min(90, 5 + int(22 * math.log1p((days_silent - 30) / 20)))

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
    unpinned = deps.get('unpinned_count', 0)
    unpinned_ratio = unpinned / max(dep_count, 1)
    # Unpinned deps above 30% of total signal reproducibility risk
    unpinned_penalty = min(15, int(unpinned_ratio * 30)) if unpinned_ratio > 0.3 else 0
    dep_score = min(100, (docker_issues * 15) + (lockfile_warnings * 20) + min(20, dep_bloat * 4) + unpinned_penalty)
    dep_parts = []
    if docker_issues:
        dep_parts.append(f'{docker_issues} deprecated Docker base image{"s" if docker_issues > 1 else ""}')
    if lockfile_warnings:
        dep_parts.append(f'{lockfile_warnings} missing lockfile{"s" if lockfile_warnings > 1 else ""}')
    if unpinned > 0 and unpinned_ratio > 0.3:
        dep_parts.append(f'{unpinned} unpinned dependencies ({unpinned_ratio:.0%}) — reproducibility risk')
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
            code_blocks = readme.get('code_block_count', 0)
            shallow = readme.get('shallow_sections', [])
            if wc < 100:
                if code_blocks >= 2:
                    doc_issues.append('README short but has code examples')
                else:
                    doc_issues.append('README too short (under 100 words, no code examples)')
            elif wc < 300 and not readme.get('has_external_links'):
                doc_issues.append('README brief with no external links or docs site')
            if not readme.get('has_installation'):
                doc_issues.append('no installation instructions')
            if not readme.get('has_usage'):
                doc_issues.append('no usage section')
            if scoring_mode == 'oss':
                if not readme.get('has_changelog'):
                    doc_issues.append('no changelog')
                if not readme.get('has_contributing'):
                    doc_issues.append('no contributing guide')
                if structure and not structure.get('has_contributing'):
                    doc_issues.append('no CONTRIBUTING file')
            # Shallow sections carry half weight of a full missing section
            if len(shallow) >= 3:
                doc_issues.append(f'{len(shallow)} sections too brief to be useful')
            # "README short but has code examples" is a lighter issue — weight 8 instead of 15
            weighted = sum(8 if 'short but has code' in i else 15 for i in doc_issues)
            doc_score = min(100, weighted)

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
        has_ci = structure.get('has_ci', False)
        if not has_ci:
            ci_score += 40
            ci_parts.append('no CI configuration')
        if not structure.get('has_lint_config'):
            ci_score += 20
            ci_parts.append('no linting config')
        test_ratio = structure.get('test_ratio', 0)
        # If CI exists, integration/e2e tests may live outside the file ratio —
        # reduce the file-ratio penalty to avoid double-penalizing well-tested repos.
        test_penalty_scale = 0.65 if has_ci else 1.0
        if test_ratio < 0.05:
            ci_score += int(30 * test_penalty_scale)
            ci_parts.append(f'very few test files ({test_ratio:.0%} ratio)')
        elif test_ratio < 0.15:
            ci_score += int(15 * test_penalty_scale)
            ci_parts.append(f'low test file ratio ({test_ratio:.0%})')
        elif test_ratio < 0.25:
            ci_score += int(5 * test_penalty_scale)

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
        total_contributors = commits.get('total_contributors', 1)
        bf_score = max(0, min(100, (5 - bus_factor) * 20))
        if total_contributors == 1:
            bf_score = 0
            bf_desc = 'Solo project — all changes by one author by design'
        elif bus_factor == 1:
            if total_contributors >= 10:
                bf_score = min(bf_score, 45)
                if scoring_mode == 'closed_source':
                    bf_desc = (
                        f'1 contributor touches 80%+ of files across {total_contributors} '
                        'contributors — concentrated ownership'
                    )
                else:
                    bf_desc = (
                        f'1 contributor touches 80%+ of files, but {total_contributors} '
                        'contributors have participated — typical of a founder-led open source project'
                    )
            elif total_contributors >= 5:
                bf_score = min(bf_score, 60)
                bf_desc = f'1 contributor accounts for 80%+ of file changes across {total_contributors} contributors — may reflect project founder ownership'
            else:
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
        vulns = security.get('vulnerabilities', [])
        vuln_count = len(vulns)

        cve_score = 0
        for v in vulns:
            cvss = v.get('severity_score')
            if cvss is None:
                cvss = 5.0
            if cvss >= 9.0:
                cve_score += 25
            elif cvss >= 7.0:
                cve_score += 15
            elif cvss >= 4.0:
                cve_score += 8
            else:
                cve_score += 3
        cve_score = min(60, cve_score)

        combined = min(100, sec_score + cve_score)

        sec_items = [_fmt_sec_item(i) for i in issues[:5]] if issues else []
        if vuln_count:
            sec_items.append(f'{vuln_count} known CVE{"s" if vuln_count != 1 else ""} in dependencies')

        if issues and vuln_count:
            desc = f'{len(issues)} security issue{"s" if len(issues) != 1 else ""} and {vuln_count} CVE{"s" if vuln_count != 1 else ""} detected'
        elif vuln_count:
            desc = f'{vuln_count} known CVE{"s" if vuln_count != 1 else ""} in dependencies'
        elif issues:
            desc = f'{len(issues)} security issue{"s" if len(issues) != 1 else ""} detected'
        else:
            desc = 'No obvious security issues or known CVEs detected'

        signals.append({
            'signal': 'security_hygiene',
            'label': 'Security Hygiene',
            'score': combined,
            'confidence': 'medium',
            'description': desc,
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
        else:
            # Smooth log curve: 90d→5, 180d→21, 365d→39, 730d→56, 1095d→65, 1460d+→75
            rel_score = min(75, 5 + int(25 * math.log1p((days_since_release - 90) / 100)))
            if days_since_release < 365:
                rel_desc = f'{release_count} releases, last {days_since_release} days ago — pace slowing'
            elif days_since_release < 730:
                years_f = days_since_release / 365
                rel_desc = f'Last release {years_f:.1f} years ago — release cadence stale'
            else:
                years = days_since_release // 365
                rel_desc = f'Last release {years}+ year{"s" if years > 1 else ""} ago — significantly stale'

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
        if scoring_mode == 'oss':
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
            comm_desc = (
                'Missing: ' + ', '.join(community_issues)
                if community_issues
                else 'License, contributing guide, and community files all present'
            )
        else:
            if not structure.get('has_security_policy'):
                comm_score += 15
                community_issues.append('no SECURITY policy')
            comm_desc = (
                'Missing: ' + ', '.join(community_issues)
                if community_issues
                else 'Security policy present — OSS community files not expected for closed-source repos'
            )

        signals.append({
            'signal': 'community_health',
            'label': 'Community Health',
            'score': min(100, comm_score),
            'confidence': 'high',
            'description': comm_desc,
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
        else:
            # Smooth power curve preserving approximate anchors: 0.7→~22, 0.4→~47, 0.0→75
            vel_score = min(75, int(75 * math.pow(1.0 - velocity_ratio, 0.65)))
            if velocity_ratio >= 0.7:
                vel_desc = f'Slight slowdown — {recent_avg:.0f} vs {prior_avg:.0f} commits/month prior'
            elif velocity_ratio >= 0.4:
                vel_desc = f'Noticeable slowdown — {recent_avg:.0f} vs {prior_avg:.0f} commits/month prior'
            else:
                vel_desc = f'Sharp decline — {recent_avg:.0f} vs {prior_avg:.0f} commits/month prior'

        signals.append({
            'signal': 'commit_velocity',
            'label': 'Commit Velocity Trend',
            'score': vel_score,
            'confidence': 'medium' if len(monthly) >= 12 else 'low',
            'description': vel_desc,
        })

    # ── License risk ─────────────────────────────────────────────────────────
    if license_data is not None:
        lic_score = license_data.get('score', 0)
        lic_issues = license_data.get('issues', [])
        spdx = license_data.get('spdx_id')
        if scoring_mode == 'closed_source' and not spdx:
            lic_score = 0
            lic_desc = 'Closed-source context — license not required for internal use'
        elif lic_score == 0 and spdx:
            lic_desc = f'Licensed under {spdx} — no compatibility issues detected'
        elif not spdx:
            lic_desc = 'No license detected — repository is implicitly all-rights-reserved'
        else:
            lic_desc = '; '.join(i['message'] for i in lic_issues[:3]) or f'{spdx} license present'
        signals.append({
            'signal': 'license_risk',
            'label': 'License Risk',
            'score': min(100, lic_score),
            'confidence': 'high' if spdx else 'medium',
            'description': lic_desc,
        })

    # ── Complexity debt ───────────────────────────────────────────────────────
    if complexity_data is not None:
        cplx_score = complexity_data.get('score', 0)
        hotspots = complexity_data.get('hotspots', [])
        files_over = complexity_data.get('files_over_threshold', 0)
        threshold = complexity_data.get('threshold', 500)
        untested = sum(1 for h in hotspots if not h.get('has_adjacent_test', True))
        if cplx_score < 15:
            cplx_desc = f'No files exceed {threshold} LOC — code stays manageable'
        elif files_over == 1:
            suffix = ', lacks adjacent tests' if untested else ''
            cplx_desc = f'1 file exceeds {threshold} LOC{suffix}'
        else:
            cplx_desc = f'{files_over} files exceed {threshold} LOC' + (
                f', {untested} without adjacent tests' if untested else ''
            )
        signals.append({
            'signal': 'complexity_debt',
            'label': 'Complexity Debt',
            'score': min(100, cplx_score),
            'confidence': 'medium',
            'description': cplx_desc,
        })

    # ── Test coverage ─────────────────────────────────────────────────────────
    if test_coverage_data is not None:
        tc_score = test_coverage_data.get('score', 0)
        test_ratio = test_coverage_data.get('test_ratio', 0)
        framework = test_coverage_data.get('framework_detected')
        untested_dirs = test_coverage_data.get('untested_dirs', [])
        if tc_score < 15:
            tc_desc = f'{test_ratio:.0%} test ratio' + (f' — {framework}' if framework else '')
        elif test_ratio < 0.05:
            tc_desc = f'Very low test coverage ({test_ratio:.0%} ratio)' + (
                f'; {len(untested_dirs)} untested directories' if untested_dirs else ''
            )
        else:
            tc_desc = f'{test_ratio:.0%} test ratio' + (
                f', {len(untested_dirs)} directories without tests' if untested_dirs else ''
            )
        signals.append({
            'signal': 'test_coverage',
            'label': 'Test Coverage',
            'score': min(100, tc_score),
            'confidence': 'medium',
            'description': tc_desc,
        })

    # ── CI/CD maturity ────────────────────────────────────────────────────────
    if cicd_data is not None:
        ci_maturity = cicd_data.get('score', 0)
        ci_risk = max(0, 100 - ci_maturity)
        summary = cicd_data.get('summary', {})
        system = cicd_data.get('system')
        missing: list[str] = []
        if not cicd_data.get('workflow_count'):
            missing.append('no CI configured')
        else:
            if not summary.get('has_tests'):
                missing.append('no test step in CI')
            if not summary.get('has_lint'):
                missing.append('no lint step in CI')
        if missing:
            ci_maturity_desc = ', '.join(missing)
        else:
            parts = [system or 'CI'] + (
                ['tests', 'lint'] if summary.get('has_lint') else ['tests']
            )
            ci_maturity_desc = f'{" + ".join(parts)} pipeline active'
        signals.append({
            'signal': 'cicd_maturity',
            'label': 'CI/CD Maturity',
            'score': min(100, ci_risk),
            'confidence': 'high' if cicd_data.get('workflow_count', 0) > 0 else 'medium',
            'description': ci_maturity_desc,
        })

    # ── Container hygiene ─────────────────────────────────────────────────────
    if container_data is not None and container_data.get('dockerfile_count', 0) > 0:
        cont_score = container_data.get('score', 0)
        total_issues = container_data.get('total_issues', 0)
        high_issues = sum(
            sum(1 for i in d.get('issues', []) if i.get('severity') == 'high')
            for d in container_data.get('dockerfiles', [])
        )
        root_count = sum(1 for d in container_data.get('dockerfiles', []) if d.get('runs_as_root'))
        if cont_score < 15:
            cont_desc = 'Dockerfiles follow best practices'
        elif high_issues:
            parts = []
            if root_count:
                root_s = 's' if root_count > 1 else ''
                parts.append(f'{root_count} container{root_s} running as root')
            other = high_issues - root_count
            if other > 0:
                other_s = 's' if other > 1 else ''
                parts.append(f'{other} other high-severity issue{other_s}')
            cont_desc = ', '.join(parts)
        else:
            issue_s = 's' if total_issues != 1 else ''
            cont_desc = f'{total_issues} minor container hygiene issue{issue_s}'
        signals.append({
            'signal': 'container_hygiene',
            'label': 'Container Hygiene',
            'score': min(100, cont_score),
            'confidence': 'high',
            'description': cont_desc,
        })

    return signals


def compute_oss_score(signals: list[dict], scoring_mode: ScoringMode = 'oss') -> dict:
    """Compute a 0–10 health score from heuristic signals. 10 = perfect."""
    signal_map = {s['signal']: s['score'] for s in signals}

    weights = {
        'community_health': 0.13,
        'documentation_quality': 0.11,
        'ci_health': 0.11,
        'security_hygiene': 0.09,
        'release_cadence': 0.08,
        'abandonment_risk': 0.08,
        'license_risk': 0.07,
        'test_coverage': 0.07,
        'dependency_health': 0.06,
        'cicd_maturity': 0.05,
        'bus_factor_risk': 0.05,
        'complexity_debt': 0.04,
        'container_hygiene': 0.03,
        'monolith_growth': 0.02,
        'commit_velocity': 0.01,
        'burnout': 0.01,
    }
    if scoring_mode == 'closed_source':
        weights = {
            **weights,
            'community_health': 0.0,
            'license_risk': 0.0,
            'documentation_quality': 0.13,
            'ci_health': 0.16,
            'security_hygiene': 0.13,
            'test_coverage': 0.10,
            'abandonment_risk': 0.11,
            'dependency_health': 0.09,
        }

    weighted = 0.0
    total_weight = 0.0
    for sig, weight in weights.items():
        if sig in signal_map:
            weighted += (100 - signal_map[sig]) * weight
            total_weight += weight

    raw = (weighted / total_weight) if total_weight else 50.0
    score = round(raw / 10, 1)
    score = max(0.0, min(10.0, score))

    if score >= 9.0:
        badge = 'champion'
        label = 'Champion'
    elif score >= 7.5:
        badge = 'thriving'
        label = 'Thriving'
    elif score >= 6.0:
        badge = 'growing'
        label = 'Growing'
    elif score >= 4.0:
        badge = 'seedling'
        label = 'Seedling'
    elif score >= 2.0:
        badge = 'struggling'
        label = 'Struggling'
    else:
        badge = 'dormant'
        label = 'Dormant'

    return {'score': score, 'badge': badge, 'label': label, 'mode': scoring_mode}
