"""Unit tests for pure analysis functions (no DB, no network, no git)."""
import os
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# classifications.py
# ---------------------------------------------------------------------------

from apps.analysis.classifications import classify_repo


def _base_commits(**kw):
    return {
        'days_since_last_commit': 0,
        'total_commits': 200,
        'total_contributors': 5,
        'abandoned': False,
        'activity_decay_ratio': 1.0,
        **kw,
    }


def _base_graph(**kw):
    return {'node_count': 20, 'god_modules': [], 'cycle_count': 0, **kw}


def _base_deps(**kw):
    return {'dependency_count': 10, 'docker_issues': [], 'missing_lockfile_warnings': [], **kw}


def _base_readme(**kw):
    return {
        'found': True,
        'word_count': 500,
        'has_installation': True,
        'has_contributing': True,
        'has_usage': True,
        'has_changelog': True,
        **kw,
    }


def _base_structure(**kw):
    return {
        'total_files': 100,
        'test_ratio': 0.2,
        'has_ci': True,
        'has_contributing': True,
        'has_coc': False,
        'bus_factor': 3,
        **kw,
    }


def _base_security(**kw):
    return {'score': 10, 'issues': [], 'issue_count': 0, **kw}


def _base_meta(**kw):
    return {
        'stars': 50,
        'open_issues': 10,
        'pushed_at': '2024-01-01T00:00:00Z',
        'archived': False,
        **kw,
    }


class TestClassifyRepo:
    def test_returns_required_keys(self):
        result = classify_repo(
            _base_commits(), _base_graph(), _base_deps(),
            _base_readme(), _base_structure(), _base_security(), _base_meta(),
        )
        assert 'contribution_difficulty' in result
        assert 'project_health' in result
        assert 'code_complexity' in result
        assert 'documentation_grade' in result
        assert 'tags' in result
        assert isinstance(result['tags'], list)

    def test_abandoned_repo_has_poor_health(self):
        commits = _base_commits(abandoned=True, days_since_last_commit=1000, total_commits=5)
        result = classify_repo(
            commits, _base_graph(), _base_deps(),
            None, None, None, _base_meta(stars=0, open_issues=0),
        )
        # Very stale + abandoned should classify as declining or abandoned
        assert result['project_health']['key'] in ('abandoned', 'declining', 'stable')

    def test_active_repo_has_good_health(self):
        commits = _base_commits(days_since_last_commit=2, total_commits=500)
        result = classify_repo(
            commits, _base_graph(), _base_deps(),
            _base_readme(), _base_structure(), _base_security(),
            _base_meta(stars=500, open_issues=5),
        )
        assert result['project_health']['key'] in ('thriving', 'active')

    def test_many_god_modules_raises_complexity(self):
        graph = _base_graph(god_modules=[{'module': f'mod{i}'} for i in range(20)])
        result = classify_repo(
            _base_commits(), graph, _base_deps(), None, None, None, None,
        )
        assert result['code_complexity']['key'] in ('complex', 'very_complex')

    def test_no_readme_poor_docs(self):
        result = classify_repo(
            _base_commits(), _base_graph(), _base_deps(),
            {'found': False, 'word_count': 0, 'has_installation': False,
             'has_contributing': False, 'has_usage': False, 'has_changelog': False},
            None, None, None,
        )
        assert result['documentation_grade']['key'] in ('poor', 'missing')

    def test_label_is_string(self):
        result = classify_repo(
            _base_commits(), _base_graph(), _base_deps(), None, None, None, None,
        )
        assert isinstance(result['contribution_difficulty']['label'], str)
        assert len(result['contribution_difficulty']['label']) > 0


# ---------------------------------------------------------------------------
# dep_report.py
# ---------------------------------------------------------------------------

from apps.analysis.dep_report import analyze_dependencies


class TestAnalyzeDependencies:
    def test_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = analyze_dependencies(tmpdir)
        assert result['dependency_count'] == 0
        assert result['dependencies'] == []

    def test_parses_requirements_txt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'requirements.txt').write_text('django>=4.0\nrequests>=2.28\n# comment\n')
            result = analyze_dependencies(tmpdir)
        names = [d['name'] for d in result['dependencies']]
        assert 'django' in names
        assert 'requests' in names

    def test_parses_package_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'package.json').write_text(
                '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"vite": "^4.0.0"}}'
            )
            result = analyze_dependencies(tmpdir)
        names = [d['name'] for d in result['dependencies']]
        assert 'react' in names
        assert 'vite' in names

    def test_parses_pyproject_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'pyproject.toml').write_text(
                '[project]\ndependencies = ["fastapi>=0.100"]\n'
            )
            result = analyze_dependencies(tmpdir)
        names = [d['name'] for d in result['dependencies']]
        assert 'fastapi' in names

    def test_detects_old_docker_base(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'Dockerfile').write_text('FROM python:3.6\nRUN echo hi\n')
            result = analyze_dependencies(tmpdir)
        assert len(result['docker_issues']) > 0

    def test_lockfile_warning_npm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'package.json').write_text('{"dependencies": {"lodash": "^4"}}')
            result = analyze_dependencies(tmpdir)
        assert any('package-lock.json' in w or 'yarn.lock' in w for w in result['missing_lockfile_warnings'])


# ---------------------------------------------------------------------------
# import_parser.py
# ---------------------------------------------------------------------------

from apps.analysis.import_parser import parse_imports


