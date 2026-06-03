"""Contributors endpoint tests — mocks filesystem and git log."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client


def _make_md(frontmatter: str, body: str) -> str:
    return f"---\n{frontmatter}\n---\n{body}"


@pytest.fixture
def git_stats():
    return {
        'alice@example.com': {
            'name': 'Alice',
            'email': 'alice@example.com',
            'lines_added': 500,
            'lines_removed': 100,
            'commit_count': 40,
            'contrib_only_lines': 0,
        },
        'bob@example.com': {
            'name': 'Bob',
            'email': 'bob@example.com',
            'lines_added': 200,
            'lines_removed': 50,
            'commit_count': 15,
            'contrib_only_lines': 5,
        },
    }


@pytest.mark.django_db
class TestListContributors:
    def test_missing_contributors_dir_returns_empty(self, db):
        with patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR') as mock_dir:
            mock_dir.exists.return_value = False
            resp = Client().get('/api/v1/contributors/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['items'] == []
        assert data['total'] == 0

    def test_contributor_with_frontmatter_email(self, git_stats, tmp_path):
        md_file = tmp_path / 'alice.md'
        md_file.write_text(
            _make_md('git_emails: alice@example.com', 'Alice is a core contributor.'),
            encoding='utf-8',
        )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=git_stats),
        ):
            resp = Client().get('/api/v1/contributors/')

        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1
        item = data['items'][0]
        assert item['username'] == 'alice'
        assert item['commit_count'] == 40
        assert item['lines_added'] == 500

    def test_contributor_with_legacy_git_email(self, git_stats, tmp_path):
        md_file = tmp_path / 'bob.md'
        md_file.write_text(
            _make_md('git_email: bob@example.com', 'Bob contributes here.'),
            encoding='utf-8',
        )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=git_stats),
        ):
            resp = Client().get('/api/v1/contributors/')

        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1
        assert data['items'][0]['username'] == 'bob'

    def test_contributor_no_frontmatter_falls_back_to_username_match(self, git_stats, tmp_path):
        md_file = tmp_path / 'alice.md'
        md_file.write_text('Alice is a contributor.', encoding='utf-8')

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=git_stats),
        ):
            resp = Client().get('/api/v1/contributors/')

        assert resp.status_code == 200
        assert resp.json()['total'] == 1

    def test_contributor_no_matching_stats_excluded(self, tmp_path):
        md_file = tmp_path / 'unknown.md'
        md_file.write_text(
            _make_md('git_emails: nobody@nowhere.com', 'No match.'),
            encoding='utf-8',
        )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value={}),
        ):
            resp = Client().get('/api/v1/contributors/')

        assert resp.status_code == 200
        assert resp.json()['total'] == 0

    def test_filter_by_q(self, git_stats, tmp_path):
        (tmp_path / 'alice.md').write_text(
            _make_md('git_emails: alice@example.com', 'Alice works on frontend.'),
            encoding='utf-8',
        )
        (tmp_path / 'bob.md').write_text(
            _make_md('git_email: bob@example.com', 'Bob works on backend.'),
            encoding='utf-8',
        )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=git_stats),
        ):
            resp = Client().get('/api/v1/contributors/', {'q': 'frontend'})

        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1
        assert data['items'][0]['username'] == 'alice'

    def test_pagination(self, tmp_path):
        stats = {}
        for i in range(25):
            email = f'user{i}@example.com'
            stats[email] = {
                'name': f'User{i}',
                'email': email,
                'lines_added': 100,
                'lines_removed': 10,
                'commit_count': 5,
                'contrib_only_lines': 0,
            }
            (tmp_path / f'user{i}.md').write_text(
                _make_md(f'git_emails: {email}', f'User {i} bio.'),
                encoding='utf-8',
            )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=stats),
        ):
            resp_p1 = Client().get('/api/v1/contributors/', {'page': 1, 'per_page': 10})
            resp_p2 = Client().get('/api/v1/contributors/', {'page': 2, 'per_page': 10})

        assert resp_p1.status_code == 200
        assert resp_p2.status_code == 200
        d1 = resp_p1.json()
        d2 = resp_p2.json()
        assert d1['total'] == 25
        assert len(d1['items']) == 10
        assert len(d2['items']) == 10
        assert d1['items'][0]['username'] != d2['items'][0]['username']

    def test_per_page_capped_at_50(self, git_stats, tmp_path):
        (tmp_path / 'alice.md').write_text(
            _make_md('git_emails: alice@example.com', 'Alice.'),
            encoding='utf-8',
        )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=git_stats),
        ):
            resp = Client().get('/api/v1/contributors/', {'per_page': 200})

        assert resp.status_code == 200
        assert resp.json()['per_page'] == 50

    def test_bio_truncated_if_too_long(self, git_stats, tmp_path):
        long_bio = 'word ' * 200
        (tmp_path / 'alice.md').write_text(
            _make_md('git_emails: alice@example.com', long_bio),
            encoding='utf-8',
        )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=git_stats),
        ):
            resp = Client().get('/api/v1/contributors/')

        item = resp.json()['items'][0]
        assert item['bio_md'].endswith('…')
        assert len(item['bio_md']) <= 510

    def test_multiple_emails_stats_merged(self, tmp_path):
        stats = {
            'alice1@example.com': {
                'name': 'Alice',
                'email': 'alice1@example.com',
                'lines_added': 300,
                'lines_removed': 50,
                'commit_count': 20,
                'contrib_only_lines': 0,
            },
            'alice2@example.com': {
                'name': 'Alice Alt',
                'email': 'alice2@example.com',
                'lines_added': 200,
                'lines_removed': 30,
                'commit_count': 10,
                'contrib_only_lines': 0,
            },
        }
        (tmp_path / 'alice.md').write_text(
            _make_md('git_emails: alice1@example.com, alice2@example.com', 'Alice.'),
            encoding='utf-8',
        )

        with (
            patch('apps.repositories.router_contributors._CONTRIBUTORS_DIR', tmp_path),
            patch('apps.repositories.router_contributors._parse_git_log', return_value=stats),
        ):
            resp = Client().get('/api/v1/contributors/')

        item = resp.json()['items'][0]
        assert item['lines_added'] == 500
        assert item['commit_count'] == 30


@pytest.mark.django_db
class TestParseGitLog:
    def test_uses_cache_file_if_present(self, tmp_path):
        cache_data = {
            'dev@test.com': {
                'name': 'Dev',
                'email': 'dev@test.com',
                'lines_added': 100,
                'lines_removed': 10,
                'commit_count': 5,
                'contrib_only_lines': 0,
            }
        }
        cache_file = tmp_path / 'contributors_stats.json'
        cache_file.write_text(json.dumps(cache_data))

        with patch('apps.repositories.router_contributors._STATS_CACHE', cache_file):
            from apps.repositories.router_contributors import _parse_git_log
            result = _parse_git_log()

        assert 'dev@test.com' in result
        assert result['dev@test.com']['commit_count'] == 5

    def test_malformed_cache_falls_back_to_git(self, tmp_path):
        bad_cache = tmp_path / 'contributors_stats.json'
        bad_cache.write_text('not valid json')

        with (
            patch('apps.repositories.router_contributors._STATS_CACHE', bad_cache),
            patch('subprocess.check_output') as mock_git,
        ):
            mock_git.return_value = (
                'COMMIT\talice@x.com\tAlice\n'
                '10\t2\tsrc/app.py\n'
            )
            from apps.repositories.router_contributors import _parse_git_log
            result = _parse_git_log()

        assert 'alice@x.com' in result
        assert result['alice@x.com']['lines_added'] == 10
