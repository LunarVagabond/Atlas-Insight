"""Extended meta endpoint tests: my_repos, featured, spotlight history, badge edge cases."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings

from apps.repositories.models import AnalysisRun, Repository, RepoOfTheWeek

User = get_user_model()


@pytest.fixture
def repo(db):
    return Repository.objects.create(url='https://github.com/meta/repo', owner='meta', name='repo')


@pytest.fixture
def completed_run(repo):
    return AnalysisRun.objects.create(
        repo=repo, status='completed',
        result={
            'github_meta': {'primary_language': 'Go', 'stars': 50},
            'classification': {
                'project_health': {'key': 'active', 'label': 'Active', 'score': 7}
            },
            'oss_score': {'score': 7.0},
        },
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(username='metauser', password='pass')


@pytest.fixture
def auth_client(user):
    c = Client()
    c.force_login(user)
    return c


# ---------------------------------------------------------------------------
# run_card (203-204: unknown run, 200: rate limit)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunCardEdgeCases:
    def test_unknown_run_returns_404(self):
        resp = Client().get(f'/api/v1/repositories/runs/{uuid.uuid4()}/card.svg')
        assert resp.status_code == 404

    def test_pending_run_returns_404(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        resp = Client().get(f'/api/v1/repositories/runs/{run.id}/card.svg')
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# repo_badge: no run / not analyzed (246-249)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBadgeEdgeCases:
    def test_repo_exists_but_no_completed_run(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        resp = Client().get('/api/v1/repositories/badge/meta/repo.svg')
        assert resp.status_code == 200
        assert b'not analyzed' in resp.content

    def test_repo_exists_completed_run_no_result(self, repo):
        AnalysisRun.objects.create(repo=repo, status='completed', result=None)
        resp = Client().get('/api/v1/repositories/badge/meta/repo.svg')
        assert resp.status_code == 200
        assert b'not analyzed' in resp.content


# ---------------------------------------------------------------------------
# my_repos (265-286)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMyRepos:
    def test_unauthenticated_returns_401(self):
        resp = Client().get('/api/v1/repositories/my-repos')
        assert resp.status_code == 401

    def test_no_github_connected_returns_403(self, auth_client):
        resp = auth_client.get('/api/v1/repositories/my-repos')
        assert resp.status_code == 403

    @patch('requests.get')
    def test_github_connected_returns_repos(self, mock_get, db):
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from django.contrib.sites.models import Site

        user = User.objects.create_user(username='ghconnected', password='pass')
        app = SocialApp.objects.create(
            provider='github', name='GHMyRepos', client_id='a', secret='b'
        )
        app.sites.add(Site.objects.get_current())
        account = SocialAccount.objects.create(user=user, provider='github', uid='789')
        SocialToken.objects.create(account=account, app=app, token='ghp_mytoken')

        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: [
                {'full_name': 'user/repo1', 'html_url': 'https://github.com/user/repo1', 'private': False},
                {'full_name': 'user/repo2', 'html_url': 'https://github.com/user/repo2', 'private': True},
            ]
        )
        c = Client()
        c.force_login(user)
        resp = c.get('/api/v1/repositories/my-repos')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]['full_name'] == 'user/repo1'

    @patch('requests.get')
    def test_github_api_failure_returns_502(self, mock_get, db):
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from django.contrib.sites.models import Site

        user = User.objects.create_user(username='ghfail', password='pass')
        app = SocialApp.objects.create(
            provider='github', name='GHFail', client_id='c', secret='d'
        )
        app.sites.add(Site.objects.get_current())
        account = SocialAccount.objects.create(user=user, provider='github', uid='999')
        SocialToken.objects.create(account=account, app=app, token='ghp_fail')

        mock_get.return_value = MagicMock(ok=False)
        c = Client()
        c.force_login(user)
        resp = c.get('/api/v1/repositories/my-repos')
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# get_featured (295-310)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetFeatured:
    @override_settings(FEATURED_REPO_URL='')
    def test_no_featured_url_returns_null(self):
        resp = Client().get('/api/v1/repositories/featured')
        assert resp.status_code == 200
        assert resp.json() is None

    @override_settings(FEATURED_REPO_URL='https://github.com/feat/missing')
    def test_repo_not_found_returns_null(self, db):
        resp = Client().get('/api/v1/repositories/featured')
        assert resp.status_code == 200
        assert resp.json() is None

    @override_settings(FEATURED_REPO_URL='https://github.com/feat/private')
    def test_private_repo_returns_null(self, db):
        Repository.objects.create(
            url='https://github.com/feat/private', owner='feat', name='private', is_private=True
        )
        resp = Client().get('/api/v1/repositories/featured')
        assert resp.status_code == 200
        assert resp.json() is None

    @override_settings(FEATURED_REPO_URL='https://github.com/feat/norun')
    def test_no_completed_run_returns_null(self, db):
        repo = Repository.objects.create(
            url='https://github.com/feat/norun', owner='feat', name='norun'
        )
        AnalysisRun.objects.create(repo=repo, status='pending')
        resp = Client().get('/api/v1/repositories/featured')
        assert resp.status_code == 200
        assert resp.json() is None

    @override_settings(FEATURED_REPO_URL='https://github.com/feat/hasrun')
    def test_with_completed_run_returns_data(self, db):
        repo = Repository.objects.create(
            url='https://github.com/feat/hasrun', owner='feat', name='hasrun'
        )
        AnalysisRun.objects.create(
            repo=repo, status='completed',
            result={
                'github_meta': {'stars': 100, 'primary_language': 'Rust'},
                'classification': {'project_health': {'key': 'thriving', 'label': 'Thriving'}},
            },
        )
        resp = Client().get('/api/v1/repositories/featured')
        assert resp.status_code == 200
        data = resp.json()
        assert data['repo_owner'] == 'feat'
        assert data['primary_language'] == 'Rust'


# ---------------------------------------------------------------------------
# trending (including skipping entries with no run)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTrending:
    def test_returns_trending_repos(self, completed_run):
        resp = Client().get('/api/v1/repositories/trending')
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_empty_when_no_recent_runs(self, db):
        from datetime import timedelta
        from django.utils import timezone
        repo = Repository.objects.create(
            url='https://github.com/old/repo', owner='old', name='repo'
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={})
        # Move triggered_at to >7 days ago
        AnalysisRun.objects.filter(id=run.id).update(
            triggered_at=timezone.now() - timedelta(days=10)
        )
        resp = Client().get('/api/v1/repositories/trending')
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# spotlight history (384-407)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSpotlightHistory:
    def test_empty_returns_schema(self):
        resp = Client().get('/api/v1/repositories/spotlight/history')
        assert resp.status_code == 200
        data = resp.json()
        assert 'items' in data
        assert data['total'] == 0

    def test_returns_spotlight_entries(self, completed_run):
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        spot = RepoOfTheWeek.objects.create(
            repo=completed_run.repo, week_start=week_start, pick_number=1
        )
        resp = Client().get('/api/v1/repositories/spotlight/history')
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1
        assert data['items'][0]['repo_owner'] == 'meta'

    def test_returns_entry_with_no_run(self, repo):
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + 7)
        RepoOfTheWeek.objects.create(repo=repo, week_start=week_start, pick_number=1)
        resp = Client().get('/api/v1/repositories/spotlight/history')
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1
        assert data['items'][0]['run_id'] is None

    def test_pagination(self, db):
        from datetime import date, timedelta
        for i in range(5):
            r = Repository.objects.create(
                url=f'https://github.com/hist/r{i}', owner='hist', name=f'r{i}'
            )
            week = date.today() - timedelta(days=7 * i)
            week_start = week - timedelta(days=week.weekday())
            RepoOfTheWeek.objects.create(repo=r, week_start=week_start, pick_number=1)

        resp = Client().get('/api/v1/repositories/spotlight/history?page=1&per_page=3')
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 5
        assert len(data['items']) == 3


# ---------------------------------------------------------------------------
# _spotlight_to_schema with run having no result (line 111)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSpotlightCurrentNoResult:
    def test_spotlight_with_run_no_result_returns_null(self, db):
        from datetime import date, timedelta
        repo = Repository.objects.create(
            url='https://github.com/spot/nores', owner='spot', name='nores'
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result=None)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        RepoOfTheWeek.objects.create(repo=repo, week_start=week_start, pick_number=1)
        resp = Client().get('/api/v1/repositories/spotlight/current')
        assert resp.status_code == 200
        assert resp.json() is None


# ---------------------------------------------------------------------------
# remove_favorite: unauthenticated (line 429)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRemoveFavoriteAuth:
    def test_unauthenticated_returns_403(self, repo):
        resp = Client().delete(f'/api/v1/repositories/repos/{repo.id}/favorite')
        assert resp.status_code == 403
