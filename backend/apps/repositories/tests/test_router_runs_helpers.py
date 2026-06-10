"""Cover router_runs helper functions and remaining analyze/get_run/retry paths."""
import ipaddress
import secrets
import socket
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, override_settings
from django.utils import timezone

from apps.repositories.models import AnalysisRun, Repository
from apps.users.models import APIToken

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='helperuser', password='pass')


@pytest.fixture
def user_client(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def superuser(db):
    return User.objects.create_user(
        username='helpersuper', password='pass', is_staff=True, is_superuser=True
    )


@pytest.fixture
def superuser_client(superuser):
    c = Client()
    c.force_login(superuser)
    return c


# ---------------------------------------------------------------------------
# _validate_webhook_url
# ---------------------------------------------------------------------------

class TestValidateWebhookUrl:
    def _call(self, url):
        from apps.repositories.router_runs import _validate_webhook_url
        from ninja.errors import HttpError
        try:
            _validate_webhook_url(url)
            return None
        except HttpError as e:
            return e.status_code

    def test_http_scheme_rejected(self):
        assert self._call('http://example.com/hook') == 422

    def test_no_hostname_rejected(self):
        assert self._call('https:///path') == 422

    @patch('socket.getaddrinfo')
    def test_dns_failure_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = socket.gaierror('nxdomain')
        assert self._call('https://nxdomain.invalid/hook') == 422

    @patch('socket.getaddrinfo')
    def test_private_ip_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ('10.0.0.1', 0))]
        assert self._call('https://internal.example.com/hook') == 422

    @patch('socket.getaddrinfo')
    def test_loopback_ip_rejected(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ('127.0.0.1', 0))]
        assert self._call('https://localhost/hook') == 422

    @patch('socket.getaddrinfo')
    def test_public_ip_accepted(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ('93.184.216.34', 0))]
        assert self._call('https://example.com/hook') is None


# ---------------------------------------------------------------------------
# _cooldown_until
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCooldownUntil:
    def test_no_last_analyzed_at_returns_none(self, db):
        from apps.repositories.router_runs import _cooldown_until
        repo = Repository.objects.create(
            url='https://github.com/cool/test', owner='cool', name='test'
        )
        assert _cooldown_until(repo) is None

    def test_recent_analysis_returns_cutoff(self, db):
        from apps.repositories.router_runs import _cooldown_until
        repo = Repository.objects.create(
            url='https://github.com/cool/test2', owner='cool', name='test2',
        )
        AnalysisRun.objects.create(
            repo=repo, status='completed', branch='', completed_at=timezone.now()
        )
        result = _cooldown_until(repo)
        assert result is not None

    def test_old_analysis_returns_none(self, db):
        from datetime import timedelta
        from apps.repositories.router_runs import _cooldown_until
        repo = Repository.objects.create(
            url='https://github.com/cool/test3', owner='cool', name='test3',
            last_analyzed_at=timezone.now() - timedelta(hours=10),
        )
        assert _cooldown_until(repo) is None


# ---------------------------------------------------------------------------
# _resolve_token
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestResolveToken:
    def test_pat_takes_precedence(self):
        from apps.repositories.router_runs import _resolve_token
        factory = RequestFactory()
        req = factory.get('/')
        req.user = MagicMock(is_authenticated=False)
        result = _resolve_token(req, 'ghp_mypat')
        assert result == 'ghp_mypat'

    def test_unauthenticated_no_pat_returns_none(self):
        from apps.repositories.router_runs import _resolve_token
        factory = RequestFactory()
        req = factory.get('/')
        req.user = MagicMock(is_authenticated=False)
        assert _resolve_token(req, None) is None

    def test_authenticated_no_social_token_returns_none(self, user):
        from apps.repositories.router_runs import _resolve_token
        factory = RequestFactory()
        req = factory.get('/')
        req.user = user
        assert _resolve_token(req, None) is None


# ---------------------------------------------------------------------------
# _token_has_repo_scope
# ---------------------------------------------------------------------------

class TestTokenHasRepoScope:
    @patch('requests.get')
    def test_has_repo_scope_returns_true(self, mock_get):
        from apps.repositories.router_runs import _token_has_repo_scope
        mock_get.return_value = MagicMock(
            headers={'X-OAuth-Scopes': 'repo, read:user'}
        )
        assert _token_has_repo_scope('ghp_token') is True

    @patch('requests.get')
    def test_no_repo_scope_returns_false(self, mock_get):
        from apps.repositories.router_runs import _token_has_repo_scope
        mock_get.return_value = MagicMock(
            headers={'X-OAuth-Scopes': 'read:user, gist'}
        )
        assert _token_has_repo_scope('ghp_token') is False

    @patch('requests.get')
    def test_exception_returns_true(self, mock_get):
        from apps.repositories.router_runs import _token_has_repo_scope
        mock_get.side_effect = Exception('network error')
        assert _token_has_repo_scope('ghp_token') is True


