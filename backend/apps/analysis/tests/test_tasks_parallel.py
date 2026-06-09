import pytest

from apps.analysis.tasks import _compute_run_diff, _compute_similar_runs
from apps.repositories.models import AnalysisRun, Repository


@pytest.mark.django_db
class TestTailHelpers:
    def test_compute_run_diff_no_previous(self):
        repo = Repository.objects.create(
            url='https://github.com/a/b', owner='a', name='b',
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed')
        result = {'commits': {'total_commits': 1}}
        assert _compute_run_diff(run, result) == {'available': False}

    def test_compute_similar_runs_empty_when_no_candidates(self):
        repo = Repository.objects.create(
            url='https://github.com/a/b', owner='a', name='b',
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed')
        result = {'oss_score': {'score': 7.0}, 'github_meta': {'primary_language': 'Python'}}
        assert _compute_similar_runs(run, result) == []
