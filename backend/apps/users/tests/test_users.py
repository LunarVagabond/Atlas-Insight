"""Users app tests: /me, logout, API token CRUD, middleware."""
import secrets
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, override_settings

from apps.users.models import APIToken

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser', password='pass', email='test@example.com',
        github_login='testgh', avatar_url='https://github.com/avatar.png',
    )


@pytest.fixture
def auth_client(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
class TestMeEndpoint:
    def test_unauthenticated_returns_401(self):
        resp = Client().get('/api/v1/auth/me')
        assert resp.status_code == 401

    def test_authenticated_returns_user_data(self, auth_client, user):
        resp = auth_client.get('/api/v1/auth/me')
        assert resp.status_code == 200
        data = resp.json()
        assert data['username'] == 'testuser'
        assert data['email'] == 'test@example.com'
        assert data['github_login'] == 'testgh'
        assert data['is_staff'] is False
        assert data['is_superuser'] is False
        assert data['github_connected'] is False

    def test_staff_flag_returned(self, db):
        staff = User.objects.create_user(username='staffme', password='pass', is_staff=True)
        c = Client()
        c.force_login(staff)
        data = c.get('/api/v1/auth/me').json()
        assert data['is_staff'] is True


@pytest.mark.django_db
class TestLogout:
    def test_logout_returns_ok(self, auth_client):
        resp = auth_client.post('/api/v1/auth/logout')
        assert resp.status_code == 200
        assert resp.json() == {'ok': True}

    def test_anonymous_logout_succeeds(self):
        resp = Client().post('/api/v1/auth/logout')
        assert resp.status_code == 200


@pytest.mark.django_db
class TestListTokens:
    def test_unauthenticated_returns_401(self):
        resp = Client().get('/api/v1/auth/tokens')
        assert resp.status_code == 401

    def test_empty_list_when_no_tokens(self, auth_client):
        resp = auth_client.get('/api/v1/auth/tokens')
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_active_tokens_only(self, auth_client, user):
        from django.utils import timezone
        raw = secrets.token_urlsafe(32)
        active = APIToken.objects.create(
            user=user, name='active', token_hash=APIToken.hash_token(raw)
        )
        revoked = APIToken.objects.create(
            user=user, name='revoked',
            token_hash=APIToken.hash_token(secrets.token_urlsafe(32)),
            revoked_at=timezone.now(),
        )
        resp = auth_client.get('/api/v1/auth/tokens')
        assert resp.status_code == 200
        names = [t['name'] for t in resp.json()]
        assert 'active' in names
        assert 'revoked' not in names

    def test_token_fields_present(self, auth_client, user):
        raw = secrets.token_urlsafe(32)
        APIToken.objects.create(
            user=user, name='mytoken', token_hash=APIToken.hash_token(raw)
        )
        token = auth_client.get('/api/v1/auth/tokens').json()[0]
        assert 'id' in token
        assert token['name'] == 'mytoken'
        assert 'created_at' in token
        assert token['last_used_at'] is None


@pytest.mark.django_db
class TestCreateToken:
    def test_unauthenticated_returns_401(self):
        resp = Client().post(
            '/api/v1/auth/tokens',
            data='{"name": "mytoken"}',
            content_type='application/json',
        )
        assert resp.status_code == 401

    def test_creates_token_and_returns_raw_value(self, auth_client):
        resp = auth_client.post(
            '/api/v1/auth/tokens',
            data='{"name": "ci-token"}',
            content_type='application/json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == 'ci-token'
        assert 'token' in data
        assert len(data['token']) > 20

    def test_empty_name_returns_400(self, auth_client):
        resp = auth_client.post(
            '/api/v1/auth/tokens',
            data='{"name": "   "}',
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_max_20_tokens_enforced(self, auth_client, user):
        for i in range(20):
            APIToken.objects.create(
                user=user,
                name=f'token-{i}',
                token_hash=APIToken.hash_token(secrets.token_urlsafe(32)),
            )
        resp = auth_client.post(
            '/api/v1/auth/tokens',
            data='{"name": "overflow"}',
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_token_hash_stored_not_raw(self, auth_client, user):
        resp = auth_client.post(
            '/api/v1/auth/tokens',
            data='{"name": "hashcheck"}',
            content_type='application/json',
        )
        raw = resp.json()['token']
        db_token = APIToken.objects.get(user=user, name='hashcheck')
        assert db_token.token_hash != raw
        assert db_token.token_hash == APIToken.hash_token(raw)


@pytest.mark.django_db
class TestRevokeToken:
    def test_unauthenticated_returns_401(self, db):
        resp = Client().delete(f'/api/v1/auth/tokens/{uuid.uuid4()}')
        assert resp.status_code == 401

    def test_revokes_own_token(self, auth_client, user):
        raw = secrets.token_urlsafe(32)
        token = APIToken.objects.create(
            user=user, name='todel', token_hash=APIToken.hash_token(raw)
        )
        resp = auth_client.delete(f'/api/v1/auth/tokens/{token.id}')
        assert resp.status_code == 204
        token.refresh_from_db()
        assert token.revoked_at is not None

    def test_unknown_token_returns_404(self, auth_client):
        resp = auth_client.delete(f'/api/v1/auth/tokens/{uuid.uuid4()}')
        assert resp.status_code == 404

    def test_cannot_revoke_other_users_token(self, db):
        owner = User.objects.create_user(username='tok_owner', password='pass')
        other = User.objects.create_user(username='tok_other', password='pass')
        token = APIToken.objects.create(
            user=owner, name='tok', token_hash=APIToken.hash_token(secrets.token_urlsafe(32))
        )
        c = Client()
        c.force_login(other)
        resp = c.delete(f'/api/v1/auth/tokens/{token.id}')
        assert resp.status_code == 404

    def test_cannot_revoke_already_revoked_token(self, auth_client, user):
        from django.utils import timezone
        token = APIToken.objects.create(
            user=user, name='already_revoked',
            token_hash=APIToken.hash_token(secrets.token_urlsafe(32)),
            revoked_at=timezone.now(),
        )
        resp = auth_client.delete(f'/api/v1/auth/tokens/{token.id}')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestAPITokenAuth:
    """APITokenAuth bearer scheme used by router_runs analyze endpoint."""

    @pytest.fixture
    def token_pair(self, user):
        raw = secrets.token_urlsafe(32)
        token = APIToken.objects.create(
            user=user, name='bearer-test', token_hash=APIToken.hash_token(raw)
        )
        return raw, token

    def test_valid_bearer_sets_user(self, user, token_pair):
        raw, _ = token_pair
        from apps.users.router import APITokenAuth
        factory = RequestFactory()
        req = factory.get('/')
        result = APITokenAuth().authenticate(req, raw)
        assert result == user

    def test_invalid_bearer_returns_none(self, db):
        from apps.users.router import APITokenAuth
        factory = RequestFactory()
        req = factory.get('/')
        result = APITokenAuth().authenticate(req, 'invalid-token-xyz')
        assert result is None

    def test_revoked_token_returns_none(self, user, token_pair):
        from django.utils import timezone
        raw, token = token_pair
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])

        from apps.users.router import APITokenAuth
        factory = RequestFactory()
        req = factory.get('/')
        result = APITokenAuth().authenticate(req, raw)
        assert result is None


class TestOAuthCallbackMiddleware:
    @override_settings(BACKEND_URL='')
    def test_no_backend_url_passthrough(self):
        from apps.users.middleware import OAuthCallbackHostMiddleware
        get_response = lambda req: req
        mw = OAuthCallbackHostMiddleware(get_response)
        assert mw._host is None

    @override_settings(BACKEND_URL='https://example.com')
    def test_backend_url_parsed(self):
        from apps.users.middleware import OAuthCallbackHostMiddleware
        get_response = lambda req: req
        mw = OAuthCallbackHostMiddleware(get_response)
        assert mw._host == 'example.com'
        assert mw._scheme == 'https'

    @override_settings(BACKEND_URL='https://example.com')
    def test_accounts_path_rewrites_host(self):
        from apps.users.middleware import OAuthCallbackHostMiddleware
        get_response = lambda req: req
        mw = OAuthCallbackHostMiddleware(get_response)

        factory = RequestFactory()
        req = factory.get('/accounts/github/login/')
        req.META['HTTP_HOST'] = 'localhost:4500'
        mw(req)
        assert req.META['HTTP_HOST'] == 'example.com'
        assert req.META['wsgi.url_scheme'] == 'https'

    @override_settings(BACKEND_URL='https://example.com')
    def test_non_accounts_path_unchanged(self):
        from apps.users.middleware import OAuthCallbackHostMiddleware
        get_response = lambda req: req
        mw = OAuthCallbackHostMiddleware(get_response)

        factory = RequestFactory()
        req = factory.get('/api/v1/auth/me')
        req.META['HTTP_HOST'] = 'localhost:4500'
        mw(req)
        assert req.META['HTTP_HOST'] == 'localhost:4500'
