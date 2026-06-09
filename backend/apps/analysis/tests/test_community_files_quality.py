from apps.analysis.community_files_quality import score_community_files


class TestScoreCommunityFiles:
    def test_oss_penalizes_missing_files(self):
        result = score_community_files({}, {}, scoring_mode='oss')
        assert result['score'] == 0.0
        assert len(result['recommendations']) == 6
        assert all(r['status'] == 'missing' for r in result['recommendations'])
        assert len(result['breakdown']) == 6

    def test_breakdown_sorted_by_gap(self):
        readme = {'found': True, 'word_count': 500}
        structure = {
            'license_type': 'MIT',
            'has_contributing': True,
            'community_files_content': {
                'contributing': ' '.join(['word'] * 100),
            },
        }
        result = score_community_files(
            readme, structure, scoring_mode='oss', readme_quality_score=80.0,
        )
        gaps = [f['gap'] for f in result['breakdown']]
        assert gaps == sorted(gaps, reverse=True)
        readme_entry = next(f for f in result['files'] if f['key'] == 'readme')
        assert readme_entry['weight'] == 0.25
        assert readme_entry['weighted_score'] == 20.0

    def test_closed_source_skips_missing_penalty(self):
        result = score_community_files({}, {}, scoring_mode='closed_source')
        assert result['score'] == 0.0
        assert result['recommendations'] == []

    def test_scores_present_files_closed_source(self):
        structure = {
            'has_contributing': True,
            'contributing_file': 'CONTRIBUTING.md',
            'community_files_content': {
                'contributing': ' '.join(['word'] * 100),
            },
        }
        result = score_community_files({}, structure, scoring_mode='closed_source')
        assert result['score'] > 0
        contrib = next(f for f in result['files'] if f['key'] == 'contributing')
        assert contrib['present'] is True
        assert contrib['score'] == 100.0

    def test_shallow_file_needs_improvement(self):
        structure = {
            'has_contributing': True,
            'community_files_content': {'contributing': 'short text'},
        }
        result = score_community_files({}, structure, scoring_mode='oss')
        assert any(r['status'] == 'needs_improvement' for r in result['recommendations'])
