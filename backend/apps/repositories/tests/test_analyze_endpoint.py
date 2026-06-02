import pytest
from unittest.mock import MagicMock, patch
from django.test import Client

from apps.repositories.models import AnalysisRun, Repository


@pytest.mark.django_db
class TestAnalyzeEndpoint:
    def setup_method(self):
        self.client = Client()

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha', return_value='abc123')
    def test_new_repo_returns_pending(self, mock_sha, mock_task_class):
        mock_task_class.delay.return_value = MagicMock(id='task-id-123')
        resp = self.client.post(
            '/api/v1/repositories/analyze',
            data='{"url": "https://github.com/django/django"}',
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'run_id' in data
        assert data['status'] == 'pending'
        assert data['cached'] is False
        mock_task_class.delay.assert_called_once()

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha', return_value='abc123')
    def test_cached_run_returns_cached_true(self, mock_sha, mock_task_class):
        repo = Repository.objects.create(
            url='https://github.com/django/django',
            owner='django',
            name='django',
            last_commit_sha='abc123',
        )
        AnalysisRun.objects.create(repo=repo, status='completed')
        resp = self.client.post(
            '/api/v1/repositories/analyze',
            data='{"url": "https://github.com/django/django"}',
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['cached'] is True
        assert data['status'] == 'completed'
        mock_task_class.delay.assert_not_called()

    def test_non_github_url_returns_422(self):
        resp = self.client.post(
            '/api/v1/repositories/analyze',
            data='{"url": "https://gitlab.com/some/repo"}',
            content_type='application/json',
        )
        assert resp.status_code == 422

    def test_missing_url_returns_422(self):
        resp = self.client.post(
            '/api/v1/repositories/analyze',
            data='{}',
            content_type='application/json',
        )
        assert resp.status_code == 422

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha', return_value=None)
    def test_no_sha_queues_new_run(self, mock_sha, mock_task_class):
        mock_task_class.delay.return_value = MagicMock(id='task-xyz')
        resp = self.client.post(
            '/api/v1/repositories/analyze',
            data='{"url": "https://github.com/new/repo"}',
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['cached'] is False
