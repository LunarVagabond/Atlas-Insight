"""Extended JIT endpoint tests: ai_summary, file_history live call, vulns with deps."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client

from apps.repositories.models import AnalysisRun, Repository

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def repo(db):
    return Repository.objects.create(
        url='https://github.com/jit/extended', owner='jit', name='extended'
    )


@pytest.fixture
def rich_result():
    return {
        'github_meta': {
            'primary_language': 'Python',
            'stars': 250,
            'description': 'A great project',
            'open_prs': 3,
        },
        'commits': {
            'total_commits': 500,
            'total_contributors': 8,
            'active_contributor_count_90d': 3,
            'top_contributors': [
                {'author': 'alice', 'commits': 100},
                {'author': 'bob', 'commits': 50},
            ],
            'weekly_frequency': [1, 2],
            'monthly_frequency': [10],
            'contributor_churn': [0.2],
            'commit_conventions': {'style': 'conventional', 'format_template': '<type>: <subject>'},
        },
        'heuristics': [
            {'signal': 'burnout', 'score': 60, 'label': 'Burnout Risk', 'description': ''}
        ],
        'dependencies': {
            'dependency_count': 3,
            'dependencies': [
                {'name': 'requests', 'version': '2.28.0', 'ecosystem': 'pip', 'dev': False},
                {'name': 'django', 'version': '4.2.0', 'ecosystem': 'pip', 'dev': False},
            ],
        },
        'structure': {
            'total_files': 120,
            'total_loc': 8000,
            'test_ratio': 0.15,
            'hot_files': [{'file': 'src/main.py', 'changes': 30}],
            'languages': [{'name': 'Python', 'pct': 95}, {'name': 'Shell', 'pct': 5}],
        },
        'graph': {
            'node_count': 25,
            'edge_count': 60,
            'cycle_count': 1,
            'god_modules': [{'module': 'src/core.py'}],
        },
        'security': {'issues': [], 'vulnerabilities': []},
        'oss_score': {'score': 7.5, 'badge': 'thriving', 'label': 'Thriving'},
        'classification': {
            'project_health': {'key': 'thriving', 'label': 'Thriving', 'score': 8},
            'contribution_difficulty': {'key': 'moderate', 'label': 'Moderate', 'score': 5},
            'code_complexity': {'key': 'medium', 'label': 'Medium', 'score': 5},
            'documentation_grade': {'key': 'good', 'label': 'Good', 'score': 6},
            'tags': ['python', 'web'],
        },
        'repo_type': {'type': 'single', 'sub_projects': []},
        'arch_tours': [
            {'name': 'Core', 'entry_files': ['src/core.py', 'src/models.py']},
        ],
        'contribution_opportunities': [
            {
                'title': 'Fix null pointer',
                'difficulty': 'easy',
                'issue_number': 42,
                'has_open_pr': False,
            }
        ],
    }


@pytest.fixture
def completed_run(repo, rich_result):
    return AnalysisRun.objects.create(repo=repo, status='completed', result=rich_result)


@pytest.mark.django_db
class TestAiSummary:
    def test_returns_summary_text(self, completed_run):
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/ai-summary')
        assert resp.status_code == 200
        data = resp.json()
        assert 'summary' in data
        assert 'extended' in data['summary']
        assert 'Python' in data['summary']

    def test_summary_includes_contributors(self, completed_run):
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/ai-summary')
        assert resp.status_code == 200
        assert 'alice' in resp.json()['summary']

    def test_summary_includes_hot_files(self, completed_run):
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/ai-summary')
        assert resp.status_code == 200
        assert 'src/main.py' in resp.json()['summary']

    def test_summary_includes_open_tasks(self, completed_run):
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/ai-summary')
        assert resp.status_code == 200
        assert 'Fix null pointer' in resp.json()['summary']

    def test_summary_includes_commit_convention(self, completed_run):
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/ai-summary')
        assert resp.status_code == 200
        assert 'conventional' in resp.json()['summary']

    def test_not_completed_run_returns_404(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/ai-summary')
        assert resp.status_code == 404

    def test_unknown_run_returns_404(self):
        resp = Client().get(f'/api/v1/repositories/runs/{uuid.uuid4()}/ai-summary')
        assert resp.status_code == 404

    def test_private_run_anonymous_returns_403(self, db):
        repo = Repository.objects.create(
            url='https://github.com/priv/ai', owner='priv', name='ai', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/ai-summary')
        assert resp.status_code == 403

    def test_private_run_owner_can_access(self, db):
        user = User.objects.create_user(username='ai_owner', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/aimine', owner='priv', name='aimine', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={}, user=user)
        c = Client()
        c.force_login(user)
        resp = c.get(f'/api/v1/repositories/runs/{run.id}/ai-summary')
        assert resp.status_code == 200

    def test_summary_with_security_vulns(self, repo):
        result = {
            'github_meta': {'primary_language': 'Python', 'description': ''},
            'structure': {'languages': [{'name': 'Python', 'pct': 100}]},
            'security': {
                'vulnerabilities': [
                    {'name': 'lodash', 'version': '4.0.0', 'vuln_id': 'CVE-2021-1234', 'severity': 'HIGH'}
                ],
                'issues': ['possible secret in .env'],
            },
            'commits': {},
            'dependencies': {},
            'graph': {},
            'oss_score': {},
            'classification': {},
            'repo_type': {},
            'arch_tours': [],
            'contribution_opportunities': [],
        }
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=result)
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/ai-summary')
        assert resp.status_code == 200
        assert 'lodash' in resp.json()['summary']


@pytest.mark.django_db
class TestFileHistoryLiveCall:
    @patch('requests.get')
    def test_fetches_from_github_on_cache_miss(self, mock_get, completed_run):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [
            {
                'sha': 'abc1234567890',
                'commit': {
                    'message': 'fix: resolve #99 crash',
                    'author': {'name': 'alice', 'date': '2024-01-01T00:00:00Z'},
                },
                'html_url': 'https://github.com/jit/extended/commit/abc123',
            }
        ]
        mock_get.return_value = mock_resp

        resp = Client().get(
            f'/api/v1/repositories/runs/{completed_run.id}/file-history',
            {'path': 'src/main.py'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['path'] == 'src/main.py'
        assert len(data['commits']) == 1
        assert data['commits'][0]['author'] == 'alice'
        assert data['commits'][0]['issue_refs'] == [99]

    @patch('requests.get')
    def test_github_failure_returns_502(self, mock_get, completed_run):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_get.return_value = mock_resp

        resp = Client().get(
            f'/api/v1/repositories/runs/{completed_run.id}/file-history',
            {'path': 'src/main.py'},
        )
        assert resp.status_code == 502

    @patch('requests.get')
    def test_result_is_cached(self, mock_get, completed_run):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        path = 'README.md'
        Client().get(
            f'/api/v1/repositories/runs/{completed_run.id}/file-history',
            {'path': path},
        )
        Client().get(
            f'/api/v1/repositories/runs/{completed_run.id}/file-history',
            {'path': path},
        )
        assert mock_get.call_count == 1

    def test_private_run_anonymous_returns_403(self, db):
        repo = Repository.objects.create(
            url='https://github.com/priv/fh', owner='priv', name='fh', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
        resp = Client().get(
            f'/api/v1/repositories/runs/{run.id}/file-history',
            {'path': 'README.md'},
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestVulnerabilitiesWithDeps:
    @patch('apps.analysis.vuln_scan._enrich_vulns')
    @patch('requests.post')
    def test_queries_osv_for_deps(self, mock_post, mock_enrich, repo):
        result = {
            'dependencies': {
                'dependencies': [
                    {'name': 'lodash', 'version': '4.17.15', 'ecosystem': 'npm'},
                    {'name': 'requests', 'version': '2.25.0', 'ecosystem': 'pip'},
                ]
            }
        }
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=result)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            'results': [
                {'vulns': [{'id': 'GHSA-1234'}]},
                {'vulns': []},
            ]
        }
        mock_post.return_value = mock_resp
        mock_enrich.return_value = {
            'GHSA-1234': {
                'summary': 'Prototype pollution',
                'severity': 'HIGH',
                'severity_score': 8.1,
            }
        }

        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/vulnerabilities')
        assert resp.status_code == 200
        data = resp.json()
        assert data['checked'] == 2
        assert len(data['vulnerable']) == 1
        assert data['vulnerable'][0]['vuln_id'] == 'GHSA-1234'
        assert data['vulnerable'][0]['severity'] == 'HIGH'

    @patch('requests.post')
    def test_osv_failure_returns_502(self, mock_post, repo):
        result = {
            'dependencies': {
                'dependencies': [
                    {'name': 'lodash', 'version': '4.17.15', 'ecosystem': 'npm'},
                ]
            }
        }
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=result)
        mock_post.side_effect = Exception('OSV down')

        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/vulnerabilities')
        assert resp.status_code == 502

    def test_deps_missing_fields_skipped(self, repo):
        result = {
            'dependencies': {
                'dependencies': [
                    {'name': 'lodash'},
                    {'name': '', 'version': '1.0', 'ecosystem': 'npm'},
                ]
            }
        }
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=result)
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/vulnerabilities')
        assert resp.status_code == 200
        data = resp.json()
        assert data['checked'] == 0


@pytest.mark.django_db
class TestJitPrivateAccess:
    """Verify 403 path for issues/prs/diff/similar on private repos."""

    def _private_run(self):
        repo = Repository.objects.create(
            url='https://github.com/priv/jit', owner='priv', name='jit', is_private=True
        )
        return AnalysisRun.objects.create(repo=repo, status='completed', result={})

    def test_issues_private_anonymous_403(self, db):
        run = self._private_run()
        assert Client().get(f'/api/v1/repositories/runs/{run.id}/issues').status_code == 403

    def test_prs_private_anonymous_403(self, db):
        run = self._private_run()
        assert Client().get(f'/api/v1/repositories/runs/{run.id}/prs').status_code == 403

    def test_diff_private_anonymous_403(self, db):
        run = self._private_run()
        assert Client().get(f'/api/v1/repositories/runs/{run.id}/diff').status_code == 403

    def test_similar_private_anonymous_403(self, db):
        run = self._private_run()
        assert Client().get(f'/api/v1/repositories/runs/{run.id}/similar').status_code == 403
