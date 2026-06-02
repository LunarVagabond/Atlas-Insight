import tempfile
from pathlib import Path

import pytest


# ── file_tree ─────────────────────────────────────────────────────────────────

class TestWalkFiles:
    def test_yields_files(self):
        from apps.analysis.project_structure.file_tree import walk_files
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'a.py').write_text('x')
            (base / 'b.py').write_text('x')
            found = list(walk_files(base))
            assert len(found) == 2

    def test_skips_node_modules(self):
        from apps.analysis.project_structure.file_tree import walk_files
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'node_modules').mkdir()
            (base / 'node_modules' / 'pkg.js').write_text('x')
            (base / 'main.js').write_text('x')
            found = list(walk_files(base))
            assert len(found) == 1
            assert found[0].name == 'main.js'

    def test_respects_max_files(self):
        from apps.analysis.project_structure.file_tree import walk_files
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for i in range(5):
                (base / f'f{i}.py').write_text('x')
            found = list(walk_files(base, max_files=3))
            assert len(found) == 3


class TestIsTestFile:
    def test_test_prefix(self):
        from apps.analysis.project_structure.file_tree import is_test_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = base / 'test_something.py'
            p.touch()
            assert is_test_file(p, base) is True

    def test_test_suffix(self):
        from apps.analysis.project_structure.file_tree import is_test_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = base / 'something_test.py'
            p.touch()
            assert is_test_file(p, base) is True

    def test_tests_directory(self):
        from apps.analysis.project_structure.file_tree import is_test_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'tests').mkdir()
            p = base / 'tests' / 'helpers.py'
            p.touch()
            assert is_test_file(p, base) is True

    def test_non_test_file(self):
        from apps.analysis.project_structure.file_tree import is_test_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = base / 'main.py'
            p.touch()
            assert is_test_file(p, base) is False

    def test_spec_suffix(self):
        from apps.analysis.project_structure.file_tree import is_test_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = base / 'app.spec.ts'
            p.touch()
            assert is_test_file(p, base) is True


class TestFindFile:
    def test_finds_first_match(self):
        from apps.analysis.project_structure.file_tree import find_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / 'LICENSE.md').write_text('MIT')
            result = find_file(base, ['LICENSE', 'LICENSE.md', 'LICENSE.txt'])
            assert result == 'LICENSE.md'

    def test_returns_none_when_absent(self):
        from apps.analysis.project_structure.file_tree import find_file
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            result = find_file(base, ['LICENSE', 'LICENSE.md'])
            assert result is None


# ── tech_stack ────────────────────────────────────────────────────────────────

class TestDetectTechStack:
    def test_detects_from_deps(self):
        from apps.analysis.project_structure.tech_stack import detect_tech_stack
        with tempfile.TemporaryDirectory() as d:
            deps = [{'name': 'django', 'version_spec': '>=4.0'}, {'name': 'celery', 'version_spec': '>=5.0'}]
            result = detect_tech_stack(d, deps)
            assert 'Django' in result
            assert 'Celery' in result

    def test_detects_from_config_files(self):
        from apps.analysis.project_structure.tech_stack import detect_tech_stack
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'manage.py').write_text('# django')
            result = detect_tech_stack(d, [])
            assert 'Django' in result

    def test_empty_project(self):
        from apps.analysis.project_structure.tech_stack import detect_tech_stack
        with tempfile.TemporaryDirectory() as d:
            result = detect_tech_stack(d, [])
            assert isinstance(result, list)

    def test_framework_packages_frozenset(self):
        from apps.analysis.project_structure.tech_stack import FRAMEWORK_PACKAGES
        assert isinstance(FRAMEWORK_PACKAGES, frozenset)
        assert 'django' in FRAMEWORK_PACKAGES
        assert 'react' in FRAMEWORK_PACKAGES


# ── branch_detection ─────────────────────────────────────────────────────────

class TestDetectStaleBranches:
    def test_no_remote_returns_empty(self):
        from unittest.mock import MagicMock
        from apps.analysis.project_structure.branch_detection import detect_stale_branches
        repo = MagicMock()
        repo.remote.side_effect = Exception('no remote')
        stale, count = detect_stale_branches(repo)
        assert stale == []
        assert count == 0

    def test_stale_branch_detected(self):
        from unittest.mock import MagicMock, patch
        from apps.analysis.project_structure.branch_detection import detect_stale_branches
        from datetime import datetime, timezone, timedelta
        repo = MagicMock()
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(days=120)).timestamp()
        ref = MagicMock()
        ref.name = 'origin/old-feature'
        ref.commit.committed_date = old_ts
        repo.remote.return_value.refs = [ref]
        stale, count = detect_stale_branches(repo)
        assert count == 1
        assert stale[0]['days_ago'] >= 120

    def test_fresh_branch_not_stale(self):
        from unittest.mock import MagicMock
        from apps.analysis.project_structure.branch_detection import detect_stale_branches
        from datetime import datetime, timezone, timedelta
        repo = MagicMock()
        fresh_ts = (datetime.now(tz=timezone.utc) - timedelta(days=10)).timestamp()
        ref = MagicMock()
        ref.name = 'origin/main'
        ref.commit.committed_date = fresh_ts
        repo.remote.return_value.refs = [ref]
        stale, count = detect_stale_branches(repo)
        assert count == 0


# ── community ─────────────────────────────────────────────────────────────────

