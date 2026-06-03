"""Cover remaining jit endpoint gaps: 404s, similar candidates, diff with classification,
ai_summary with sub_projects/many_deps, vuln edge cases, jit_token with auth_token."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.test import Client

from apps.repositories.models import AnalysisRun, Repository


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def repo(db):
    return Repository.objects.create(url='https://github.com/mis/repo', owner='mis', name='repo')


@pytest.fixture
def completed_run(repo):
    return AnalysisRun.objects.create(repo=repo, status='completed', result={
        'github_meta': {'primary_language': 'Python', 'stars': 5},
        'oss_score': {'score': 7.0},
        'classification': {'project_health': {'key': 'active', 'label': 'Active', 'score': 7}},
    })


@pytest.mark.django_db
class TestPrs404:
    def test_unknown_run_returns_404(self):
        resp = Client().get(f'/api/v1/repositories/runs/{uuid.uuid4()}/prs')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestDiff404AndEdgeCases:
    def test_unknown_run_returns_404(self):
        resp = Client().get(f'/api/v1/repositories/runs/{uuid.uuid4()}/diff')
        assert resp.status_code == 404

    def test_prev_run_with_no_result_returns_unavailable(self, repo):
        prev = AnalysisRun.objects.create(repo=repo, status='completed', result=None)
        curr = AnalysisRun.objects.create(repo=repo, status='completed', result={'heuristics': []})
        resp = Client().get(f'/api/v1/repositories/runs/{curr.id}/diff')
        assert resp.status_code == 200
        assert resp.json()['available'] is False

    def test_diff_with_classification_data(self, repo):
        """Hit cls_delta return branch (line 65) by having classification in both runs."""
        result_base = {
            'heuristics': [{'signal': 'docs', 'score': 40, 'label': 'Docs', 'description': ''}],
            'dependencies': {'dependencies': []},
            'structure': {'total_files': 10, 'test_ratio': 0.1},
            'graph': {'node_count': 5, 'god_modules': []},
            'commits': {'total_contributors': 2},
            'classification': {
                'project_health': {'key': 'active', 'label': 'Active', 'score': 7},
                'contribution_difficulty': {'key': 'easy', 'label': 'Easy', 'score': 3},
                'documentation_grade': {'key': 'good', 'label': 'Good', 'score': 6},
                'code_complexity': {'key': 'medium', 'label': 'Medium', 'score': 5},
            },
        }
        result_curr = {
            'heuristics': [{'signal': 'docs', 'score': 60, 'label': 'Docs', 'description': ''}],
            'dependencies': {'dependencies': []},
            'structure': {'total_files': 15, 'test_ratio': 0.2},
            'graph': {'node_count': 8, 'god_modules': []},
            'commits': {'total_contributors': 3},
            'classification': {
                'project_health': {'key': 'thriving', 'label': 'Thriving', 'score': 9},
                'contribution_difficulty': {'key': 'moderate', 'label': 'Moderate', 'score': 5},
                'documentation_grade': {'key': 'great', 'label': 'Great', 'score': 8},
                'code_complexity': {'key': 'complex', 'label': 'Complex', 'score': 8},
            },
        }
        prev = AnalysisRun.objects.create(repo=repo, status='completed', result=result_base)
        curr = AnalysisRun.objects.create(repo=repo, status='completed', result=result_curr)
        resp = Client().get(f'/api/v1/repositories/runs/{curr.id}/diff')
        assert resp.status_code == 200
        data = resp.json()
        assert data['available'] is True
        cls = data['classification']
        assert cls['project_health'] is not None
        assert cls['project_health']['before_label'] == 'Active'
        assert cls['project_health']['after_label'] == 'Thriving'


@pytest.mark.django_db
class TestSimilar404AndCandidates:
    def test_unknown_run_returns_404(self):
        resp = Client().get(f'/api/v1/repositories/runs/{uuid.uuid4()}/similar')
        assert resp.status_code == 404

    def test_returns_matching_candidates(self, completed_run, repo):
        other_repo = Repository.objects.create(
            url='https://github.com/other/repo', owner='other', name='repo'
        )
        other_run = AnalysisRun.objects.create(
            repo=other_repo, status='completed', result={
                'github_meta': {'primary_language': 'Python', 'stars': 20},
                'oss_score': {'score': 7.5},
                'classification': {'project_health': {'key': 'active', 'label': 'Active'}},
            }
        )
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/similar')
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(r['owner'] == 'other' for r in data)

    def test_skips_candidate_with_no_result(self, completed_run):
        other_repo = Repository.objects.create(
            url='https://github.com/nores/repo', owner='nores', name='repo'
        )
        AnalysisRun.objects.create(repo=other_repo, status='completed', result=None)
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/similar')
        assert resp.status_code == 200
        owners = [r['owner'] for r in resp.json()]
        assert 'nores' not in owners

    def test_caps_results_at_5(self, completed_run, db):
        for i in range(6):
            r = Repository.objects.create(
                url=f'https://github.com/bulk{i}/repo', owner=f'bulk{i}', name='repo'
            )
            AnalysisRun.objects.create(
                repo=r, status='completed', result={
                    'github_meta': {'primary_language': 'Python', 'stars': 10},
                    'oss_score': {'score': 7.2},
                    'classification': {'project_health': {'key': 'active', 'label': 'Active'}},
                }
            )
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/similar')
        assert resp.status_code == 200
        assert len(resp.json()) <= 5

    def test_skips_candidate_with_score_too_different(self, completed_run):
        other_repo = Repository.objects.create(
            url='https://github.com/farscr/repo', owner='farscr', name='repo'
        )
        AnalysisRun.objects.create(
            repo=other_repo, status='completed', result={
                'github_meta': {'primary_language': 'Python', 'stars': 5},
                'oss_score': {'score': 1.0},
            }
        )
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/similar')
        assert resp.status_code == 200
        owners = [r['owner'] for r in resp.json()]
        assert 'farscr' not in owners


@pytest.mark.django_db
class TestFileHistory404:
    def test_unknown_run_returns_404(self):
        resp = Client().get(
            f'/api/v1/repositories/runs/{uuid.uuid4()}/file-history',
            {'path': 'README.md'}
        )
        assert resp.status_code == 404

    @patch('requests.get')
    def test_non_dict_commit_skipped(self, mock_get, completed_run):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = [
            'not_a_dict',
            {
                'sha': 'abc1234567890',
                'commit': {'message': 'fix', 'author': {'name': 'alice', 'date': '2024-01-01'}},
                'html_url': 'https://github.com/mis/repo/commit/abc123',
            },
        ]
        mock_get.return_value = mock_resp
        resp = Client().get(
            f'/api/v1/repositories/runs/{completed_run.id}/file-history',
            {'path': 'src/app.py'}
        )
        assert resp.status_code == 200
        assert len(resp.json()['commits']) == 1


@pytest.mark.django_db
class TestVulnEdgeCases:
    def test_private_run_anonymous_returns_403(self, db):
        repo = Repository.objects.create(
            url='https://github.com/prv/vuln', owner='prv', name='vuln', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/vulnerabilities')
        assert resp.status_code == 403

    def test_not_completed_run_returns_empty(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/vulnerabilities')
        assert resp.status_code == 200
        data = resp.json()
        assert data['checked'] == 0
        assert data['vulnerable'] == []

    @patch('apps.analysis.vuln_scan._enrich_vulns')
    @patch('requests.post')
    def test_vuln_with_empty_id_skipped(self, mock_post, mock_enrich, repo):
        result = {
            'dependencies': {
                'dependencies': [
                    {'name': 'lodash', 'version': '4.17.15', 'ecosystem': 'npm'},
                ]
            }
        }
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=result)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            'results': [{'vulns': [{'id': ''}]}]
        }
        mock_post.return_value = mock_resp
        mock_enrich.return_value = {}

        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/vulnerabilities')
        assert resp.status_code == 200
        assert resp.json()['vulnerable'] == []


@pytest.mark.django_db
class TestJitTokenWithAuthToken:
    """Cover _jit_token returning repo.auth_token (line 29 = auth header set)."""

    @patch('apps.repositories.router_jit.fetch_contribution_data')
    def test_auth_token_used_in_request(self, mock_fetch, db):
        repo = Repository.objects.create(
            url='https://github.com/tok/repo', owner='tok', name='repo',
            auth_token='ghp_secret_token',
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
        mock_fetch.return_value = {'issues': [], 'pr_issue_refs': []}
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/issues')
        assert resp.status_code == 200
        call_args = mock_fetch.call_args
        headers = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get('headers', {})
        assert 'Authorization' in headers
        assert 'ghp_secret_token' in headers['Authorization']


@pytest.mark.django_db
class TestAiSummaryEdgeCases:
    def test_summary_with_sub_projects(self, db):
        repo = Repository.objects.create(
            url='https://github.com/mono/repo', owner='mono', name='repo'
        )
        result = {
            'github_meta': {'primary_language': 'Python', 'description': 'A monorepo'},
            'structure': {'languages': [{'name': 'Python', 'pct': 60}, {'name': 'JS', 'pct': 40}]},
            'repo_type': {
                'type': 'monorepo',
                'sub_projects': [
                    {'name': 'api', 'languages': ['Python'], 'tech_stack': ['Django']},
                    {'name': 'web', 'languages': ['TypeScript'], 'tech_stack': []},
                ],
            },
            'commits': {},
            'dependencies': {},
            'graph': {},
            'security': {},
            'oss_score': {},
            'classification': {},
            'arch_tours': [],
            'contribution_opportunities': [],
        }
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=result)
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/ai-summary')
        assert resp.status_code == 200
        summary = resp.json()['summary']
        assert 'monorepo' in summary
        assert 'api/' in summary
        assert 'Django' in summary

    def test_summary_with_many_deps_shows_remaining_count(self, db):
        repo = Repository.objects.create(
            url='https://github.com/bigdep/repo', owner='bigdep', name='repo'
        )
        deps = [
            {'name': f'dep{i}', 'version': '1.0.0', 'ecosystem': 'pip', 'dev': False}
            for i in range(15)
        ]
        result = {
            'github_meta': {'primary_language': 'Python', 'description': ''},
            'structure': {'languages': [{'name': 'Python', 'pct': 100}]},
            'dependencies': {'dependencies': deps, 'dependency_count': 15},
            'commits': {},
            'graph': {},
            'security': {},
            'oss_score': {},
            'classification': {},
            'repo_type': {},
            'arch_tours': [],
            'contribution_opportunities': [],
        }
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=result)
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/ai-summary')
        assert resp.status_code == 200
        assert 'more production deps' in resp.json()['summary']

    def test_summary_private_wrong_user_returns_403(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        owner = User.objects.create_user(username='ai_owner2', password='pass')
        other = User.objects.create_user(username='ai_other2', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/pv/ai2', owner='pv', name='ai2', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={}, user=owner)
        c = Client()
        c.force_login(other)
        resp = c.get(f'/api/v1/repositories/runs/{run.id}/ai-summary')
        assert resp.status_code == 403
