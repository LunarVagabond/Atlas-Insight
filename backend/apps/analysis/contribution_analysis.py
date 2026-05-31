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
                'hints': [
                    'Create a file named `LICENSE` in the root directory of the project',
                    'Visit choosealicense.com to pick one — MIT is a popular permissive choice for open-source',
                    'Paste the full license text into the file and update any placeholder year or name',
                ],
            })
        if not structure.get('has_contributing'):
            opps.append({
                'id': 'add_contributing',
                'title': 'Add CONTRIBUTING.md',
                'description': 'No contributing guide. New contributors need to know how to set up the project, run tests, and open a PR.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
                'hints': [
                    'Create a file named `CONTRIBUTING.md` in the root directory',
                    'Include: how to fork and clone the repo, how to install dependencies, how to run tests, and how to open a pull request',
                    'Look at github.com/firstcontributions/first-contributions for a great example',
                ],
            })
        if not structure.get('has_changelog'):
            opps.append({
                'id': 'add_changelog',
                'title': 'Create a CHANGELOG',
                'description': 'No changelog exists. Maintainers and users have no structured way to track what changed between releases.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
                'hints': [
                    'Create a file named `CHANGELOG.md` in the root directory',
                    'Use the "Keep a Changelog" format: group changes under Added, Changed, Fixed, Removed per version',
                    'Start with an `[Unreleased]` section at the top for changes not yet in a release',
                ],
            })
        if not structure.get('has_coc'):
            opps.append({
                'id': 'add_coc',
                'title': 'Add a Code of Conduct',
                'description': 'No Code of Conduct. Signals community standards and protects contributors from harassment.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'community',
                'hints': [
                    'Create a file named `CODE_OF_CONDUCT.md` in the root directory',
                    'The Contributor Covenant (contributor-covenant.org) provides a ready-to-use template trusted by thousands of projects',
                    'Update the contact email placeholder in the template before committing',
                ],
            })
        if not structure.get('has_security_policy'):
            opps.append({
                'id': 'add_security_policy',
                'title': 'Add a SECURITY.md',
                'description': 'No security disclosure policy. Researchers and contributors have no clear channel to report vulnerabilities.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'security',
                'hints': [
                    'Create a file named `SECURITY.md` in the root directory',
                    'Explain how users should report a vulnerability — an email address or private GitHub issue works fine',
                    'Include which versions of the project are currently supported and receiving security fixes',
                ],
            })

    if readme:
        if not readme.get('found'):
            opps.append({
                'id': 'add_readme',
                'title': 'Create a README',
                'description': 'No README found. Every project needs one to explain what it does and how to get started.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
                'hints': [
                    'Create a file named `README.md` in the root directory',
                    'A good README includes: project name and description, installation steps, a usage example, and a link to contributing guidelines',
                    'Use Markdown formatting — GitHub renders it automatically as the project homepage',
                ],
            })
        else:
            if not readme.get('has_installation'):
                opps.append({
                    'id': 'readme_installation',
                    'title': 'Add installation instructions to README',
                    'description': 'README has no installation section — newcomers cannot get the project running without it.',
                    'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
                    'hints': [
                        'Open `README.md` in the root directory and add a `## Installation` section',
                        'List every step a new user needs to get the project running from scratch (dependencies, environment setup, build commands)',
                        'Wrap terminal commands in code fences (```bash ... ```) so they are easy to copy and paste',
                    ],
                })
            if not readme.get('has_usage'):
                opps.append({
                    'id': 'readme_usage',
                    'title': 'Add usage examples to README',
                    'description': 'README has no usage section. Code examples are the fastest way to show what the project does.',
                    'difficulty': 'beginner', 'risk': 'low', 'category': 'documentation',
                    'hints': [
                        'Open `README.md` and add a `## Usage` section after Installation',
                        'Show a minimal working example — a code snippet or terminal command that demonstrates the core feature',
                        'If it is a CLI tool, show common flags; if it is a library, show an import and a function call example',
                    ],
                })

    if security:
        if not security.get('gitignore_exists'):
            opps.append({
                'id': 'add_gitignore',
                'title': 'Add a .gitignore file',
                'description': 'No .gitignore found. Build artifacts, secrets, and editor files could be accidentally committed.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'security',
                'hints': [
                    'Create a file named `.gitignore` in the root directory (the dot at the start is important)',
                    'Visit gitignore.io and select your language or framework to auto-generate a solid starting template',
                    'Files listed in `.gitignore` will never be tracked by git — always ignore secrets, build output, and editor config',
                ],
            })
        elif security.get('gitignore_gaps'):
            gaps = security['gitignore_gaps']
            gap_str = ', '.join(f'`{g}`' for g in gaps[:5])
            opps.append({
                'id': 'gitignore_gaps',
                'title': f'Fix .gitignore — {len(gaps)} missing pattern{"s" if len(gaps) != 1 else ""}',
                'description': f'Patterns not covered: {", ".join(gaps[:5])}. Risk of accidentally committing sensitive files or noise.',
                'difficulty': 'beginner', 'risk': 'low', 'category': 'security',
                'hints': [
                    'Open `.gitignore` in the root directory',
                    f'Add these missing patterns: {gap_str}',
                    'Each line is a pattern — `*.log` ignores all log files, `build/` ignores the whole build folder',
                ],
            })

    if structure and structure.get('roadmap_file'):
        roadmap_file = structure['roadmap_file']
        opps.append({
            'id': 'roadmap',
            'title': f'Review the project roadmap ({roadmap_file})',
            'description': 'A roadmap file exists — it likely lists planned features and known gaps. Good starting point for finding impactful work that aligns with maintainer intent.',
            'difficulty': 'beginner', 'risk': 'low', 'category': 'feature',
            'hints': [
                f'Open `{roadmap_file}` to see what the maintainers have planned',
                'Look for items marked TODO, [ ], or "planned" — these are features the project wants but has not built yet',
                'Before starting work on a roadmap item, open a GitHub issue to let maintainers know you are working on it',
            ],
        })

    for i, warning in enumerate(deps.get('missing_lockfile_warnings', [])[:2]):
        opps.append({
            'id': f'lockfile_{i}',
            'title': 'Add a package lockfile',
            'description': f'{warning}. Lockfiles ensure reproducible installs across machines and CI.',
            'difficulty': 'beginner', 'risk': 'low', 'category': 'dependencies',
            'hints': [
                'Run your package manager\'s install command to generate the lockfile (e.g., `npm install`, `yarn install`, `pip freeze > requirements.txt`)',
                'Commit the generated lockfile — it pins exact dependency versions so every contributor gets identical packages',
                'Do not edit the lockfile by hand; let the package manager manage it',
            ],
        })

    # ── Intermediate / Medium risk ────────────────────────────────────────────
    if structure:
        if not structure.get('has_ci'):
            opps.append({
                'id': 'add_ci',
                'title': 'Set up a CI pipeline',
                'description': 'No CI configuration found. Automated testing on PRs prevents regressions and speeds up code review.',
                'difficulty': 'intermediate', 'risk': 'low', 'category': 'ci',
                'hints': [
                    'Create the directory `.github/workflows/` and add a file called `ci.yml` inside it',
                    'GitHub Actions will automatically run this workflow on every push and pull request — no extra setup needed',
                    'Start simple: check out the code, install dependencies, then run your project\'s test command',
                ],
            })
        if not structure.get('has_lint_config'):
            opps.append({
                'id': 'add_linting',
                'title': 'Add a linting configuration',
                'description': 'No linter config found. Consistent code style reduces review friction and catches simple errors automatically.',
                'difficulty': 'intermediate', 'risk': 'low', 'category': 'ci',
                'hints': [
                    'Add a linter config file to the root — `.eslintrc.js` for JavaScript, `pyproject.toml` for Python (with ruff or flake8), `.rubocop.yml` for Ruby',
                    'Linters check your code for style mistakes and common bugs before you even run it',
                    'Run the linter locally before committing so CI does not surprise you with failures',
                ],
            })
        test_ratio = structure.get('test_ratio', 0)
        if test_ratio < 0.05:
            opps.append({
                'id': 'add_tests',
                'title': f'Add test coverage ({test_ratio:.0%} test file ratio)',
                'description': 'Very few test files relative to source. Even basic unit tests for core modules substantially improve confidence in changes.',
                'difficulty': 'intermediate', 'risk': 'medium', 'category': 'testing',
                'hints': [
                    'Look for an existing `tests/` or `test/` directory to see how current tests are structured',
                    'Start by writing a test for the simplest function you can find — just check that it returns the expected output for a known input',
                    'Run the test suite with the project\'s test command (often `pytest`, `npm test`, or `cargo test`) to confirm your test passes',
                ],
            })
        elif test_ratio < 0.15:
            opps.append({
                'id': 'improve_tests',
                'title': f'Improve test coverage ({test_ratio:.0%} test file ratio)',
                'description': 'Below-average test file ratio. Adding tests for core functionality reduces regression risk on future contributions.',
                'difficulty': 'intermediate', 'risk': 'medium', 'category': 'testing',
                'hints': [
                    'Open the `tests/` directory and look for source files that have no corresponding test file',
                    'Pick a small, self-contained function and write a few test cases covering normal and edge-case inputs',
                    'Run the full test suite after adding tests to make sure nothing is broken',
                ],
            })

    for i, di in enumerate(deps.get('docker_issues', [])[:3]):
        opps.append({
            'id': f'docker_{i}',
            'title': f'Update Dockerfile: {di["file"]}',
            'description': di['issue'],
            'difficulty': 'intermediate', 'risk': 'medium', 'category': 'dependencies',
            'hints': [
                f'Open `{di["file"]}` in the project',
                f'The specific issue is: {di["issue"]}',
                'The Docker documentation at docs.docker.com/develop/develop-images/dockerfile_best-practices/ has guidance on common Dockerfile improvements',
            ],
        })

    # ── Advanced / High risk ──────────────────────────────────────────────────
    for gm in graph.get('god_modules', [])[:3]:
        opps.append({
            'id': f'refactor_{gm["module"]}',
            'title': f'Refactor god module: {gm["module"]}',
            'description': f'Imported by {gm["in_degree"]} other modules. Splitting it reduces coupling and makes isolated testing possible.',
            'difficulty': 'advanced', 'risk': 'high', 'category': 'refactoring',
            'hints': [
                f'Open `{gm["module"]}` — it is imported by {gm["in_degree"]} other files, which makes changes here risky',
                'Read through the file and identify two or three distinct responsibilities that could live in separate files',
                'Start small: extract one clearly separate piece of logic into a new file, update all the imports, then run the tests before touching anything else',
            ],
        })

    cycle_count = graph.get('cycle_count', 0)
    if cycle_count > 0:
        cycles_sample = graph.get('cycles', [])[:2]
        cycle_hint = ''
        if cycles_sample:
            cycle_hint = f'For example: {" → ".join(cycles_sample[0][:3])}{"…" if len(cycles_sample[0]) > 3 else ""}'
        opps.append({
            'id': 'break_cycles',
            'title': f'Break {cycle_count} circular dependenc{"ies" if cycle_count > 1 else "y"}',
            'description': 'Circular imports prevent tree-shaking, complicate testing, and can hide initialization order bugs.',
            'difficulty': 'advanced', 'risk': 'high', 'category': 'refactoring',
            'hints': [
                'Open the Architecture tab in this tool to see which files form circular import chains',
                *([f'Example cycle: {cycle_hint}'] if cycle_hint else []),
                'The fix is usually to extract the shared code both modules need into a third module that neither end imports from',
                'Start with the shortest cycle — they are the easiest to untangle',
            ],
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
                'hints': [
                    'Check the Architecture tab\'s Hot Files section to find the most frequently changed files',
                    'Look at the git log for files that only one or two people have ever touched — those are the knowledge gaps',
                    'Great first steps: add inline comments explaining tricky sections, document the setup process, or pair with the main contributor on a small change',
                ],
            })

    return opps


