"""
Endpoint coverage tests for the remaining router surface:
retry_run, delete_run, by_slug, badge.svg, card.svg, vulnerabilities, similar,
file-history, trending, spotlight/current, webhook/github, admin/stats,
add_favorite / remove_favorite.
"""
import hashlib
import hmac
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.core.cache import cache
from django.utils import timezone

from apps.repositories.models import AnalysisRun, Repository, RepoOfTheWeek, UserFavorite

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache_fixture():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def repo(db):
    return Repository.objects.create(
        url='https://github.com/test/repo',
        owner='test',
        name='repo',
    )


@pytest.fixture
def completed_run(repo):
    result = {
        'commits': {'total_commits': 10, 'total_contributors': 2, 'weekly_frequency': [], 'monthly_frequency': [], 'contributor_churn': []},
        'heuristics': [{'signal': 'burnout', 'score': 40, 'label': 'Burnout', 'description': ''}],
        'dependencies': {'dependencies': [], 'dependency_count': 0},
        'structure': {'total_files': 50, 'test_ratio': 0.1},
        'graph': {'node_count': 10, 'god_modules': []},
        'github_meta': {'primary_language': 'Python', 'stars': 100},
        'oss_score': {'score': 7.5, 'badge': 'thriving', 'label': 'Thriving'},
        'classification': {
            'project_health': {'key': 'thriving', 'label': 'Thriving', 'score': 8},
            'contribution_difficulty': {'key': 'moderate', 'label': 'Moderate', 'score': 5},
            'code_complexity': {'key': 'medium', 'label': 'Medium', 'score': 5},
            'documentation_grade': {'key': 'good', 'label': 'Good', 'score': 6},
            'tags': ['python', 'web'],
        },
    }
    return AnalysisRun.objects.create(repo=repo, status='completed', result=result)


@pytest.fixture
def staff_client(db):
    user = User.objects.create_user(username='staff', password='pass', is_staff=True)
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def superuser_client(db):
    user = User.objects.create_user(username='super', password='pass', is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username='normaluser', password='pass')
    client = Client()
    client.force_login(user)
    return client, user


