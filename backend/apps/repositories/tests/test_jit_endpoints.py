import pytest
from unittest.mock import patch
from django.test import Client, override_settings
from django.core.cache import cache

from apps.repositories.models import AnalysisRun, Repository


@pytest.fixture
def completed_run(db):
    repo = Repository.objects.create(
        url='https://github.com/testorg/jittest',
        owner='testorg',
        name='jittest',
    )
    run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
    return run


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestIssuesEndpoint:
    def setup_method(self):
        self.client = Client()

    @patch('apps.repositories.router_jit.fetch_contribution_data')
    def test_cache_miss_calls_github(self, mock_fetch, completed_run):
        mock_fetch.return_value = {
            'issues': [{'number': 1, 'title': 'Bug'}],
            'pr_issue_refs': [],
        }
        resp = self.client.get(f'/api/v1/repositories/runs/{completed_run.id}/issues')
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        mock_fetch.assert_called_once()

    @patch('apps.repositories.router_jit.fetch_contribution_data')
    def test_cache_hit_skips_github(self, mock_fetch, completed_run):
        cache.set(f'jit_{completed_run.id}_issues', [{'number': 99, 'title': 'Cached'}], 900)
        resp = self.client.get(f'/api/v1/repositories/runs/{completed_run.id}/issues')
        assert resp.status_code == 200
        assert resp.json()[0]['number'] == 99
        mock_fetch.assert_not_called()

    def test_unknown_run_returns_404(self):
        import uuid
        resp = self.client.get(f'/api/v1/repositories/runs/{uuid.uuid4()}/issues')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestPrsEndpoint:
    def setup_method(self):
        self.client = Client()

    @patch('apps.repositories.router_jit.fetch_contribution_data')
    def test_returns_pr_structure(self, mock_fetch, completed_run):
        mock_fetch.return_value = {'issues': [], 'pr_issue_refs': [{'number': 5}]}
        resp = self.client.get(f'/api/v1/repositories/runs/{completed_run.id}/prs')
        assert resp.status_code == 200
        data = resp.json()
        assert 'pr_issue_refs' in data
        assert 'open_prs' in data

    @patch('apps.repositories.router_jit.fetch_contribution_data')
    def test_cache_hit_skips_github(self, mock_fetch, completed_run):
        cached_result = {'pr_issue_refs': [{'number': 42}], 'open_prs': 1}
        cache.set(f'jit_{completed_run.id}_prs', cached_result, 900)
        resp = self.client.get(f'/api/v1/repositories/runs/{completed_run.id}/prs')
        assert resp.status_code == 200
        mock_fetch.assert_not_called()


@pytest.mark.django_db
class TestDiffEndpoint:
    def setup_method(self):
        self.client = Client()

    def test_no_previous_run_returns_unavailable(self, completed_run):
        resp = self.client.get(f'/api/v1/repositories/runs/{completed_run.id}/diff')
        assert resp.status_code == 200
        assert resp.json()['available'] is False

    def test_pending_run_returns_unavailable(self):
        repo = Repository.objects.create(
            url='https://github.com/testorg/difftest',
            owner='testorg',
            name='difftest',
        )
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{run.id}/diff')
        assert resp.status_code == 200
        assert resp.json()['available'] is False

    def test_with_previous_run_returns_diff(self):
        repo = Repository.objects.create(
            url='https://github.com/testorg/difftest2',
            owner='testorg',
            name='difftest2',
        )
        result_stub = {
            'heuristics': [{'signal': 'burnout', 'score': 30, 'label': 'Burnout', 'description': ''}],
            'dependencies': {},
            'structure': {},
            'oss_score': {'score': 7.0},
            'commits': {'contributor_count': 3},
        }
        prev_run = AnalysisRun.objects.create(repo=repo, status='completed', result=result_stub)
        # Make triggered_at of curr_run later than prev_run by using a different approach
        import datetime
        curr_run = AnalysisRun.objects.create(repo=repo, status='completed', result=result_stub)
        # Ensure ordering: manually set triggered_at if needed
        # curr_run should have a later triggered_at (auto_now_add ensures this since created later)
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{curr_run.id}/diff')
        assert resp.status_code == 200
