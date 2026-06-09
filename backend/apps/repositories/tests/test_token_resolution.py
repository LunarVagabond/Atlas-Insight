from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from ninja.errors import HttpError

from apps.repositories.models import Repository
from apps.repositories.router_runs import (
    _persist_repo_token,
    _resolve_repo_access_token,
)

User = get_user_model()


@pytest.fixture
def repo(db):
    return Repository.objects.create(
        url='https://github.com/org/spyglass',
        owner='org',
        name='spyglass',
        auth_token='stored-pat',
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


class TestResolveRepoAccessToken:
    def test_explicit_pat_wins(self, request_factory, repo):
        request = request_factory.get('/')
        assert _resolve_repo_access_token(request, 'ghp_explicit', repo) == 'ghp_explicit'

    def test_stored_token_before_oauth(self, request_factory, repo):
        request = request_factory.get('/')
        with patch('apps.repositories.router_runs._resolve_token_soft', return_value='oauth-token'):
            assert _resolve_repo_access_token(request, None, repo) == 'stored-pat'

    def test_oauth_when_no_stored(self, request_factory, db):
        request = request_factory.get('/')
        bare = Repository.objects.create(
            url='https://github.com/org/other',
            owner='org',
            name='other',
        )
        with patch('apps.repositories.router_runs._resolve_token_soft', return_value='oauth-token'):
            assert _resolve_repo_access_token(request, None, bare) == 'oauth-token'

    def test_explicit_pat_used_even_when_scope_check_raises(self, request_factory, repo):
        request = request_factory.get('/')
        with patch(
            'apps.repositories.router_runs._resolve_token',
            side_effect=HttpError(403, 'missing repo scope'),
        ):
            assert _resolve_repo_access_token(request, 'ghp_org_pat', repo) == 'ghp_org_pat'


class TestPersistRepoToken:
    def test_persists_only_explicit_pat(self, repo):
        _persist_repo_token(repo, 'ghp_new', explicit=True)
        repo.refresh_from_db()
        assert repo.auth_token == 'ghp_new'

    def test_skips_non_explicit(self, repo):
        _persist_repo_token(repo, 'oauth-token', explicit=False)
        repo.refresh_from_db()
        assert repo.auth_token == 'stored-pat'