# ---------------------------------------------------------------------------
# retry_run
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRetryRun:
    @patch('apps.repositories.router_runs.analyze_repository')
    def test_public_run_retries(self, mock_task, completed_run):
        mock_task.delay.return_value = MagicMock(id='new-task')
        client = Client()
        resp = client.post(f'/api/v1/repositories/runs/{completed_run.id}/retry')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'pending'
        assert data['cached'] is False

    def test_unknown_run_returns_404(self):
        client = Client()
        resp = client.post(f'/api/v1/repositories/runs/{uuid.uuid4()}/retry')
        assert resp.status_code == 404

    @patch('apps.repositories.router_runs.analyze_repository')
    def test_cooldown_blocks_retry(self, mock_task, completed_run):
        completed_run.completed_at = timezone.now()
        completed_run.save(update_fields=['completed_at'])
        client = Client()
        resp = client.post(f'/api/v1/repositories/runs/{completed_run.id}/retry')
        assert resp.status_code == 429

    @patch('apps.repositories.router_runs.analyze_repository')
    def test_superuser_bypasses_cooldown(self, mock_task, completed_run, superuser_client):
        mock_task.delay.return_value = MagicMock(id='bypass-task')
        completed_run.repo.last_analyzed_at = timezone.now()
        completed_run.repo.save(update_fields=['last_analyzed_at'])
        resp = superuser_client.post(f'/api/v1/repositories/runs/{completed_run.id}/retry')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# delete_run
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeleteRun:
    def test_anonymous_returns_403(self, completed_run):
        client = Client()
        resp = client.delete(f'/api/v1/repositories/runs/{completed_run.id}')
        assert resp.status_code == 403

    def test_public_repo_cannot_be_deleted(self, completed_run, auth_client):
        client, _ = auth_client
        resp = client.delete(f'/api/v1/repositories/runs/{completed_run.id}')
        assert resp.status_code == 403

    def test_private_run_owner_can_delete(self, db, auth_client):
        client, user = auth_client
        repo = Repository.objects.create(
            url='https://github.com/private/repo',
            owner='private',
            name='repo',
            is_private=True,
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', user=user)
        resp = client.delete(f'/api/v1/repositories/runs/{run.id}')
        assert resp.status_code == 204
        assert not AnalysisRun.objects.filter(id=run.id).exists()


# ---------------------------------------------------------------------------
# by_slug
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBySlug:
    def test_returns_run_for_known_repo(self, completed_run):
        client = Client()
        resp = client.get('/api/v1/repositories/by-slug/test/repo')
        assert resp.status_code == 200
        data = resp.json()
        assert 'run_id' in data
        assert data['status'] == 'completed'

    def test_case_insensitive_match(self, completed_run):
        client = Client()
        resp = client.get('/api/v1/repositories/by-slug/TEST/REPO')
        assert resp.status_code == 200

    def test_unknown_repo_returns_404(self):
        client = Client()
        resp = client.get('/api/v1/repositories/by-slug/nobody/norepo')
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# badge.svg
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBadgeSvg:
    def test_known_repo_returns_svg(self, completed_run):
        client = Client()
        resp = client.get('/api/v1/repositories/badge/test/repo.svg')
        assert resp.status_code == 200
        assert b'<svg' in resp.content
        assert b'Thriving' in resp.content

    def test_unknown_repo_returns_404_with_svg(self):
        client = Client()
        resp = client.get('/api/v1/repositories/badge/nobody/norepo.svg')
        assert resp.status_code == 404
        assert b'<svg' in resp.content


# ---------------------------------------------------------------------------
# card.svg
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCardSvg:
    def test_completed_run_returns_svg(self, completed_run):
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{completed_run.id}/card.svg')
        assert resp.status_code == 200
        assert b'<svg' in resp.content

    def test_pending_run_returns_404(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{run.id}/card.svg')
        assert resp.status_code == 404

    def test_light_theme_accepted(self, completed_run):
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{completed_run.id}/card.svg?theme=light')
        assert resp.status_code == 200
        assert b'#ffffff' in resp.content


# ---------------------------------------------------------------------------
# vulnerabilities
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVulnerabilities:
    def test_no_deps_returns_empty(self, completed_run):
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{completed_run.id}/vulnerabilities')
        assert resp.status_code == 200
        data = resp.json()
        assert data['checked'] == 0
        assert data['vulnerable'] == []

    def test_unknown_run_returns_404(self):
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{uuid.uuid4()}/vulnerabilities')
        assert resp.status_code == 404

    def test_cache_is_used(self, completed_run):
        cached = {'checked': 5, 'vulnerable': []}
        cache.set(f'jit_{completed_run.id}_vulns', cached, 900)
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{completed_run.id}/vulnerabilities')
        assert resp.status_code == 200
        assert resp.json()['checked'] == 5


# ---------------------------------------------------------------------------
# similar
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSimilar:
    def test_returns_list(self, completed_run):
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{completed_run.id}/similar')
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_pending_run_returns_empty(self, repo):
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{run.id}/similar')
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# file-history
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFileHistory:
    def test_missing_path_returns_422(self, completed_run):
        client = Client()
        resp = client.get(f'/api/v1/repositories/runs/{completed_run.id}/file-history')
        assert resp.status_code == 422

    def test_cache_hit_returns_cached_data(self, completed_run):
        path = 'src/main.py'
        path_hash = hashlib.md5(path.encode()).hexdigest()[:8]
        branch_slug = completed_run.branch.replace('/', '_')[:20] if completed_run.branch else 'default'
        cached = {'path': path, 'commits': [{'sha': 'abc1234', 'message': 'fix', 'date': '', 'author': '', 'url': '', 'issue_refs': [], 'full_sha': 'abc1234abc1234'}]}
        cache.set(f'jit_{completed_run.id}_fh_{branch_slug}_{path_hash}', cached, 900)
        client = Client()
        resp = client.get(
            f'/api/v1/repositories/runs/{completed_run.id}/file-history',
            {'path': path},
        )
        assert resp.status_code == 200
        assert resp.json()['path'] == path
        assert len(resp.json()['commits']) == 1


# ---------------------------------------------------------------------------
# trending
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTrending:
    def test_empty_trending(self):
        client = Client()
        resp = client.get('/api/v1/repositories/trending')
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_completed_runs_show_in_trending(self, completed_run):
        client = Client()
        resp = client.get('/api/v1/repositories/trending')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        run_ids = [r['run_id'] for r in data]
        assert str(completed_run.id) in run_ids


# ---------------------------------------------------------------------------
# spotlight/current
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSpotlightCurrent:
    def test_no_spotlight_returns_null(self):
        client = Client()
        resp = client.get('/api/v1/repositories/spotlight/current')
        assert resp.status_code == 200
        assert resp.json() is None

    def test_with_spotlight_returns_data(self, completed_run):
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        RepoOfTheWeek.objects.create(
            repo=completed_run.repo,
            week_start=week_start,
            pick_number=1,
        )
        client = Client()
        resp = client.get('/api/v1/repositories/spotlight/current')
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert data['repo_owner'] == 'test'


# ---------------------------------------------------------------------------
# webhook/github
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGithubWebhook:
    BASE_URL = '/api/v1/repositories/webhooks/github'

    @override_settings(GITHUB_WEBHOOK_SECRET='', DEBUG=True)
    @patch('apps.repositories.router_admin.analyze_repository')
    def test_push_event_triggers_reanalysis(self, mock_task, repo):
        mock_task.delay.return_value = MagicMock(id='webhook-task')
        payload = {
            'repository': {'html_url': 'https://github.com/test/repo'},
        }
        client = Client()
        resp = client.post(
            self.BASE_URL,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
            HTTP_X_GITHUB_DELIVERY='delivery-001',
        )
        assert resp.status_code == 200
        mock_task.delay.assert_called_once()

    @override_settings(GITHUB_WEBHOOK_SECRET='', DEBUG=True)
    def test_non_push_event_skips_reanalysis(self, repo):
        payload = {'repository': {'html_url': 'https://github.com/test/repo'}}
        client = Client()
        resp = client.post(
            self.BASE_URL,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='star',
            HTTP_X_GITHUB_DELIVERY='delivery-002',
        )
        assert resp.status_code == 200
        assert not AnalysisRun.objects.filter(repo=repo).exists()

    @override_settings(GITHUB_WEBHOOK_SECRET='testsecret', DEBUG=False)
    def test_bad_signature_returns_400(self):
        payload = json.dumps({'repository': {'html_url': 'https://github.com/test/repo'}})
        client = Client()
        resp = client.post(
            self.BASE_URL,
            data=payload,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=badhash',
            HTTP_X_GITHUB_EVENT='push',
        )
        assert resp.status_code == 400

    @override_settings(GITHUB_WEBHOOK_SECRET='testsecret', DEBUG=False)
    @patch('apps.repositories.router_admin.analyze_repository')
    def test_valid_signature_accepted(self, mock_task, repo):
        mock_task.delay.return_value = MagicMock(id='sig-task')
        payload = json.dumps({'repository': {'html_url': 'https://github.com/test/repo'}})
        sig = 'sha256=' + hmac.new(b'testsecret', payload.encode(), hashlib.sha256).hexdigest()
        client = Client()
        resp = client.post(
            self.BASE_URL,
            data=payload,
            content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig,
            HTTP_X_GITHUB_EVENT='push',
            HTTP_X_GITHUB_DELIVERY='delivery-003',
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# admin/stats
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminStats:
    def test_non_staff_returns_403(self, completed_run, auth_client):
        client, _ = auth_client
        resp = client.get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 403

    def test_anonymous_returns_403(self):
        resp = Client().get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 403

    @override_settings(REPO_CACHE_DIR='/tmp')
    def test_staff_returns_stats(self, completed_run, staff_client):
        resp = staff_client.get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 200
        data = resp.json()
        assert 'total_repos' in data
        assert 'total_runs' in data
        assert data['total_repos'] >= 1
        assert data['completed_runs'] >= 1


# ---------------------------------------------------------------------------
# add_favorite / remove_favorite
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFavorites:
    def test_anonymous_cannot_favorite(self, repo):
        resp = Client().post(f'/api/v1/repositories/repos/{repo.id}/favorite')
        assert resp.status_code == 403

    def test_add_favorite_creates_record(self, repo, auth_client):
        client, user = auth_client
        resp = client.post(f'/api/v1/repositories/repos/{repo.id}/favorite')
        assert resp.status_code == 200
        assert UserFavorite.objects.filter(user=user, repo=repo).exists()

    def test_add_favorite_idempotent(self, repo, auth_client):
        client, user = auth_client
        client.post(f'/api/v1/repositories/repos/{repo.id}/favorite')
        resp = client.post(f'/api/v1/repositories/repos/{repo.id}/favorite')
        assert resp.status_code == 200
        assert UserFavorite.objects.filter(user=user, repo=repo).count() == 1

    def test_remove_favorite_deletes_record(self, repo, auth_client):
        client, user = auth_client
        UserFavorite.objects.create(user=user, repo=repo)
        resp = client.delete(f'/api/v1/repositories/repos/{repo.id}/favorite')
        assert resp.status_code == 204
        assert not UserFavorite.objects.filter(user=user, repo=repo).exists()

    def test_unknown_repo_favorite_returns_404(self, auth_client):
        client, _ = auth_client
        resp = client.post(f'/api/v1/repositories/repos/{uuid.uuid4()}/favorite')
        assert resp.status_code == 404
