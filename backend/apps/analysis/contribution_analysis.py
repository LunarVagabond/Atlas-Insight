from __future__ import annotations


def _heuristic_opportunities(
    commits: dict,
    graph: dict,
    deps: dict,
    readme: dict | None,
    structure: dict | None,
    security: dict | None,
) -> list[dict]:
    opps: list[dict] = []

    # ── Beginner / Low risk ───────────────────────────────────────────────────
    if structure:
        if not structure.get('license_file') and not structure.get('license_type'):
            opps.append({
                'id': 'add_license',
                'title': 'Add a LICENSE file',
                'description': 'No license detected. Without one the code is legally "all rights reserved" — contributors and users cannot safely rely on it.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'community',
            })
        if not structure.get('has_contributing'):
            opps.append({
                'id': 'add_contributing',
                'title': 'Add CONTRIBUTING.md',
                'description': 'No contributing guide. New contributors need to know how to set up the project, run tests, and open a PR.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
            })
        if not structure.get('has_changelog'):
            opps.append({
                'id': 'add_changelog',
                'title': 'Create a CHANGELOG',
                'description': 'No changelog exists. Maintainers and users have no structured way to track what changed between releases.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
            })
        if not structure.get('has_coc'):
            opps.append({
                'id': 'add_coc',
                'title': 'Add a Code of Conduct',
                'description': 'No Code of Conduct. Signals community standards and protects contributors from harassment.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'community',
            })
        if not structure.get('has_security_policy'):
            opps.append({
                'id': 'add_security_policy',
                'title': 'Add a SECURITY.md',
                'description': 'No security disclosure policy. Researchers and contributors have no clear channel to report vulnerabilities.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'security',
            })

    if readme:
        if not readme.get('found'):
            opps.append({
                'id': 'add_readme',
                'title': 'Create a README',
                'description': 'No README found. Every project needs one to explain what it does and how to get started.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
            })
        else:
            if not readme.get('has_installation'):
                opps.append({
                    'id': 'readme_installation',
                    'title': 'Add installation instructions to README',
                    'description': 'README has no installation section — newcomers cannot get the project running without it.',
                    'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
                })
            if not readme.get('has_usage'):
                opps.append({
                    'id': 'readme_usage',
                    'title': 'Add usage examples to README',
                    'description': 'README has no usage section. Code examples are the fastest way to show what the project does.',
                    'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
                })

    if security:
        if not security.get('gitignore_exists'):
            opps.append({
                'id': 'add_gitignore',
                'title': 'Add a .gitignore file',
                'description': 'No .gitignore found. Build artifacts, secrets, and editor files could be accidentally committed.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'security',
            })
        elif security.get('gitignore_gaps'):
            gaps = security['gitignore_gaps']
            opps.append({
                'id': 'gitignore_gaps',
                'title': f'Fix .gitignore — {len(gaps)} missing pattern{"s" if len(gaps) != 1 else ""}',
                'description': f'Patterns not covered: {", ".join(gaps[:5])}. Risk of accidentally committing sensitive files or noise.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'security',
            })

    for i, warning in enumerate(deps.get('missing_lockfile_warnings', [])[:2]):
        opps.append({
            'id': f'lockfile_{i}',
            'title': 'Add a package lockfile',
            'description': f'{warning}. Lockfiles ensure reproducible installs across machines and CI.',
            'difficulty': 'beginner', 'risk': 'low', 'category': 'dependencies',
        })

    # ── Intermediate / Medium risk ────────────────────────────────────────────
    if structure:
        if not structure.get('has_ci'):
            opps.append({
                'id': 'add_ci',
                'title': 'Set up a CI pipeline',
                'description': 'No CI configuration found. Automated testing on PRs prevents regressions and speeds up code review.',
                'difficulty': 'intermediate', 'risk': 'low', 'category': 'ci',
            })
        if not structure.get('has_lint_config'):
            opps.append({
                'id': 'add_linting',
                'title': 'Add a linting configuration',
                'description': 'No linter config found. Consistent code style reduces review friction and catches simple errors automatically.',
                'difficulty': 'intermediate', 'risk': 'low', 'category': 'ci',
            })
        test_ratio = structure.get('test_ratio', 0)
        if test_ratio < 0.05:
            opps.append({
                'id': 'add_tests',
                'title': f'Add test coverage ({test_ratio:.0%} test file ratio)',
                'description': 'Very few test files relative to source. Even basic unit tests for core modules substantially improve confidence in changes.',
                'difficulty': 'intermediate', 'risk': 'medium', 'category': 'testing',
            })
        elif test_ratio < 0.15:
            opps.append({
                'id': 'improve_tests',
                'title': f'Improve test coverage ({test_ratio:.0%} test file ratio)',
                'description': 'Below-average test file ratio. Adding tests for core functionality reduces regression risk on future contributions.',
                'difficulty': 'intermediate', 'risk': 'medium', 'category': 'testing',
            })

    for i, di in enumerate(deps.get('docker_issues', [])[:3]):
        opps.append({
            'id': f'docker_{i}',
            'title': f'Update Dockerfile: {di["file"]}',
            'description': di['issue'],
            'difficulty': 'intermediate', 'risk': 'medium', 'category': 'dependencies',
        })

    # ── Advanced / High risk ──────────────────────────────────────────────────
    for gm in graph.get('god_modules', [])[:3]:
        opps.append({
            'id': f'refactor_{gm["module"]}',
            'title': f'Refactor god module: {gm["module"]}',
            'description': f'Imported by {gm["in_degree"]} other modules. Splitting it reduces coupling and makes isolated testing possible.',
            'difficulty': 'advanced', 'risk': 'high', 'category': 'refactoring',
        })

    cycle_count = graph.get('cycle_count', 0)
    if cycle_count > 0:
        opps.append({
            'id': 'break_cycles',
            'title': f'Break {cycle_count} circular dependenc{"ies" if cycle_count > 1 else "y"}',
            'description': 'Circular imports prevent tree-shaking, complicate testing, and can hide initialization order bugs.',
            'difficulty': 'advanced', 'risk': 'high', 'category': 'refactoring',
        })

    if structure:
        bus_factor = structure.get('bus_factor', 5)
        if bus_factor == 1:
            top = structure.get('top_contributors', [])
            contributor = top[0]['author'] if top else 'one contributor'
            opps.append({
                'id': 'bus_factor',
                'title': 'Spread knowledge across contributors',
                'description': f'{contributor} touches the vast majority of the codebase. Pair programming, documented onboarding, and mentoring reduce single-point-of-failure risk.',
                'difficulty': 'advanced', 'risk': 'medium', 'category': 'community',
            })

    return opps


