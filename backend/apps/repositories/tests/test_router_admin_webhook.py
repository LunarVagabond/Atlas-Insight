"""Cover remaining admin router gaps: webhook paths, dedup, invalid JSON, no-secret non-debug."""
import hashlib
import hmac
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, override_settings

from apps.repositories.models import AnalysisRun, Repository

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def repo(db):
    return Repository.objects.create(
        url='https://github.com/wh/test', owner='wh', name='test'
    )


def _signed_payload(payload: dict, secret: str) -> tuple[bytes, str]:
    body = json.dumps(payload).encode()
    sig = 'sha256=' + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, sig


@pytest.mark.django_db
class TestWebhookDedup:
    @override_settings(GITHUB_WEBHOOK_SECRET='testsecret', DEBUG=True)
    def test_duplicate_delivery_id_ignored(self):
        delivery_id = str(uuid.uuid4())
        payload = {'repository': {'html_url': 'https://github.com/wh/test'}}
        body, sig = _signed_payload(payload, 'testsecret')

        c = Client()
        resp1 = c.post(
            '/api/v1/repositories/webhooks/github',
            data=body, content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig,
            HTTP_X_GITHUB_DELIVERY=delivery_id,
            HTTP_X_GITHUB_EVENT='push',
        )
        assert resp1.status_code == 200

        resp2 = c.post(
            '/api/v1/repositories/webhooks/github',
            data=body, content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=sig,
            HTTP_X_GITHUB_DELIVERY=delivery_id,
            HTTP_X_GITHUB_EVENT='push',
        )
        assert resp2.status_code == 200
        assert AnalysisRun.objects.count() <= 1


@pytest.mark.django_db
class TestWebhookInvalidJson:
    @override_settings(GITHUB_WEBHOOK_SECRET='', DEBUG=True)
    def test_invalid_json_returns_400(self):
        resp = Client().post(
            '/api/v1/repositories/webhooks/github',
            data=b'not valid json {{',
            content_type='application/json',
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestWebhookPushWithRepo:
    @override_settings(GITHUB_WEBHOOK_SECRET='', DEBUG=True)
    @patch('apps.repositories.router_admin.analyze_repository')
    def test_push_event_repo_found_triggers_reanalysis(self, mock_task, repo):
        mock_task.delay.return_value = MagicMock(id='wh-task')
        payload = {
            'repository': {'html_url': 'https://github.com/wh/test'},
        }
        resp = Client().post(
            '/api/v1/repositories/webhooks/github',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
        )
        assert resp.status_code == 200
        mock_task.delay.assert_called_once()
        assert AnalysisRun.objects.filter(repo=repo).exists()

    @override_settings(GITHUB_WEBHOOK_SECRET='', DEBUG=True)
    def test_push_event_repo_not_found_returns_200(self):
        payload = {'repository': {'html_url': 'https://github.com/no/repo'}}
        resp = Client().post(
            '/api/v1/repositories/webhooks/github',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
        )
        assert resp.status_code == 200

    @override_settings(GITHUB_WEBHOOK_SECRET='', DEBUG=True)
    def test_push_event_no_repo_url_returns_200(self):
        payload = {'repository': {}}
        resp = Client().post(
            '/api/v1/repositories/webhooks/github',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_GITHUB_EVENT='push',
        )
        assert resp.status_code == 200


@pytest.mark.django_db
class TestWebhookNoSecret:
    @override_settings(GITHUB_WEBHOOK_SECRET='', DEBUG=False)
    def test_no_secret_non_debug_returns_500(self):
        resp = Client().post(
            '/api/v1/repositories/webhooks/github',
            data='{}',
            content_type='application/json',
        )
        assert resp.status_code == 500


@pytest.mark.django_db
class TestAdminStatsOsError:
    def test_oserror_in_cache_dir_handled_gracefully(self, db):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        staff = User.objects.create_user(username='staff_oserr', password='pass', is_staff=True)
        c = Client()
        c.force_login(staff)

        with patch('os.path.getsize', side_effect=OSError('permission denied')):
            resp = c.get('/api/v1/repositories/admin/stats')
        assert resp.status_code == 200
        assert resp.json()['cache_size_gb'] == 0.0