_BEGINNER_LABELS = frozenset({'good first issue', 'hacktoberfest', 'up for grabs'})
_FEATURE_LABELS = frozenset({
    'enhancement', 'feature', 'feature request', 'feature-request',
    'type: enhancement', 'type: feature', 'type:enhancement', 'type:feature',
})


def _issue_readiness(issue: dict, pr_refs: set) -> tuple[int, str]:
    """Score 0–100 for how ready an issue is for a new contributor."""
    score = 50
    labels_set = set(issue.get('labels', []))
    if labels_set & _BEGINNER_LABELS:
        score += 35
    elif labels_set & _FEATURE_LABELS:
        score += 10
    body = issue.get('body_excerpt', '') or ''
    if len(body) > 200:
        score += 15
    elif len(body) > 50:
        score += 5
    if issue.get('number') in pr_refs:
        score -= 25
    score = max(0, min(100, score))
    if score >= 75:
        label = 'Ready'
    elif score >= 50:
        label = 'Approachable'
    else:
        label = 'Complex'
    return score, label


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

        readiness_score, readiness_label = _issue_readiness(issue, pr_refs)

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
            'readiness_score': readiness_score,
            'readiness_label': readiness_label,
            'hints': [
                'Read the full issue description and all comments on GitHub to understand exactly what is being asked for',
                'Search the codebase for the function, file, or keyword mentioned in the issue before writing any code',
                'Leave a comment on the issue saying you would like to work on it — maintainers appreciate knowing someone is on it',
            ],
        })
    return opps


