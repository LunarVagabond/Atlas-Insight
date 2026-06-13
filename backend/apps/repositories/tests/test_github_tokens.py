from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.repositories.github_tokens import (
    get_github_oauth_token,
    resolve_analysis_token,
    token_has_repo_scope,
)
from apps.repositories.models import Repository

User = get_user_model()


@pytest.fixture
def repo(db):
    return Repository.objects.create(
        url='https://github.com/org/private-repo',
        owner='org',
        name='private-repo',
        auth_token='stored-pat',
    )


class TestTokenHasRepoScope:
    @patch('requests.get')
    def test_true_when_repo_in_scopes(self, mock_get):
        mock_get.return_value.headers = {'X-OAuth-Scopes': 'read:user, repo'}
        assert token_has_repo_scope('ghp_token') is True

    @patch('requests.get')
    def test_false_when_repo_missing(self, mock_get):
        mock_get.return_value.headers = {'X-OAuth-Scopes': 'read:user'}
        assert token_has_repo_scope('ghp_token') is False

    @patch('requests.get', side_effect=Exception('network'))
    def test_true_on_request_failure(self, mock_get):
        assert token_has_repo_scope('ghp_token') is True


class TestResolveAnalysisToken:
    def test_prefers_stored_pat(self, repo):
        user = User.objects.create_user(username='u1', password='pass')
        assert resolve_analysis_token(repo, user) == 'stored-pat'

    def test_falls_back_to_oauth(self, repo, db):
        repo.auth_token = ''
        repo.save(update_fields=['auth_token'])
        user = User.objects.create_user(username='u2', password='pass')
        with patch(
            'apps.repositories.github_tokens.get_github_oauth_token',
            return_value='oauth-token',
        ):
            assert resolve_analysis_token(repo, user) == 'oauth-token'

    def test_none_without_stored_or_oauth(self, db):
        bare = Repository.objects.create(
            url='https://github.com/org/bare',
            owner='org',
            name='bare',
        )
        assert resolve_analysis_token(bare, None) is None


class TestGetGithubOauthToken:
    def test_none_for_anonymous(self):
        assert get_github_oauth_token(None) is None

    @patch('apps.repositories.github_tokens._fetch_social_github_token', return_value='ghu_device')
    def test_accepts_ghu_without_scope_check(self, mock_fetch, db):
        user = User.objects.create_user(username='u3', password='pass')
        assert get_github_oauth_token(user) == 'ghu_device'

    @patch('apps.repositories.github_tokens.token_has_repo_scope', return_value=False)
    @patch('apps.repositories.github_tokens._fetch_social_github_token', return_value='ghp_noscope')
    def test_none_when_repo_scope_missing(self, mock_fetch, mock_scope, db):
        user = User.objects.create_user(username='u4', password='pass')
        assert get_github_oauth_token(user) is None
