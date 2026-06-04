import tempfile
from pathlib import Path

import pytest
from apps.analysis.readme_parser import (
    _dedupe_link_dicts,
    _detect_docs_links,
    _detect_social_links,
    _extract_description,
    _extract_links,
    parse_readme,
)


class TestParseReadme:
    def test_no_readme(self):
        with tempfile.TemporaryDirectory() as d:
            result = parse_readme(d)
        assert result['found'] is False
        assert result['filename'] is None
        assert result['content'] is None
        assert result['sections'] == []

    def test_finds_readme_md(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('# Hello\nSome text here.')
            result = parse_readme(d)
        assert result['found'] is True
        assert result['filename'] == 'README.md'

    def test_finds_lowercase_readme(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'readme.md').write_text('# Hello\nText.')
            result = parse_readme(d)
        assert result['found'] is True

    def test_word_count(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('one two three four five')
            result = parse_readme(d)
        assert result['word_count'] == 5

    def test_badge_count(self):
        with tempfile.TemporaryDirectory() as d:
            content = '[![Build](img)](url)\n[![Tests](img)](url)'
            (Path(d) / 'README.md').write_text(content)
            result = parse_readme(d)
        assert result['badge_count'] == 2

    def test_has_installation(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('## Installation\nnpm install')
            result = parse_readme(d)
        assert result['has_installation'] is True

    def test_has_usage(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('## Usage\nRun the app.')
            result = parse_readme(d)
        assert result['has_usage'] is True

    def test_has_contributing(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('## Contributing\nPRs welcome.')
            result = parse_readme(d)
        assert result['has_contributing'] is True

    def test_has_changelog(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('## Changelog\nv1.0: initial release')
            result = parse_readme(d)
        assert result['has_changelog'] is True

    def test_has_license(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('## License\nMIT')
            result = parse_readme(d)
        assert result['has_license'] is True

    def test_has_api_docs(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'README.md').write_text('## API\nEndpoints described here.')
            result = parse_readme(d)
        assert result['has_api_docs'] is True

    def test_sections_extracted(self):
        with tempfile.TemporaryDirectory() as d:
            content = '# Title\n## Install\n## Usage\n'
            (Path(d) / 'README.md').write_text(content)
            result = parse_readme(d)
        assert 'Title' in result['sections']
        assert 'Install' in result['sections']

    def test_content_truncated_at_50k(self):
        with tempfile.TemporaryDirectory() as d:
            content = 'x' * 100_000
            (Path(d) / 'README.md').write_text(content)
            result = parse_readme(d)
        assert len(result['content']) == 50_000

    def test_docs_links_detected(self):
        with tempfile.TemporaryDirectory() as d:
            content = 'See [docs](https://myproject.readthedocs.io/en/latest/)'
            (Path(d) / 'README.md').write_text(content)
            result = parse_readme(d)
        assert len(result['docs_links']) >= 1
        assert result['docs_links'][0]['label'] == 'Read the Docs'

    def test_social_links_detected(self):
        with tempfile.TemporaryDirectory() as d:
            content = 'Join us at https://discord.gg/abc123'
            (Path(d) / 'README.md').write_text(content)
            result = parse_readme(d)
        assert len(result['social_links']) >= 1
        assert result['social_links'][0]['platform'] == 'Discord'


class TestExtractDescription:
    def test_returns_first_paragraph(self):
        content = '# Title\n\nThis is the description paragraph.\n\n## Section\n'
        result = _extract_description(content)
        assert result == 'This is the description paragraph.'

    def test_skips_badges(self):
        content = '[![badge](img)](url)\n\nReal description here.\n'
        result = _extract_description(content)
        assert result == 'Real description here.'

    def test_returns_none_for_empty(self):
        assert _extract_description('# Only heading\n') is None

    def test_truncates_long_description(self):
        content = 'A' * 400 + '.'
        result = _extract_description(content)
        assert len(result) <= 360

    def test_truncates_at_sentence(self):
        content = 'First sentence. ' + 'B' * 300 + '.'
        result = _extract_description(content)
        assert result.endswith('.')

    def test_adds_ellipsis_when_no_sentence(self):
        content = 'A' * 400
        result = _extract_description(content)
        assert result.endswith('…')

    def test_multi_line_paragraph(self):
        content = 'Line one\nLine two\nLine three\n'
        result = _extract_description(content)
        assert 'Line one' in result
        assert 'Line two' in result


class TestExtractLinks:
    def test_markdown_links(self):
        content = 'See [docs](https://example.com/docs) for more.'
        links = _extract_links(content)
        assert 'https://example.com/docs' in links

    def test_bare_urls(self):
        content = 'Visit https://example.com for more.'
        links = _extract_links(content)
        assert 'https://example.com' in links

    def test_deduplicates(self):
        content = 'https://example.com https://example.com'
        links = _extract_links(content)
        assert links.count('https://example.com') == 1

    def test_ignores_non_http(self):
        content = 'See ftp://example.com or mailto:a@b.com'
        links = _extract_links(content)
        assert len(links) == 0

    def test_strips_trailing_punctuation(self):
        content = 'See https://example.com.'
        links = _extract_links(content)
        assert 'https://example.com' in links

    def test_caps_at_150(self):
        content = ' '.join(f'https://example.com/{i}' for i in range(200))
        links = _extract_links(content)
        assert len(links) == 150


class TestDetectDocLinks:
    def test_readthedocs(self):
        links = ['https://myproject.readthedocs.io']
        result = _detect_docs_links(links)
        assert result[0]['label'] == 'Read the Docs'

    def test_wiki(self):
        links = ['https://github.com/user/repo/wiki']
        result = _detect_docs_links(links)
        assert result[0]['label'] == 'Wiki'

    def test_no_match(self):
        links = ['https://github.com/user/repo']
        result = _detect_docs_links(links)
        assert result == []


class TestDetectSocialLinks:
    def test_discord(self):
        links = ['https://discord.gg/abc123']
        result = _detect_social_links(links)
        assert result[0]['platform'] == 'Discord'

    def test_slack(self):
        links = ['https://myteam.slack.com']
        result = _detect_social_links(links)
        assert result[0]['platform'] == 'Slack'

    def test_twitter(self):
        links = ['https://twitter.com/myproject']
        result = _detect_social_links(links)
        assert result[0]['platform'] == 'X'

    def test_youtube(self):
        links = ['https://youtube.com/watch?v=abc']
        result = _detect_social_links(links)
        assert result[0]['platform'] == 'YouTube'

    def test_no_match(self):
        links = ['https://github.com/user/repo']
        result = _detect_social_links(links)
        assert result == []


class TestDedupeLinkDicts:
    def test_deduplicates_by_url(self):
        items = [
            {'url': 'https://a.com', 'label': 'A'},
            {'url': 'https://a.com', 'label': 'A2'},
        ]
        result = _dedupe_link_dicts(items)
        assert len(result) == 1

    def test_skips_non_string_url(self):
        items = [{'url': None, 'label': 'X'}, {'url': 'https://b.com', 'label': 'B'}]
        result = _dedupe_link_dicts(items)
        assert len(result) == 1
        assert result[0]['url'] == 'https://b.com'