_TODO_PRIORITY = {'BUG': 0, 'FIXME': 1, 'HACK': 2, 'XXX': 3, 'TODO': 4, 'OPTIMIZE': 5}
_TODO_DIFFICULTY = {'BUG': 'beginner', 'FIXME': 'beginner', 'HACK': 'intermediate', 'XXX': 'intermediate', 'TODO': 'beginner', 'OPTIMIZE': 'beginner'}
_TODO_RISK = {'BUG': 'medium', 'FIXME': 'medium', 'HACK': 'medium', 'XXX': 'medium', 'TODO': 'low', 'OPTIMIZE': 'low'}


def _todo_opportunities(todos: dict) -> list[dict]:
    """One contribution card per code marker, prioritised by severity."""
    items = todos.get('items', [])
    sorted_items = sorted(items, key=lambda m: (_TODO_PRIORITY.get(m['type'].upper(), 9), m['file'], m['line']))

    opps = []
    for m in sorted_items[:20]:
        mtype = m['type'].upper()
        basename = m['file'].split('/')[-1]
        text = m['text'].strip() if m['text'] else ''
        title = f'{mtype}: {text[:60]}' if text else f'Resolve {mtype} in {basename}'
        desc = (
            f'`{m["file"]}` line {m["line"]} contains a {mtype} marker'
            + (f': "{text}"' if text else '') + '.'
        )
        hints = [
            f'Open `{m["file"]}` at line {m["line"]}',
            'Read the surrounding context to understand what was left unfinished',
            'Fix, remove, or convert to a tracked issue if out of scope for a quick PR',
        ]
        opps.append({
            'id': f'todo_{mtype}_{basename}_{m["line"]}',
            'title': title,
            'description': desc,
            'difficulty': _TODO_DIFFICULTY.get(mtype, 'beginner'),
            'risk': _TODO_RISK.get(mtype, 'low'),
            'category': 'refactoring',
            'hints': hints,
        })
    return opps