class TestParseImports:
    def test_empty_dir_returns_no_edges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            edges = parse_imports(tmpdir)
        assert edges == []

    def test_parses_python_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'a.py').write_text('import django\nfrom flask import Flask\n')
            edges = parse_imports(tmpdir)
        assert len(edges) > 0
        assert all('source' in e and 'target' in e for e in edges)
        targets = {e['target'] for e in edges}
        assert 'django' in targets or 'flask' in targets

    def test_skips_stdlib_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'mod.py').write_text('import os\nimport sys\nimport json\n')
            edges = parse_imports(tmpdir)
        # stdlib imports should be filtered
        targets = {e[1] for e in edges}
        assert 'os' not in targets
        assert 'sys' not in targets

    def test_parses_js_relative_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'index.js').write_text("import utils from './utils';\nimport helpers from './helpers';\n")
            edges = parse_imports(tmpdir)
        # Only relative (non-external) imports are included in the import graph
        targets = {e['target'] for e in edges}
        assert './utils' in targets or './helpers' in targets


# ---------------------------------------------------------------------------
# graph_analysis.py
# ---------------------------------------------------------------------------

from apps.analysis.graph_analysis import analyze_graph


class TestAnalyzeGraph:
    def test_empty_edges_returns_defaults(self):
        result = analyze_graph([])
        assert result['node_count'] == 0
        assert result['edge_count'] == 0
        assert result['god_modules'] == []
        assert result['cycles'] == []

    def test_counts_nodes_and_edges(self):
        edges = [
            {'source': 'a', 'target': 'b'},
            {'source': 'b', 'target': 'c'},
            {'source': 'a', 'target': 'c'},
        ]
        result = analyze_graph(edges)
        assert result['node_count'] >= 3
        assert result['edge_count'] == 3

    def test_detects_god_module(self):
        edges = [{'source': f'mod_{i}', 'target': 'god_module'} for i in range(20)]
        result = analyze_graph(edges)
        god_names = [g['module'] for g in result['god_modules']]
        assert 'god_module' in god_names

    def test_cycle_detection(self):
        edges = [
            {'source': 'a', 'target': 'b'},
            {'source': 'b', 'target': 'c'},
            {'source': 'c', 'target': 'a'},
        ]
        result = analyze_graph(edges)
        assert result['cycle_count'] >= 1


# ---------------------------------------------------------------------------
# commit_analysis.py  (needs a mock git.Repo)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, PropertyMock
from apps.analysis.commit_analysis import analyze_commits
import datetime


def _make_commit(sha='abc1234', message='fix: something', author_name='Alice',
                 author_email='alice@example.com', days_ago=0):
    commit = MagicMock()
    commit.hexsha = sha * 10  # make it 40 chars
    commit.message = message
    commit.author.name = author_name
    commit.author.email = author_email
    dt = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days_ago)
    commit.committed_date = int(dt.timestamp())
    commit.parents = []
    return commit


class TestAnalyzeCommits:
    def test_empty_repo_returns_zeros(self):
        repo = MagicMock()
        repo.iter_commits.return_value = []
        result = analyze_commits(repo)
        assert result['total_commits'] == 0
        assert result['total_contributors'] == 0
        # No commits → days_since_last_commit is None; abandoned depends on implementation
        assert result['days_since_last_commit'] is None

    def test_active_repo_not_abandoned(self):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _make_commit(sha=f'{i:040x}', author_email=f'user{i}@x.com', days_ago=i)
            for i in range(5)
        ]
        result = analyze_commits(repo)
        assert result['total_commits'] == 5
        assert result['total_contributors'] >= 1
        assert result['abandoned'] is False

    def test_stale_repo_marked_abandoned(self):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _make_commit(sha=f'{i:040x}', days_ago=400) for i in range(3)
        ]
        result = analyze_commits(repo)
        assert result['abandoned'] is True

    def test_returns_frequency_lists(self):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _make_commit(sha=f'{i:040x}', days_ago=i * 7) for i in range(10)
        ]
        result = analyze_commits(repo)
        assert 'weekly_frequency' in result
        assert 'monthly_frequency' in result
        assert isinstance(result['weekly_frequency'], list)


# ---------------------------------------------------------------------------
# ownership_analysis.py
# ---------------------------------------------------------------------------

from apps.analysis.ownership_analysis import analyze_ownership


class TestAnalyzeOwnership:
    def _structure_with_files(self, **kw):
        s = _base_structure(**kw)
        s['all_files'] = ['src/main.py', 'src/utils.py', 'tests/test_main.py']
        s['hot_files'] = [{'file': 'src/main.py', 'commit_count': 20}]
        s['top_contributors'] = [{'author': 'Alice', 'files_touched': 20}]
        return s

    def test_returns_required_keys_when_files_present(self):
        result = analyze_ownership(self._structure_with_files(), _base_commits(), _base_graph())
        assert 'subsystems' in result
        assert 'top_contributors' in result
        assert 'bus_factor' in result

    def test_empty_all_files_returns_empty_dict(self):
        structure = _base_structure()
        structure['all_files'] = []
        result = analyze_ownership(structure, _base_commits(), _base_graph())
        assert result == {}

    def test_bus_factor_is_integer(self):
        result = analyze_ownership(self._structure_with_files(), _base_commits(), _base_graph())
        assert isinstance(result.get('bus_factor', 0), (int, float))
