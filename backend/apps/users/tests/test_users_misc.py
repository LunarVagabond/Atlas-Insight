"""Users app: signals, context_processors, models __str__, management command."""
import pytest
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import override_settings, RequestFactory

User = get_user_model()


# ---------------------------------------------------------------------------
# User & APIToken model methods
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserModel:
    def test_str_returns_github_login(self, db):
        user = User.objects.create_user(
            username='teststr', password='pass', github_login='githubhandle'
        )
        assert str(user) == 'githubhandle'

    def test_str_falls_back_to_username(self, db):
        user = User.objects.create_user(username='fallback', password='pass')
        assert str(user) == 'fallback'


@pytest.mark.django_db
class TestAPITokenModel:
    def test_str_representation(self, db):
        from apps.users.models import APIToken
        import secrets
        user = User.objects.create_user(username='tokstr', password='pass')
        token = APIToken.objects.create(
            user=user, name='mykey',
            token_hash=APIToken.hash_token(secrets.token_urlsafe(32)),
        )
        s = str(token)
        assert 'tokstr' in s
        assert 'mykey' in s

    def test_is_active_true_when_not_revoked(self, db):
        from apps.users.models import APIToken
        import secrets
        user = User.objects.create_user(username='activetok', password='pass')
        token = APIToken.objects.create(
            user=user, name='active',
            token_hash=APIToken.hash_token(secrets.token_urlsafe(32)),
        )
        assert token.is_active is True

    def test_is_active_false_when_revoked(self, db):
        from apps.users.models import APIToken
        from django.utils import timezone
        import secrets
        user = User.objects.create_user(username='revokedtok', password='pass')
        token = APIToken.objects.create(
            user=user, name='revoked',
            token_hash=APIToken.hash_token(secrets.token_urlsafe(32)),
            revoked_at=timezone.now(),
        )
        assert token.is_active is False


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class TestSyncGithubFields:
    def test_syncs_github_login_and_avatar(self, db):
        from apps.users.signals import _sync_github_fields
        user = User.objects.create_user(username='siguser', password='pass')

        sociallogin = MagicMock()
        sociallogin.account.provider = 'github'
        sociallogin.account.extra_data = {
            'login': 'gh_handle',
            'avatar_url': 'https://avatars.githubusercontent.com/u/1',
        }
        sociallogin.user = user

        _sync_github_fields(sociallogin)
        user.refresh_from_db()
        assert user.github_login == 'gh_handle'
        assert user.avatar_url == 'https://avatars.githubusercontent.com/u/1'

    def test_non_github_provider_is_noop(self, db):
        from apps.users.signals import _sync_github_fields
        user = User.objects.create_user(
            username='siguser2', password='pass', github_login='original'
        )
        sociallogin = MagicMock()
        sociallogin.account.provider = 'twitter'
        sociallogin.user = user

        _sync_github_fields(sociallogin)
        user.refresh_from_db()
        assert user.github_login == 'original'

    def test_on_social_added_fires(self, db):
        from apps.users.signals import on_social_added
        user = User.objects.create_user(username='added', password='pass')
        sociallogin = MagicMock()
        sociallogin.account.provider = 'github'
        sociallogin.account.extra_data = {'login': 'addedgh', 'avatar_url': ''}
        sociallogin.user = user
        on_social_added(sender=None, request=None, sociallogin=sociallogin)
        user.refresh_from_db()
        assert user.github_login == 'addedgh'

    def test_on_social_updated_fires(self, db):
        from apps.users.signals import on_social_updated
        user = User.objects.create_user(username='updated', password='pass')
        sociallogin = MagicMock()
        sociallogin.account.provider = 'github'
        sociallogin.account.extra_data = {'login': 'updatedgh', 'avatar_url': ''}
        sociallogin.user = user
        on_social_updated(sender=None, request=None, sociallogin=sociallogin)
        user.refresh_from_db()
        assert user.github_login == 'updatedgh'

    def test_login_falls_back_to_username_when_missing(self, db):
        from apps.users.signals import _sync_github_fields
        user = User.objects.create_user(username='fallbackgh', password='pass')
        sociallogin = MagicMock()
        sociallogin.account.provider = 'github'
        sociallogin.account.extra_data = {}
        sociallogin.user = user
        _sync_github_fields(sociallogin)
        user.refresh_from_db()
        assert user.github_login == 'fallbackgh'


# ---------------------------------------------------------------------------
# context_processors
# ---------------------------------------------------------------------------

class TestFrontendContext:
    @override_settings(FRONTEND_URL='https://app.example.com', SITE_NAME='Atlas Insight')
    def test_returns_frontend_url_and_site_name(self):
        from apps.users.context_processors import frontend_context
        result = frontend_context(None)
        assert result['frontend_url'] == 'https://app.example.com'
        assert result['site_name'] == 'Atlas Insight'


# ---------------------------------------------------------------------------
# Management command: ensure_github_socialapp
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnsureGithubSocialApp:
    @override_settings(SOCIALACCOUNT_PROVIDERS={
        'github': {'APP': {'client_id': 'ghclientid', 'secret': 'ghsecret'}}
    })
    def test_creates_social_app(self, db):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        err = StringIO()
        call_command('ensure_github_socialapp', stdout=out, stderr=err)
        output = out.getvalue()
        assert 'GitHub SocialApp' in output
        assert err.getvalue() == ''

    @override_settings(SOCIALACCOUNT_PROVIDERS={
        'github': {'APP': {'client_id': '', 'secret': ''}}
    })
    def test_no_client_id_writes_error(self, db):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        err = StringIO()
        call_command('ensure_github_socialapp', stdout=out, stderr=err)
        assert 'GITHUB_CLIENT_ID' in err.getvalue()
        assert out.getvalue() == ''

    @override_settings(SOCIALACCOUNT_PROVIDERS={
        'github': {'APP': {'client_id': 'ghid2', 'secret': 'ghsec2'}}
    })
    def test_updates_existing_social_app(self, db):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('ensure_github_socialapp', stdout=out)
        assert 'created' in out.getvalue()
        out2 = StringIO()
        call_command('ensure_github_socialapp', stdout=out2)
        assert 'updated' in out2.getvalue()