def _revert_opportunities(commits: dict) -> list[dict]:
    """Generate opportunities from files with repeated reverted commits."""
    import collections as _coll
    file_revert_count: dict[str, int] = _coll.defaultdict(int)
    for rc in commits.get('reverted_commits', []):
        for f in rc.get('files', []):
            file_revert_count[f] += 1

    opps = []
    for file, count in sorted(file_revert_count.items(), key=lambda kv: -kv[1]):
        if count < 3:
            continue
        basename = file.split('/')[-1]
        opps.append({
            'id': f'revert_hotspot_{basename}',
            'title': f'Investigate historically problematic area: {basename}',
            'description': f'{file} has been part of {count} reverted commits, suggesting recurring instability or unclear requirements.',
            'difficulty': 'intermediate',
            'risk': 'medium',
            'category': 'refactoring',
            'hints': [
                f'Open `{file}` and read through its git history: `git log --follow -p {file}`',
                'Look for recurring patterns in the reverted changes — they often reveal a missing abstraction or unclear ownership',
                'Consider adding tests before making changes to catch regressions early',
            ],
        })
        if len(opps) >= 5:
            break
    return opps


_CATEGORY_DOMAINS: dict[str, list[str]] = {
    'documentation': ['documentation'],
    'community': ['community'],
    'ci': ['devops', 'ci'],
    'testing': ['testing'],
    'security': ['security'],
    'dependencies': ['dependencies'],
}

