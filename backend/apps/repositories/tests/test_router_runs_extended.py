"""Extended runs router tests: list_runs, get_run, delete cleanup, by_slug edge cases."""
import secrets
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from apps.repositories.models import AnalysisRun, Repository, UserFavorite
from apps.users.models import APIToken

User = get_user_model()


@pytest.fixture
def repo(db):
    return Repository.objects.create(url='https://github.com/ext/runs', owner='ext', name='runs')


@pytest.fixture
def user(db):
    return User.objects.create_user(username='runsuser', password='pass')


@pytest.fixture
def user_client(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def superuser(db):
    return User.objects.create_user(username='runssuper', password='pass', is_staff=True, is_superuser=True)


@pytest.fixture
def superuser_client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


@pytest.fixture
def completed_run(repo):
    return AnalysisRun.objects.create(
        repo=repo,
        status='completed',
        result={
            'github_meta': {'primary_language': 'Python', 'stars': 10},
            'classification': {'tags': ['python']},
            'oss_score': {'score': 7.0},
        },
    )


@pytest.mark.django_db
class TestListRuns:
    def test_returns_paginated_results(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'items' in data
        assert 'total' in data
        assert data['total'] >= 1

    def test_search_by_owner(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/?q=ext')
        assert resp.status_code == 200
        assert resp.json()['total'] >= 1

    def test_search_no_match(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/?q=zzznomatch')
        assert resp.status_code == 200
        assert resp.json()['total'] == 0

    def test_sort_by_status(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/?sort=status&order=asc')
        assert resp.status_code == 200

    def test_sort_invalid_field_falls_back(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/?sort=malicious&order=desc')
        assert resp.status_code == 200

    def test_mine_filter_unauthenticated_ignored(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/?mine=true')
        assert resp.status_code == 200

    def test_mine_filter_authenticated(self, user_client, user, repo):
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={}, user=user)
        resp = user_client.get('/api/v1/repositories/runs/?mine=true')
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] >= 1

    def test_pagination_per_page_capped_at_25(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/?per_page=100')
        assert resp.status_code == 200
        assert resp.json()['per_page'] == 25

    def test_favorites_marked_for_authenticated_user(self, user_client, user, repo, completed_run):
        UserFavorite.objects.create(user=user, repo=repo)
        resp = user_client.get('/api/v1/repositories/runs/')
        assert resp.status_code == 200
        items = resp.json()['items']
        fav = next((i for i in items if i['repo_owner'] == 'ext'), None)
        assert fav is not None
        assert fav['is_favorited'] is True

    def test_private_runs_hidden_from_anonymous(self, db):
        private_repo = Repository.objects.create(
            url='https://github.com/priv/hidden', owner='priv', name='hidden', is_private=True
        )
        AnalysisRun.objects.create(repo=private_repo, status='completed', result={})
        resp = Client().get('/api/v1/repositories/runs/')
        assert resp.status_code == 200
        owners = [i['repo_owner'] for i in resp.json()['items']]
        assert 'priv' not in owners

    def test_tags_and_primary_language_in_response(self, completed_run):
        resp = Client().get('/api/v1/repositories/runs/')
        assert resp.status_code == 200
        item = resp.json()['items'][0]
        assert item['tags'] == ['python']
        assert item['primary_language'] == 'Python'


@pytest.mark.django_db
class TestGetRun:
    def test_completed_run_increments_view_count(self, completed_run):
        initial = completed_run.repo.view_count
        Client().get(f'/api/v1/repositories/runs/{completed_run.id}')
        completed_run.repo.refresh_from_db()
        assert completed_run.repo.view_count == initial + 1

    def test_pending_run_no_view_count_increment(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        initial = repo.view_count
        Client().get(f'/api/v1/repositories/runs/{run.id}')
        repo.refresh_from_db()
        assert repo.view_count == initial

    def test_private_run_anonymous_returns_403(self, db):
        repo = Repository.objects.create(
            url='https://github.com/priv/secret', owner='priv', name='secret', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}')
        assert resp.status_code == 403

    def test_private_run_owner_can_access(self, user_client, user, db):
        repo = Repository.objects.create(
            url='https://github.com/priv/mine', owner='priv', name='mine', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={}, user=user)
        resp = user_client.get(f'/api/v1/repositories/runs/{run.id}')
        assert resp.status_code == 200

    def test_unknown_run_returns_404(self):
        resp = Client().get(f'/api/v1/repositories/runs/{uuid.uuid4()}')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestDeleteRunExtended:
    def test_delete_also_removes_repo_when_last_run(self, user_client, user):
        repo = Repository.objects.create(
            url='https://github.com/priv/solo', owner='priv', name='solo', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', user=user)
        repo_id = repo.id
        resp = user_client.delete(f'/api/v1/repositories/runs/{run.id}')
        assert resp.status_code == 204
        assert not Repository.objects.filter(id=repo_id).exists()

    def test_delete_keeps_repo_when_other_runs_exist(self, user_client, user):
        repo = Repository.objects.create(
            url='https://github.com/priv/multi', owner='priv', name='multi', is_private=True
        )
        run1 = AnalysisRun.objects.create(repo=repo, status='completed', user=user)
        AnalysisRun.objects.create(repo=repo, status='completed', user=user)
        repo_id = repo.id
        resp = user_client.delete(f'/api/v1/repositories/runs/{run1.id}')
        assert resp.status_code == 204
        assert Repository.objects.filter(id=repo_id).exists()

    def test_wrong_user_cannot_delete(self, db):
        owner = User.objects.create_user(username='owner_del', password='pass')
        other = User.objects.create_user(username='other_del', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/theirs', owner='priv', name='theirs', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', user=owner)
        c = Client()
        c.force_login(other)
        resp = c.delete(f'/api/v1/repositories/runs/{run.id}')
        assert resp.status_code == 403

    def test_unknown_run_returns_404(self, user_client):
        resp = user_client.delete(f'/api/v1/repositories/runs/{uuid.uuid4()}')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestGetTimeline:
    def test_completed_run_returns_timeline(self, completed_run):
        completed_run.result = {
            'commits': {
                'weekly_frequency': [1, 2, 3],
                'monthly_frequency': [10, 20],
                'contributor_churn': [0.1],
            },
            'dependencies': {'dependency_count': 5},
        }
        completed_run.save(update_fields=['commits_data', 'deps_data', 'dependency_count'])
        resp = Client().get(f'/api/v1/repositories/runs/{completed_run.id}/timeline')
        assert resp.status_code == 200
        data = resp.json()
        assert data['commit_frequency'] == [1, 2, 3]
        assert data['dependency_count'] == 5

    def test_pending_run_returns_404(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/timeline')
        assert resp.status_code == 404

    def test_unknown_run_returns_404(self):
        resp = Client().get(f'/api/v1/repositories/runs/{uuid.uuid4()}/timeline')
        assert resp.status_code == 404

    def test_private_run_anonymous_returns_403(self, db):
        repo = Repository.objects.create(
            url='https://github.com/priv/tl', owner='priv', name='tl', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/timeline')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestBySlugExtended:
    def test_private_repo_anonymous_returns_403(self, db):
        repo = Repository.objects.create(
            url='https://github.com/priv/slugtest', owner='priv', name='slugtest', is_private=True
        )
        AnalysisRun.objects.create(repo=repo, status='completed', result={})
        resp = Client().get('/api/v1/repositories/by-slug/priv/slugtest')
        assert resp.status_code == 403

    def test_no_runs_returns_404(self, repo):
        resp = Client().get('/api/v1/repositories/by-slug/ext/runs')
        assert resp.status_code == 404

    def test_private_run_wrong_user_returns_403(self, db):
        owner = User.objects.create_user(username='slug_owner', password='pass')
        other = User.objects.create_user(username='slug_other', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/slugpriv', owner='priv', name='slugpriv', is_private=True
        )
        AnalysisRun.objects.create(repo=repo, status='completed', result={}, user=owner)
        c = Client()
        c.force_login(other)
        resp = c.get('/api/v1/repositories/by-slug/priv/slugpriv')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestResolveApiTokenUser:
    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha')
    def test_api_token_auth_in_analyze(self, mock_sha, mock_task, db):
        mock_sha.return_value = 'abc123'
        mock_task.delay.return_value = MagicMock(id='task-1')
        user = User.objects.create_user(username='apiuser', password='pass')
        raw = secrets.token_urlsafe(32)
        APIToken.objects.create(
            user=user,
            name='test',
            token_hash=APIToken.hash_token(raw),
        )
        resp = Client().post(
            '/api/v1/repositories/analyze',
            data='{"url": "https://github.com/org/proj"}',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {raw}',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'pending'
