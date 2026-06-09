from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.analysis.git_ops import (
    _list_branches_via_git,
    _parse_github_next_url,
    list_remote_branches,
)


def _mock_response(status=200, json_data=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else []
    r.headers = headers or {}
    return r


class TestParseGithubNextUrl:
    def test_extracts_next_url(self):
        link = (
            '<https://api.github.com/repos/o/r/branches?per_page=100&page=2>; rel="next", '
            '<https://api.github.com/repos/o/r/branches?per_page=100&page=5>; rel="last"'
        )
        assert _parse_github_next_url(link) == (
            'https://api.github.com/repos/o/r/branches?per_page=100&page=2'
        )

    def test_none_when_no_next(self):
        assert _parse_github_next_url(None) is None
        assert _parse_github_next_url('rel="last"') is None


class TestListRemoteBranches:
    URL = 'https://github.com/test/repo'

    @override_settings(GITHUB_TOKEN='')
    @patch('requests.get')
    def test_single_page(self, mock_get):
        mock_get.return_value = _mock_response(200, [
            {'name': 'main'},
            {'name': 'development'},
        ])
        result = list_remote_branches(self.URL)
        assert result == ['development', 'main']

    @patch('requests.get')
    def test_paginates_via_link_header(self, mock_get):
        page1 = _mock_response(
            200,
            [{'name': f'branch-{i}'} for i in range(100)],
            headers={
                'Link': (
                    '<https://api.github.com/repos/test/repo/branches?per_page=100&page=2>; '
                    'rel="next"'
                ),
            },
        )
        page2 = _mock_response(200, [{'name': 'development'}])
        mock_get.side_effect = [page1, page2]
        result = list_remote_branches(self.URL)
        assert 'development' in result
        assert len(result) == 101
        assert mock_get.call_count == 2

    @patch('apps.analysis.git_ops._list_branches_via_git')
    @patch('requests.get')
    def test_falls_back_to_git_on_api_failure(self, mock_get, mock_git):
        mock_get.return_value = _mock_response(403)
        mock_git.return_value = ['development', 'main']
        result = list_remote_branches(self.URL)
        assert result == ['development', 'main']
        mock_git.assert_called_once()

    @patch('apps.analysis.git_ops._list_branches_via_git')
    @patch('requests.get')
    def test_falls_back_to_git_on_empty_api(self, mock_get, mock_git):
        mock_get.return_value = _mock_response(200, [])
        mock_git.return_value = ['development']
        result = list_remote_branches(self.URL)
        assert result == ['development']

    @patch('apps.analysis.git_ops._list_branches_via_git')
    @patch('requests.get')
    def test_retries_without_bad_token(self, mock_get, mock_git):
        bad = _mock_response(401)
        good = _mock_response(200, [{'name': 'development'}, {'name': 'main'}])
        mock_get.side_effect = [bad, good]
        result = list_remote_branches(self.URL, pat='bad-oauth-token')
        assert result == ['development', 'main']
        mock_git.assert_not_called()

    @override_settings(GITHUB_TOKEN='')
    @patch('apps.analysis.git_ops._list_branches_from_cache')
    @patch('apps.analysis.git_ops._list_branches_via_git')
    @patch('requests.get')
    def test_falls_back_to_local_cache(self, mock_get, mock_git, mock_cache):
        mock_get.return_value = _mock_response(404)
        mock_git.return_value = []
        mock_cache.return_value = ['development', 'main']
        result = list_remote_branches(self.URL, pat='bad-token')
        assert result == ['development', 'main']
        mock_cache.assert_called_once()

    @patch('requests.get')
    def test_invalid_url_returns_empty(self, mock_get):
        assert list_remote_branches('https://gitlab.com/o/r') == []
        mock_get.assert_not_called()


class TestListBranchesViaGit:
    URL = 'https://github.com/test/repo'

    @patch('apps.analysis.git_ops.subprocess.run')
    def test_parses_refs(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='abc123\trefs/heads/main\ndef456\trefs/heads/development\n',
            stderr='',
        )
        result = _list_branches_via_git(self.URL)
        assert result == ['development', 'main']

    @patch('apps.analysis.git_ops.subprocess.run')
    def test_failure_returns_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout='', stderr='not found')
        assert _list_branches_via_git(self.URL) == []