_FILE_SUBSYSTEM_PREFIXES: dict[str, list[str]] = {
    'frontend': ['src/', 'frontend/', 'client/', 'ui/', 'app/', 'web/', 'pages/', 'components/'],
    'api': ['api/', 'routes/', 'routers/', 'endpoints/', 'views/', 'handlers/', 'controllers/', 'server/'],
    'data': ['models/', 'db/', 'database/', 'migrations/', 'schemas/', 'repositories/'],
    'tests': ['tests/', '__tests__/', 'spec/', 'test/', 'e2e/', 'integration/'],
    'config': ['config/', 'scripts/', '.github/', 'ci/', 'infra/', 'deploy/'],
}


def _domain_from_file(path: str) -> str:
    lower = path.lower()
    for domain, prefixes in _FILE_SUBSYSTEM_PREFIXES.items():
        if any(lower.startswith(p) for p in prefixes):
            return domain
    return 'general'


def _effort_estimate(difficulty: str, risk: str) -> str:
    if difficulty == 'beginner' and risk == 'low':
        return 'quick-win'
    if (difficulty == 'beginner' and risk == 'medium') or (difficulty == 'intermediate' and risk == 'low'):
        return 'small'
    if difficulty == 'intermediate' and risk == 'medium':
        return 'medium'
    return 'large'


def _annotate_feasibility(opps: list[dict]) -> None:
    """Patch each opp dict in place with knowledge_domains, effort_estimate, affected_file_count."""
    for opp in opps:
        cat = opp.get('category', '')
        diff = opp.get('difficulty', 'beginner')
        risk = opp.get('risk', 'low')

        # knowledge_domains
        if cat in _CATEGORY_DOMAINS:
            domains = _CATEGORY_DOMAINS[cat]
        elif cat == 'refactoring':
            # Derive from file path in id or hints
            opp_id = opp.get('id', '')
            # TODO cards have id like 'todo_FIXME_filename_42'
            file_hint = ''
            for hint in opp.get('hints', []):
                if hint.startswith('Open `'):
                    file_hint = hint[6:].split('`')[0]
                    break
            domains = [_domain_from_file(file_hint)] if file_hint else ['general']
        else:
            domains = []

        opp['knowledge_domains'] = domains
        opp['effort_estimate'] = _effort_estimate(diff, risk)

        # affected_file_count
        if opp.get('id', '').startswith('todo_'):
            opp['affected_file_count'] = 1
        elif opp.get('id', '').startswith('revert_hotspot_'):
            opp['affected_file_count'] = 0  # unknown without git data
        else:
            opp['affected_file_count'] = 0


def analyze_contributions(
    commits: dict,
    graph: dict,
    deps: dict,
    readme: dict | None,
    structure: dict | None,
    security: dict | None,
    contribution_data: dict | None = None,
    todos: dict | None = None,
) -> list[dict]:
    opps = _heuristic_opportunities(commits, graph, deps, readme, structure, security)
    if todos:
        opps.extend(_todo_opportunities(todos))
    opps.extend(_revert_opportunities(commits))
    if contribution_data:
        opps.extend(_issue_opportunities(contribution_data))
    _annotate_feasibility(opps)
    return opps
