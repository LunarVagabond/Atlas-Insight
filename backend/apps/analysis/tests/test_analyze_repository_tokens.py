from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.repositories.models import AnalysisRun, Repository

User = get_user_model()


@pytest.fixture
def private_repo(db):
    return Repository.objects.create(
        url='https://github.com/LunarVagabond/Polycore-Exchange',
        owner='LunarVagabond',
        name='Polycore-Exchange',
        is_private=True,
    )


@pytest.fixture
def user_with_github(db):
    return User.objects.create_user(username='ghuser', password='pass')


@pytest.mark.django_db
class TestAnalyzeRepositoryTokenResolution:
    @patch('apps.analysis.tasks.clone_or_fetch')
    @patch('apps.analysis.tasks._extract_run_fields')
    @patch('apps.analysis.tasks.fetch_github_meta')
    @patch('apps.analysis.tasks.analyze_commits')
    @patch('apps.analysis.tasks.parse_readme')
    @patch('apps.analysis.tasks.detect_docs_only', return_value=True)
    @patch('apps.analysis.tasks.analyze_structure')
    @patch('apps.analysis.tasks.scan_security')
    @patch('apps.analysis.tasks.classify_repo')
    @patch('apps.analysis.tasks.compute_oss_score')
    @patch('apps.analysis.tasks.score_readme_quality')
    @patch('apps.analysis.tasks.score_community_files')
    def test_uses_oauth_when_repo_has_no_stored_token(
        self,
        mock_community,
        mock_readme_q,
        mock_oss,
        mock_classify,
        mock_security,
        mock_structure,
        mock_docs_only,
        mock_readme,
        mock_commits,
        mock_meta,
        mock_extract,
        mock_clone,
        private_repo,
        user_with_github,
    ):
        mock_repo = MagicMock()
        mock_repo.working_dir = '/tmp/fake-repo'
        mock_repo.head.commit.hexsha = 'abc123'
        mock_clone.return_value = (mock_repo, 'abc123', timezone.now())

        mock_commits.return_value = {'total': 0, 'weekly_frequency': [], 'monthly_frequency': [], 'contributor_churn': []}
        mock_readme.return_value = {'content': '', 'sections': {}}
        mock_structure.return_value = {'languages': [], 'release_count': 0}
        mock_security.return_value = {'vulnerabilities': []}
        mock_meta.return_value = {'is_private': True, 'github_languages': []}
        mock_classify.return_value = {}
        mock_oss.return_value = {'score': 1, 'badge': 'nascent', 'label': 'Nascent'}
        mock_readme_q.return_value = {'score': 0}
        mock_community.return_value = {}

        run = AnalysisRun.objects.create(
            repo=private_repo,
            user=user_with_github,
            status='pending',
        )

        with patch(
            'apps.repositories.github_tokens.get_github_oauth_token',
            return_value='gho_oauth_token',
        ) as mock_oauth:
            from apps.analysis.tasks import analyze_repository
            analyze_repository(str(run.id))

        mock_oauth.assert_called_once_with(user_with_github)
        mock_clone.assert_called_once()
        assert mock_clone.call_args.kwargs['pat'] == 'gho_oauth_token'

        private_repo.refresh_from_db()
        assert private_repo.auth_token == ''

        run.refresh_from_db()
        assert run.status == 'completed'
