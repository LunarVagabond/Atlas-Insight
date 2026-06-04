from unittest.mock import MagicMock, patch

import pytest
from apps.analysis.github_meta import (
    _fetch_contributors,
    _fetch_languages,
    _fetch_releases_meta,
    _parse_issues,
    fetch_contribution_data,
    fetch_github_meta,
    fetch_latest_sha,
)


def _mock_response(status=200, json_data=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data if json_data is not None else {}
    r.headers = headers or {}
    return r


class TestFetchLatestSha:
    @patch('apps.analysis.github_meta.requests.get')
    def test_returns_sha(self, mock_get):
        mock_get.return_value = _mock_response(200, [{'sha': 'abc123def456'}])
        result = fetch_latest_sha('owner', 'repo', token='tok')
        assert result == 'abc123def456'

    @patch('apps.analysis.github_meta.requests.get')
    def test_empty_list_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(200, [])
        result = fetch_latest_sha('owner', 'repo')
        assert result is None

    @patch('apps.analysis.github_meta.requests.get')
    def test_non_200_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(404)
        result = fetch_latest_sha('owner', 'repo')
        assert result is None

    @patch('apps.analysis.github_meta.requests.get')
    def test_exception_returns_none(self, mock_get):
        mock_get.side_effect = Exception('network error')
        result = fetch_latest_sha('owner', 'repo')
        assert result is None


class TestFetchContributors:
    @patch('apps.analysis.github_meta.requests.get')
    def test_returns_contributors(self, mock_get):
        mock_get.return_value = _mock_response(200, [
            {'login': 'alice', 'avatar_url': 'https://a.com/av', 'html_url': 'https://github.com/alice', 'contributions': 100, 'type': 'User'},
            {'login': 'anon', 'avatar_url': '', 'html_url': '', 'contributions': 5, 'type': 'Anonymous'},
        ])
        result = _fetch_contributors('owner', 'repo', {})
        assert len(result) == 1
        assert result[0]['login'] == 'alice'

    @patch('apps.analysis.github_meta.requests.get')
    def test_non_200_returns_empty(self, mock_get):
        mock_get.return_value = _mock_response(403)
        result = _fetch_contributors('owner', 'repo', {})
        assert result == []

    @patch('apps.analysis.github_meta.requests.get')
    def test_exception_returns_empty(self, mock_get):
        mock_get.side_effect = Exception('error')
        result = _fetch_contributors('owner', 'repo', {})
        assert result == []


class TestFetchLanguages:
    @patch('apps.analysis.github_meta.requests.get')
    def test_returns_language_breakdown(self, mock_get):
        mock_get.return_value = _mock_response(200, {'Python': 80000, 'TypeScript': 20000})
        result = _fetch_languages('owner', 'repo', {})
        assert len(result) == 2
        assert result[0]['name'] == 'Python'
        assert result[0]['pct'] == 80.0

    @patch('apps.analysis.github_meta.requests.get')
    def test_non_200_returns_empty(self, mock_get):
        mock_get.return_value = _mock_response(404)
        result = _fetch_languages('owner', 'repo', {})
        assert result == []

    @patch('apps.analysis.github_meta.requests.get')
    def test_exception_returns_empty(self, mock_get):
        mock_get.side_effect = Exception('error')
        result = _fetch_languages('owner', 'repo', {})
        assert result == []

    @patch('apps.analysis.github_meta.requests.get')
    def test_sorted_by_bytes_desc(self, mock_get):
        mock_get.return_value = _mock_response(200, {'Go': 10000, 'Python': 50000, 'JS': 20000})
        result = _fetch_languages('owner', 'repo', {})
        assert result[0]['name'] == 'Python'
        assert result[1]['name'] == 'JS'


class TestFetchReleasesMeta:
    @patch('apps.analysis.github_meta.requests.get')
    def test_returns_release_counts(self, mock_get):
        mock_get.return_value = _mock_response(200, [
            {'tag_name': 'v1.0', 'published_at': '2025-01-01', 'prerelease': False, 'draft': False},
            {'tag_name': 'v0.9-beta', 'published_at': '2024-12-01', 'prerelease': True, 'draft': False},
        ], headers={})
        result = _fetch_releases_meta('owner', 'repo', {})
        assert result['stable_count'] == 1
        assert result['prerelease_count'] == 1
        assert result['total_count'] == 2

    @patch('apps.analysis.github_meta.requests.get')
    def test_no_releases_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(200, [], headers={})
        result = _fetch_releases_meta('owner', 'repo', {})
        assert result is None

    @patch('apps.analysis.github_meta.requests.get')
    def test_non_200_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(404, headers={})
        result = _fetch_releases_meta('owner', 'repo', {})
        assert result is None

    @patch('apps.analysis.github_meta.requests.get')
    def test_exception_returns_none(self, mock_get):
        mock_get.side_effect = Exception('error')
        result = _fetch_releases_meta('owner', 'repo', {})
        assert result is None

    @patch('apps.analysis.github_meta.requests.get')
    def test_paginates_when_has_next(self, mock_get):
        page1 = _mock_response(200, [
            {'tag_name': f'v{i}', 'published_at': '2025-01-01', 'prerelease': False, 'draft': False}
            for i in range(5)
        ], headers={'Link': '<url?page=2>; rel="next"'})
        page2 = _mock_response(200, [
            {'tag_name': f'v{i+5}', 'published_at': '2025-01-01', 'prerelease': False, 'draft': False}
            for i in range(3)
        ], headers={})
        mock_get.side_effect = [page1, page2]
        result = _fetch_releases_meta('owner', 'repo', {})
        assert result['stable_count'] == 8

    @patch('apps.analysis.github_meta.requests.get')
    def test_latest_stable_and_prerelease(self, mock_get):
        mock_get.return_value = _mock_response(200, [
            {'tag_name': 'v2.0', 'published_at': '2025-06-01', 'prerelease': False, 'draft': False},
            {'tag_name': 'v2.1-alpha', 'published_at': '2025-07-01', 'prerelease': True, 'draft': False},
        ], headers={})
        result = _fetch_releases_meta('owner', 'repo', {})
        assert result['latest_stable']['name'] == 'v2.0'
        assert result['latest_prerelease']['name'] == 'v2.1-alpha'

    @patch('apps.analysis.github_meta.requests.get')
    def test_draft_excluded(self, mock_get):
        mock_get.return_value = _mock_response(200, [
            {'tag_name': 'v1.0-draft', 'published_at': '2025-01-01', 'prerelease': False, 'draft': True},
        ], headers={})
        result = _fetch_releases_meta('owner', 'repo', {})
        # draft releases are excluded from stable/prerelease but all_releases is non-empty → dict returned
        assert result is not None
        assert result['stable_count'] == 0
        assert result['prerelease_count'] == 0

    @patch('apps.analysis.github_meta.requests.get')
    def test_no_prereleases(self, mock_get):
        mock_get.return_value = _mock_response(200, [
            {'tag_name': 'v1.0', 'published_at': '2025-01-01', 'prerelease': False, 'draft': False},
        ], headers={})
        result = _fetch_releases_meta('owner', 'repo', {})
        assert result['latest_prerelease'] is None


class TestParseIssues:
    def test_filters_contribution_labels(self):
        raw = [
            {'number': 1, 'title': 'Bug report', 'html_url': 'http://x.com/1',
             'labels': [{'name': 'bug'}], 'body': 'details'},
            {'number': 2, 'title': 'Help me', 'html_url': 'http://x.com/2',
             'labels': [{'name': 'help wanted'}], 'body': 'need help'},
        ]
        seen: set = set()
        result = _parse_issues(raw, seen)
        assert len(result) == 1
        assert result[0]['number'] == 2

    def test_excludes_pull_requests(self):
        raw = [
            {'number': 1, 'title': 'PR', 'html_url': 'x', 'labels': [{'name': 'help wanted'}],
             'body': '', 'pull_request': {'url': 'x'}},
        ]
        seen: set = set()
        result = _parse_issues(raw, seen)
        assert result == []

    def test_deduplicates_by_number(self):
        issue = {'number': 1, 'title': 'Help', 'html_url': 'x',
                 'labels': [{'name': 'good first issue'}], 'body': ''}
        seen: set = {1}
        result = _parse_issues([issue], seen)
        assert result == []

    def test_truncates_body_at_300(self):
        raw = [{'number': 1, 'title': 'T', 'html_url': 'x',
                'labels': [{'name': 'good first issue'}], 'body': 'x' * 500}]
        seen: set = set()
        result = _parse_issues(raw, seen)
        assert len(result[0]['body_excerpt']) == 300


class TestFetchContributionData:
    @patch('apps.analysis.github_meta.requests.get')
    def test_returns_issues_and_pr_refs(self, mock_get):
        issue_resp = _mock_response(200, [
            {'number': 1, 'title': 'Good task', 'html_url': 'http://x/1',
             'labels': [{'name': 'good first issue'}], 'body': None}
        ])
        # One feature label returns results immediately, stopping the loop
        feature_resp_hit = _mock_response(200, [
            {'number': 2, 'title': 'Feature req', 'html_url': 'http://x/2',
             'labels': [{'name': 'enhancement'}], 'body': None}
        ])
        pr_resp = _mock_response(200, [
            {'title': 'Fix #1', 'body': 'Resolves #2'}
        ])
        mock_get.side_effect = [issue_resp, feature_resp_hit, pr_resp]
        result = fetch_contribution_data('owner', 'repo', {})
        assert result is not None
        assert 'issues' in result
        assert 'pr_issue_refs' in result

    @patch('apps.analysis.github_meta.requests.get')
    def test_rate_limit_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(403)
        result = fetch_contribution_data('owner', 'repo', {})
        assert result is None

    @patch('apps.analysis.github_meta.requests.get')
    def test_exception_returns_none(self, mock_get):
        mock_get.side_effect = Exception('network error')
        result = fetch_contribution_data('owner', 'repo', {})
        assert result is None


class TestFetchGithubMeta:
    def _repo_data(self):
        return {
            'html_url': 'https://github.com/owner/repo',
            'stargazers_count': 1000,
            'forks_count': 100,
            'open_issues_count': 5,
            'subscribers_count': 50,
            'language': 'Python',
            'topics': ['web', 'api'],
            'license': {'spdx_id': 'MIT', 'name': 'MIT License'},
            'description': 'A great project',
            'size': 5000,
            'default_branch': 'main',
            'has_wiki': True,
            'has_discussions': False,
            'archived': False,
            'fork': False,
            'private': False,
            'created_at': '2020-01-01T00:00:00Z',
            'pushed_at': '2025-01-01T00:00:00Z',
            'homepage': 'https://myproject.com',
        }

    @patch('apps.analysis.github_meta.requests.get')
    def test_full_meta_returned(self, mock_get):
        repo_resp = _mock_response(200, self._repo_data())
        pr_resp = _mock_response(200, [], headers={})
        contrib_resp = _mock_response(200, [])
        feature_resp = _mock_response(200, [])
        pr_issues_resp = _mock_response(200, [])
        releases_resp = _mock_response(200, [], headers={})
        lang_resp = _mock_response(200, {'Python': 90000})
        mock_get.side_effect = [repo_resp, pr_resp, contrib_resp, feature_resp, pr_issues_resp, releases_resp, lang_resp]
        result = fetch_github_meta('owner', 'repo', token='tok')
        assert result['stars'] == 1000
        assert result['primary_language'] == 'Python'
        assert result['archived'] is False

    @patch('apps.analysis.github_meta.requests.get')
    def test_non_200_returns_empty(self, mock_get):
        mock_get.return_value = _mock_response(404)
        result = fetch_github_meta('owner', 'repo')
        assert result == {}

    @patch('apps.analysis.github_meta.requests.get')
    def test_exception_returns_empty(self, mock_get):
        mock_get.side_effect = Exception('network error')
        result = fetch_github_meta('owner', 'repo')
        assert result == {}

    @patch('apps.analysis.github_meta.requests.get')
    def test_pr_count_from_link_header(self, mock_get):
        repo_resp = _mock_response(200, self._repo_data())
        pr_resp = _mock_response(200, [{'id': 1}], headers={'Link': '<url?page=5>; rel="last"'})
        # remaining calls return empty
        mock_get.side_effect = [repo_resp, pr_resp] + [_mock_response(200, [], headers={})] * 10
        result = fetch_github_meta('owner', 'repo', token='tok')
        assert result['open_prs'] == 5

    @patch('apps.analysis.github_meta.requests.get')
    def test_pr_count_from_list_when_no_link(self, mock_get):
        repo_resp = _mock_response(200, self._repo_data())
        pr_resp = _mock_response(200, [{'id': 1}, {'id': 2}], headers={})
        mock_get.side_effect = [repo_resp, pr_resp] + [_mock_response(200, [], headers={})] * 10
        result = fetch_github_meta('owner', 'repo', token='tok')
        assert result['open_prs'] == 2

    @patch('apps.analysis.github_meta.requests.get')
    def test_no_license(self, mock_get):
        data = self._repo_data()
        data['license'] = None
        repo_resp = _mock_response(200, data)
        mock_get.side_effect = [repo_resp] + [_mock_response(200, [], headers={})] * 10
        result = fetch_github_meta('owner', 'repo', token='tok')
        assert result['license_spdx'] is None