# ---------------------------------------------------------------------------
# _user_can_access_repo
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserCanAccessRepo:
    def test_no_social_token_returns_false(self, user):
        from apps.repositories.router_runs import _user_can_access_repo
        from django.core.cache import cache
        cache.clear()
        result = _user_can_access_repo(user, 'owner', 'repo')
        assert result is False

    @patch('requests.get')
    def test_github_200_returns_true(self, mock_get, db):
        from apps.repositories.router_runs import _user_can_access_repo
        from django.core.cache import cache
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from django.contrib.sites.models import Site

        cache.clear()
        user = User.objects.create_user(username='accessuser', password='pass')
        app = SocialApp.objects.create(provider='github', name='GitHub', client_id='x', secret='y')
        app.sites.add(Site.objects.get_current())
        account = SocialAccount.objects.create(user=user, provider='github', uid='123')
        SocialToken.objects.create(account=account, app=app, token='ghp_test')

        mock_get.return_value = MagicMock(status_code=200)

        result = _user_can_access_repo(user, 'org', 'private-repo')
        assert result is True

    @patch('requests.get')
    def test_github_404_returns_false(self, mock_get, db):
        from apps.repositories.router_runs import _user_can_access_repo
        from django.core.cache import cache
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from django.contrib.sites.models import Site

        cache.clear()
        user = User.objects.create_user(username='noaccessuser', password='pass')
        app = SocialApp.objects.create(provider='github', name='GitHubNA', client_id='xx', secret='yy')
        app.sites.add(Site.objects.get_current())
        account = SocialAccount.objects.create(user=user, provider='github', uid='456')
        SocialToken.objects.create(account=account, app=app, token='ghp_test2')

        mock_get.return_value = MagicMock(status_code=404)

        result = _user_can_access_repo(user, 'org', 'private-repo')
        assert result is False