_BEGINNER_LABELS = frozenset({'good first issue', 'hacktoberfest', 'up for grabs'})
_FEATURE_LABELS = frozenset({
    'enhancement', 'feature', 'feature request', 'feature-request',
    'type: enhancement', 'type: feature', 'type:enhancement', 'type:feature',
})


def _issue_opportunities(contribution_data: dict) -> list[dict]:
    pr_refs = set(contribution_data.get('pr_issue_refs', []))
    opps: list[dict] = []
    for issue in contribution_data.get('issues', []):
        labels_set = set(issue['labels'])
        is_beginner = bool(labels_set & _BEGINNER_LABELS)
        is_feature = bool(labels_set & _FEATURE_LABELS)

        if is_feature:
            category = 'feature'
        else:
            category = 'github-issue'

        if is_beginner:
            difficulty, risk = 'beginner', 'low'
        elif is_feature:
            difficulty, risk = 'intermediate', 'medium'
        else:
            difficulty, risk = 'intermediate', 'medium'

        opps.append({
            'id': f'issue_{issue["number"]}',
            'title': issue['title'],
            'description': issue['body_excerpt'] or f'Open GitHub issue #{issue["number"]}',
            'difficulty': difficulty,
            'risk': risk,
            'category': category,
            'issue_url': issue['url'],
            'issue_number': issue['number'],
            'has_open_pr': issue['number'] in pr_refs,
            'labels': issue['labels'],
        })
    return opps


def analyze_contributions(
    commits: dict,
    graph: dict,
    deps: dict,
    readme: dict | None,
    structure: dict | None,
    security: dict | None,
    contribution_data: dict | None = None,
) -> list[dict]:
    opps = _heuristic_opportunities(commits, graph, deps, readme, structure, security)
    if contribution_data:
        opps.extend(_issue_opportunities(contribution_data))
    return opps
