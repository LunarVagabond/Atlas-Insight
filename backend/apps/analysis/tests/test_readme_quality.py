from apps.analysis.readme_quality import score_readme_quality


class TestScoreReadmeQuality:
    def test_missing_readme(self):
        result = score_readme_quality({'found': False}, {})
        assert result['score'] == 0.0
        assert any(r['status'] == 'missing' for r in result['recommendations'])

    def test_good_readme_high_score(self):
        readme = {
            'found': True,
            'word_count': 500,
            'description': 'A great project.',
            'has_installation': True,
            'has_usage': True,
            'has_contributing': True,
            'has_changelog': True,
            'has_license': True,
            'has_api_docs': True,
            'code_block_count': 3,
            'shallow_sections': [],
            'docs_links': [{'label': 'Docs', 'url': 'https://example.com/docs'}],
            'social_links': [{'platform': 'Discord', 'label': 'Chat', 'url': 'https://discord.gg/x'}],
        }
        structure = {'has_contributing': True, 'has_changelog': True, 'license_type': 'MIT'}
        result = score_readme_quality(readme, structure, scoring_mode='oss')
        assert result['score'] >= 90
        assert result['potential_score'] >= result['score']

    def test_closed_source_skips_community_recs(self):
        readme = {
            'found': True,
            'word_count': 200,
            'description': 'Internal tool.',
            'has_installation': True,
            'has_usage': True,
            'code_block_count': 1,
            'has_external_links': True,
        }
        result = score_readme_quality(readme, {}, scoring_mode='closed_source')
        ids = [r['id'] for r in result['recommendations']]
        assert 'readme_contributing' not in ids
        assert 'readme_license' not in ids

    def test_potential_includes_score_gains(self):
        readme = {'found': False}
        result = score_readme_quality(readme, {}, scoring_mode='oss')
        gain = sum(r['score_gain'] for r in result['recommendations'])
        assert result['potential_score'] == round(min(100.0, result['score'] + gain), 1)
