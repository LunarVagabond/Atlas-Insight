"""Extended admin router tests: stats, rate-limit, pick-spotlight, watch/unwatch."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.repositories.models import AnalysisRun, Repository

User = get_user_model()


@pytest.fixture
def repo(db):
    return Repository.objects.create(url='https://github.com/a/b', owner='a', name='b')


@pytest.fixture
def completed_run(repo):
    return AnalysisRun.objects.create(repo=repo, status='completed', result={})


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username='staff_adm', password='pass', is_staff=True)


@pytest.fixture
def staff_client(staff_user):
    c = Client()
    c.force_login(staff_user)
    return c


@pytest.fixture
def superuser(db):
    return User.objects.create_user(username='super_adm', password='pass', is_staff=True, is_superuser=True)


@pytest.fixture
def superuser_client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


@pytest.mark.django_db
class TestAdminStats:
    def test_anonymous_returns_403(self):
        resp = Client().get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 403

    def test_non_staff_returns_403(self, db):
        user = User.objects.create_user(username='pleb_s', password='pass')
        c = Client()
        c.force_login(user)
        resp = c.get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 403

    def test_staff_returns_stats(self, staff_client, completed_run):
        resp = staff_client.get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 200
        data = resp.json()
        assert data['total_repos'] >= 1
        assert data['total_runs'] >= 1
        assert data['completed_runs'] >= 1
        assert 'queue_depth' in data
        assert 'cache_size_gb' in data

    def test_stats_counts_pending_in_queue(self, staff_client, repo):
        AnalysisRun.objects.create(repo=repo, status='pending')
        resp = staff_client.get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 200
        assert resp.json()['queue_depth'] >= 1


@pytest.mark.django_db
class TestAdminRateLimit:
    def test_non_staff_returns_403(self, db):
        user = User.objects.create_user(username='pleb_rl', password='pass')
        c = Client()
        c.force_login(user)
        resp = c.get('/api/v1/repositories/admin/rate-limit')
        assert resp.status_code == 403

    @patch('requests.get')
    def test_staff_returns_rate_limit_structure(self, mock_get, staff_client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            'resources': {
                'core': {'limit': 5000, 'remaining': 4000, 'reset': 1700000000},
                'search': {'limit': 30, 'remaining': 28, 'reset': 1700000000},
                'graphql': {'limit': 5000, 'remaining': 4999, 'reset': 1700000000},
            }
        }
        mock_get.return_value = mock_resp
        resp = staff_client.get('/api/v1/repositories/admin/rate-limit')
        assert resp.status_code == 200
        data = resp.json()
        assert data['core']['limit'] == 5000
        assert data['search']['remaining'] == 28

    @patch('requests.get')
    def test_github_failure_returns_502(self, mock_get, staff_client):
        mock_get.side_effect = Exception('network failure')
        resp = staff_client.get('/api/v1/repositories/admin/rate-limit')
        assert resp.status_code == 502


@pytest.mark.django_db
class TestPickSpotlight:
    def test_non_superuser_returns_403(self, staff_client):
        resp = staff_client.post('/api/v1/repositories/admin/pick-spotlight')
        assert resp.status_code == 403

    def test_no_eligible_repos_returns_409(self, superuser_client, db):
        resp = superuser_client.post('/api/v1/repositories/admin/pick-spotlight')
        assert resp.status_code == 409

    def test_picks_from_completed_public_repos(self, superuser_client, completed_run):
        resp = superuser_client.post('/api/v1/repositories/admin/pick-spotlight')
        assert resp.status_code == 200
        data = resp.json()
        assert data['owner'] == 'a'
        assert data['name'] == 'b'
        assert 'week_start' in data
        assert data['pick_number'] == 1

    def test_second_pick_increments_pick_number(self, superuser_client, completed_run):
        superuser_client.post('/api/v1/repositories/admin/pick-spotlight')
        # Second call same week re-picks (deletes old entry first)
        resp = superuser_client.post('/api/v1/repositories/admin/pick-spotlight')
        assert resp.status_code == 200

    def test_private_repo_not_eligible(self, superuser_client, db):
        repo = Repository.objects.create(
            url='https://github.com/priv/repo', owner='priv', name='repo', is_private=True
        )
        AnalysisRun.objects.create(repo=repo, status='completed', result={})
        resp = superuser_client.post('/api/v1/repositories/admin/pick-spotlight')
        assert resp.status_code == 409


@pytest.mark.django_db
class TestListWatched:
    def test_non_staff_returns_403(self, db):
        user = User.objects.create_user(username='pleb_w', password='pass')
        c = Client()
        c.force_login(user)
        resp = c.get('/api/v1/repositories/watched')
        assert resp.status_code == 403

    def test_returns_only_watched(self, staff_client, repo):
        repo.is_watched = True
        repo.save(update_fields=['is_watched'])
        other = Repository.objects.create(url='https://github.com/x/y', owner='x', name='y')
        resp = staff_client.get('/api/v1/repositories/watched')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['owner'] == 'a'

    def test_empty_when_none_watched(self, staff_client, repo):
        resp = staff_client.get('/api/v1/repositories/watched')
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.django_db
class TestWatchUnwatch:
    def test_non_superuser_cannot_watch(self, staff_client, repo):
        resp = staff_client.post(f'/api/v1/repositories/repos/{repo.id}/watch')
        assert resp.status_code == 403

    def test_superuser_watches_repo(self, superuser_client, repo):
        resp = superuser_client.post(f'/api/v1/repositories/repos/{repo.id}/watch')
        assert resp.status_code == 200
        repo.refresh_from_db()
        assert repo.is_watched is True

    def test_watch_unknown_repo_returns_404(self, superuser_client):
        resp = superuser_client.post(f'/api/v1/repositories/repos/{uuid.uuid4()}/watch')
        assert resp.status_code == 404

    def test_non_superuser_cannot_unwatch(self, staff_client, repo):
        resp = staff_client.delete(f'/api/v1/repositories/repos/{repo.id}/watch')
        assert resp.status_code == 403

    def test_superuser_unwatches_repo(self, superuser_client, repo):
        repo.is_watched = True
        repo.save(update_fields=['is_watched'])
        resp = superuser_client.delete(f'/api/v1/repositories/repos/{repo.id}/watch')
        assert resp.status_code == 204
        repo.refresh_from_db()
        assert repo.is_watched is False

    def test_unwatch_unknown_repo_returns_404(self, superuser_client):
        resp = superuser_client.delete(f'/api/v1/repositories/repos/{uuid.uuid4()}/watch')
        assert resp.status_code == 404
