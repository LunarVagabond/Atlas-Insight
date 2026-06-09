import pytest

from apps.analysis.scoring_mode import infer_scoring_mode


class TestInferScoringMode:
    def test_private_repo_is_closed_source(self):
        mode, reason = infer_scoring_mode(is_private=True)
        assert mode == 'closed_source'
        assert 'private' in reason

    def test_github_meta_private(self):
        mode, _ = infer_scoring_mode(github_meta={'is_private': True})
        assert mode == 'closed_source'

    def test_public_with_license_and_contributing_is_oss(self):
        mode, reason = infer_scoring_mode(
            structure={'license_file': 'LICENSE', 'has_contributing': True},
        )
        assert mode == 'oss'
        assert 'open-source' in reason

    def test_public_with_osi_license_is_oss(self):
        mode, _ = infer_scoring_mode(github_meta={'license_spdx': 'MIT'})
        assert mode == 'oss'

    def test_uncertain_public_defaults_closed_source(self):
        mode, reason = infer_scoring_mode(
            is_private=False,
            github_meta={'is_private': False},
            structure={},
        )
        assert mode == 'closed_source'
        assert 'without clear open-source' in reason