class TestDetectLicenseType:
    def test_mit(self):
        from apps.analysis.project_structure.community import detect_license_type
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('MIT License\nPermission is hereby granted...')
            fname = f.name
        result = detect_license_type(Path(fname))
        assert result == 'MIT'

    def test_apache(self):
        from apps.analysis.project_structure.community import detect_license_type
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('Apache License Version 2.0')
            fname = f.name
        result = detect_license_type(Path(fname))
        assert result == 'Apache-2.0'

    def test_unknown_returns_other(self):
        from apps.analysis.project_structure.community import detect_license_type
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('Some custom license text with no known pattern')
            fname = f.name
        result = detect_license_type(Path(fname))
        assert result == 'Other'

    def test_missing_file_returns_none(self):
        from apps.analysis.project_structure.community import detect_license_type
        result = detect_license_type(Path('/nonexistent/path/LICENSE'))
        assert result is None


# ── contribution_analysis submodules ─────────────────────────────────────────

class TestHeuristicOpportunities:
    def test_no_license_generates_opp(self):
        from apps.analysis.contribution_analysis.heuristics import generate_heuristic_opportunities
        structure = {'license_file': None, 'license_type': None, 'has_contributing': True,
                     'has_changelog': True, 'has_coc': True, 'has_security_policy': True}
        opps = generate_heuristic_opportunities({}, {}, {}, None, structure, None)
        ids = [o['id'] for o in opps]
        assert 'add_license' in ids

    def test_low_test_ratio_generates_opp(self):
        from apps.analysis.contribution_analysis.heuristics import generate_heuristic_opportunities
        structure = {'test_ratio': 0.02, 'has_ci': True, 'has_lint_config': True,
                     'license_file': 'LICENSE', 'has_contributing': True,
                     'has_changelog': True, 'has_coc': True, 'has_security_policy': True}
        opps = generate_heuristic_opportunities({}, {}, {}, None, structure, None)
        ids = [o['id'] for o in opps]
        assert 'add_tests' in ids

    def test_no_issues_empty(self):
        from apps.analysis.contribution_analysis.heuristics import generate_heuristic_opportunities
        opps = generate_heuristic_opportunities(
            {'reverted_commits': []}, {'god_modules': [], 'cycle_count': 0},
            {}, None, None, None,
        )
        assert isinstance(opps, list)


class TestIssueReadiness:
    def test_beginner_label_boosts_score(self):
        from apps.analysis.contribution_analysis.issue_ops import score_issue_readiness
        issue = {'labels': ['good first issue'], 'body_excerpt': 'x' * 300, 'number': 1}
        score, label = score_issue_readiness(issue, set())
        assert score >= 75
        assert label == 'Ready'

    def test_has_open_pr_reduces_score(self):
        from apps.analysis.contribution_analysis.issue_ops import score_issue_readiness
        issue = {'labels': [], 'body_excerpt': '', 'number': 42}
        score_without, _ = score_issue_readiness(issue, set())
        score_with, _ = score_issue_readiness(issue, {42})
        assert score_with < score_without


class TestTodoOpportunities:
    def test_bug_sorted_before_todo(self):
        from apps.analysis.contribution_analysis.todo_ops import generate_todo_opportunities
        todos = {
            'items': [
                {'type': 'TODO', 'file': 'a.py', 'line': 1, 'text': 'add feature'},
                {'type': 'BUG', 'file': 'b.py', 'line': 5, 'text': 'fix crash'},
            ]
        }
        opps = generate_todo_opportunities(todos)
        assert opps[0]['id'].startswith('todo_BUG')

    def test_revert_hotspot_threshold(self):
        from apps.analysis.contribution_analysis.todo_ops import generate_revert_opportunities
        commits = {
            'reverted_commits': [
                {'files': ['hot.py']},
                {'files': ['hot.py']},
                {'files': ['hot.py']},
            ]
        }
        opps = generate_revert_opportunities(commits)
        assert len(opps) == 1
        assert 'hot.py' in opps[0]['id']

    def test_revert_below_threshold_ignored(self):
        from apps.analysis.contribution_analysis.todo_ops import generate_revert_opportunities
        commits = {'reverted_commits': [{'files': ['cold.py']}, {'files': ['cold.py']}]}
        opps = generate_revert_opportunities(commits)
        assert len(opps) == 0


class TestFeasibility:
    def test_effort_estimate_quick_win(self):
        from apps.analysis.contribution_analysis.feasibility import effort_estimate
        assert effort_estimate('beginner', 'low') == 'quick-win'

    def test_effort_estimate_large(self):
        from apps.analysis.contribution_analysis.feasibility import effort_estimate
        assert effort_estimate('advanced', 'high') == 'large'

    def test_domain_from_file_frontend(self):
        from apps.analysis.contribution_analysis.feasibility import domain_from_file
        assert domain_from_file('src/components/Button.vue') == 'frontend'

    def test_domain_from_file_general(self):
        from apps.analysis.contribution_analysis.feasibility import domain_from_file
        assert domain_from_file('utils/helpers.py') == 'general'

    def test_annotate_adds_effort(self):
        from apps.analysis.contribution_analysis.feasibility import annotate_feasibility
        opps = [{'id': 'add_license', 'category': 'community', 'difficulty': 'beginner', 'risk': 'low', 'hints': []}]
        annotate_feasibility(opps)
        assert opps[0]['effort_estimate'] == 'quick-win'
        assert 'knowledge_domains' in opps[0]