# ---------------------------------------------------------------------------
# analyze endpoint: webhook_url, cached SHA, notification_email
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnalyzeEdgeCases:
    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha')
    @patch('socket.getaddrinfo')
    def test_analyze_with_webhook_url(self, mock_dns, mock_sha, mock_task):
        mock_sha.return_value = 'newsha123'
        mock_task.delay.return_value = MagicMock(id='task1')
        mock_dns.return_value = [(None, None, None, None, ('93.184.216.34', 0))]

        resp = Client().post(
            '/api/v1/repositories/analyze',
            data='{"url":"https://github.com/a/b","webhook_url":"https://example.com/hook"}',
            content_type='application/json',
        )
        assert resp.status_code == 200

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha')
    def test_cached_sha_returns_existing_run(self, mock_sha, mock_task, db):
        repo = Repository.objects.create(
            url='https://github.com/sha/cached', owner='sha', name='cached',
            last_commit_sha='abc123',
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed')
        mock_sha.return_value = 'abc123'

        resp = Client().post(
            '/api/v1/repositories/analyze',
            data='{"url":"https://github.com/sha/cached"}',
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['cached'] is True
        assert data['run_id'] == str(run.id)
        mock_task.delay.assert_not_called()

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha')
    def test_notification_email_requires_auth(self, mock_sha, mock_task):
        mock_sha.return_value = None
        resp = Client().post(
            '/api/v1/repositories/analyze',
            data='{"url":"https://github.com/a/b","notification_email":"x@x.com"}',
            content_type='application/json',
        )
        assert resp.status_code == 403

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha')
    def test_notification_email_must_match_account(self, mock_sha, mock_task, user_client, user):
        mock_sha.return_value = None
        mock_task.delay.return_value = MagicMock(id='t1')
        user.email = 'real@example.com'
        user.save()
        resp = user_client.post(
            '/api/v1/repositories/analyze',
            data='{"url":"https://github.com/a/b","notification_email":"other@example.com"}',
            content_type='application/json',
        )
        assert resp.status_code == 422

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha')
    def test_notification_email_matching_account_succeeds(self, mock_sha, mock_task, user_client, user):
        mock_sha.return_value = None
        mock_task.delay.return_value = MagicMock(id='t2')
        user.email = 'real@example.com'
        user.save()
        resp = user_client.post(
            '/api/v1/repositories/analyze',
            data='{"url":"https://github.com/notif/repo","notification_email":"real@example.com"}',
            content_type='application/json',
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# get_run: private repo different user calls _user_can_access_repo
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGetRunPrivateAccess:
    @patch('apps.repositories.router_runs._user_can_access_repo', return_value=False)
    def test_different_user_private_repo_denied(self, mock_access, db):
        owner = User.objects.create_user(username='priv_owner_gr', password='pass')
        other = User.objects.create_user(username='priv_other_gr', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/gr_test', owner='priv', name='gr_test', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={}, user=owner)
        c = Client()
        c.force_login(other)
        resp = c.get(f'/api/v1/repositories/runs/{run.id}')
        assert resp.status_code == 403
        mock_access.assert_called_once()

    @patch('apps.repositories.router_runs._user_can_access_repo', return_value=True)
    def test_different_user_with_access_can_view(self, mock_access, db):
        owner = User.objects.create_user(username='priv_owner_ok', password='pass')
        other = User.objects.create_user(username='priv_other_ok', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/ok_test', owner='priv', name='ok_test', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', result={}, user=owner)
        c = Client()
        c.force_login(other)
        resp = c.get(f'/api/v1/repositories/runs/{run.id}')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# retry_run: private repo not owner
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRetryPrivateRepo:
    def test_private_repo_anonymous_returns_403(self, db):
        owner = User.objects.create_user(username='retry_owner', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/retry', owner='priv', name='retry', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', user=owner)
        resp = Client().post(f'/api/v1/repositories/runs/{run.id}/retry')
        assert resp.status_code == 403

    def test_private_repo_different_user_returns_403(self, db):
        owner = User.objects.create_user(username='retry_own2', password='pass')
        other = User.objects.create_user(username='retry_oth2', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/retry2', owner='priv', name='retry2', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', user=owner)
        c = Client()
        c.force_login(other)
        resp = c.post(f'/api/v1/repositories/runs/{run.id}/retry')
        assert resp.status_code == 403

    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs._user_can_access_repo', return_value=True)
    def test_private_repo_collaborator_can_retry(self, _access, mock_task, db):
        mock_task.delay.return_value = MagicMock(id='collab-retry')
        owner = User.objects.create_user(username='retry_own3', password='pass')
        collab = User.objects.create_user(username='retry_col3', password='pass')
        repo = Repository.objects.create(
            url='https://github.com/priv/retry3', owner='priv', name='retry3', is_private=True
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed', user=owner)
        c = Client()
        c.force_login(collab)
        resp = c.post(f'/api/v1/repositories/runs/{run.id}/retry')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# _resolve_token: social token paths
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestResolveTokenSocial:
    def test_ghu_token_returned_directly(self, db):
        from apps.repositories.router_runs import _resolve_token
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from django.contrib.sites.models import Site

        user = User.objects.create_user(username='ghu_user', password='pass')
        app = SocialApp.objects.create(provider='github', name='GHResolve', client_id='r1', secret='r2')
        app.sites.add(Site.objects.get_current())
        account = SocialAccount.objects.create(user=user, provider='github', uid='ghu1')
        SocialToken.objects.create(account=account, app=app, token='ghu_devicetoken')

        factory = RequestFactory()
        req = factory.get('/')
        req.user = user
        result = _resolve_token(req, None)
        assert result == 'ghu_devicetoken'

    @patch('apps.repositories.router_runs._token_has_repo_scope', return_value=False)
    def test_non_ghu_token_without_scope_raises_403(self, mock_scope, db):
        from apps.repositories.router_runs import _resolve_token
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from django.contrib.sites.models import Site
        from ninja.errors import HttpError

        user = User.objects.create_user(username='noscope_user', password='pass')
        app = SocialApp.objects.create(provider='github', name='GHNoscope', client_id='n1', secret='n2')
        app.sites.add(Site.objects.get_current())
        account = SocialAccount.objects.create(user=user, provider='github', uid='ns1')
        SocialToken.objects.create(account=account, app=app, token='ghp_noscope')

        factory = RequestFactory()
        req = factory.get('/')
        req.user = user
        with pytest.raises(HttpError) as exc_info:
            _resolve_token(req, None)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# _user_can_access_repo: cache hit and exception
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserCanAccessRepoExtra:
    def test_cached_true_returned_immediately(self, db):
        from apps.repositories.router_runs import _user_can_access_repo
        from django.core.cache import cache

        cache.clear()
        user = User.objects.create_user(username='cacheuser', password='pass')
        cache_key = f'repo_access_{user.pk}_org_repo'
        cache.set(cache_key, True, 900)
        result = _user_can_access_repo(user, 'org', 'repo')
        assert result is True

    @patch('requests.get', side_effect=Exception('network error'))
    def test_exception_returns_false(self, mock_get, db):
        from apps.repositories.router_runs import _user_can_access_repo
        from django.core.cache import cache
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from django.contrib.sites.models import Site

        cache.clear()
        user = User.objects.create_user(username='excuser', password='pass')
        app = SocialApp.objects.create(provider='github', name='GHExc', client_id='e1', secret='e2')
        app.sites.add(Site.objects.get_current())
        account = SocialAccount.objects.create(user=user, provider='github', uid='exc1')
        SocialToken.objects.create(account=account, app=app, token='ghp_exc')

        result = _user_can_access_repo(user, 'org', 'private')
        assert result is False


# ---------------------------------------------------------------------------
# analyze: token save path (251-252)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnalyzeTokenSave:
    @patch('apps.repositories.router_runs.analyze_repository')
    @patch('apps.repositories.router_runs.fetch_latest_sha')
    def test_new_pat_saved_to_repo(self, mock_sha, mock_task, db):
        mock_sha.return_value = 'sha_new'
        mock_task.delay.return_value = MagicMock(id='tok-task')

        repo = Repository.objects.create(
            url='https://github.com/patsave/repo',
            owner='patsave', name='repo',
            auth_token='old_token',
        )

        resp = Client().post(
            '/api/v1/repositories/analyze',
            data='{"url":"https://github.com/patsave/repo","pat":"ghp_newtoken"}',
            content_type='application/json',
        )
        assert resp.status_code == 200
        repo.refresh_from_db()
        assert repo.auth_token == 'ghp_newtoken'
