"""
Integration tests for Celery tasks using CELERY_TASK_ALWAYS_EAGER=True.
Tests cover the periodic / beat tasks — not analyze_repository (which
requires git clone + network). That task is tested via its endpoint tests.
"""
import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.utils import timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def public_repo(db):
    from apps.repositories.models import Repository
    return Repository.objects.create(
        url='https://github.com/celery-test/pub',
        owner='celery-test',
        name='pub',
        last_commit_sha='abc123',
        is_private=False,
    )


@pytest.fixture
def completed_run_for_repo(public_repo):
    from apps.repositories.models import AnalysisRun
    return AnalysisRun.objects.create(
        repo=public_repo,
        status='completed',
        result={'oss_score': {'score': 7.0, 'badge': 'thriving', 'label': 'Thriving'}},
    )


# ---------------------------------------------------------------------------
# check_stale_repos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCheckStaleRepos:
    @override_settings(STALE_AFTER_DAYS=30, CELERY_TASK_ALWAYS_EAGER=True)
    @patch('apps.analysis.github_meta.fetch_latest_sha', return_value='new_sha')
    def test_marks_repo_stale_when_sha_changed(self, mock_sha, public_repo):
        from apps.analysis.tasks import check_stale_repos
        check_stale_repos()
        public_repo.refresh_from_db()
        assert public_repo.is_stale is True

    @override_settings(STALE_AFTER_DAYS=30, CELERY_TASK_ALWAYS_EAGER=True)
    @patch('apps.analysis.github_meta.fetch_latest_sha', return_value='abc123')
    def test_no_change_leaves_repo_fresh(self, mock_sha, public_repo):
        from apps.analysis.tasks import check_stale_repos
        check_stale_repos()
        public_repo.refresh_from_db()
        assert public_repo.is_stale is False

    @override_settings(STALE_AFTER_DAYS=30, CELERY_TASK_ALWAYS_EAGER=True)
    @patch('apps.analysis.github_meta.fetch_latest_sha', side_effect=Exception('network error'))
    def test_fetch_failure_does_not_crash(self, mock_sha, public_repo):
        from apps.analysis.tasks import check_stale_repos
        check_stale_repos()  # should not raise
        public_repo.refresh_from_db()
        assert public_repo.is_stale is False


# ---------------------------------------------------------------------------
# cleanup_old_runs
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCleanupOldRuns:
    @override_settings(RUNS_TO_KEEP_PER_REPO=2, CELERY_TASK_ALWAYS_EAGER=True)
    def test_keeps_only_configured_count(self, public_repo):
        from apps.repositories.models import AnalysisRun
        from apps.analysis.tasks import cleanup_old_runs
        runs = [
            AnalysisRun.objects.create(repo=public_repo, status='completed', result={})
            for _ in range(5)
        ]
        cleanup_old_runs()
        remaining = AnalysisRun.objects.filter(repo=public_repo).count()
        assert remaining <= 2

    @override_settings(RUNS_TO_KEEP_PER_REPO=5, CELERY_TASK_ALWAYS_EAGER=True)
    def test_does_not_delete_in_flight_runs(self, public_repo):
        from apps.repositories.models import AnalysisRun
        from apps.analysis.tasks import cleanup_old_runs
        # Create 6 old completed runs and 1 pending
        for _ in range(6):
            AnalysisRun.objects.create(repo=public_repo, status='completed', result={})
        pending = AnalysisRun.objects.create(repo=public_repo, status='pending')
        cleanup_old_runs()
        # Pending run must still exist
        assert AnalysisRun.objects.filter(id=pending.id).exists()

    @override_settings(RUNS_TO_KEEP_PER_REPO=10, CELERY_TASK_ALWAYS_EAGER=True)
    def test_no_op_when_few_runs(self, public_repo):
        from apps.repositories.models import AnalysisRun
        from apps.analysis.tasks import cleanup_old_runs
        AnalysisRun.objects.create(repo=public_repo, status='completed', result={})
        cleanup_old_runs()
        assert AnalysisRun.objects.filter(repo=public_repo).count() == 1


# ---------------------------------------------------------------------------
# cleanup_never_succeeded_repos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCleanupNeverSucceededRepos:
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_removes_repo_with_only_failed_run(self, db):
        from apps.repositories.models import AnalysisRun, Repository
        from apps.analysis.tasks import cleanup_never_succeeded_repos

        repo = Repository.objects.create(
            url='https://github.com/dead/repo',
            owner='dead',
            name='repo',
        )
        AnalysisRun.objects.create(repo=repo, status='failed')
        # Cleanup checks repo.created_at — backdate it to be old enough
        Repository.objects.filter(id=repo.id).update(
            created_at=timezone.now() - timedelta(hours=2)
        )
        cleanup_never_succeeded_repos()
        assert not Repository.objects.filter(id=repo.id).exists()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_keeps_repo_with_completed_run(self, db, public_repo, completed_run_for_repo):
        from apps.analysis.tasks import cleanup_never_succeeded_repos
        cleanup_never_succeeded_repos()
        # public_repo has a completed run — must survive
        from apps.repositories.models import Repository
        assert Repository.objects.filter(id=public_repo.id).exists()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_keeps_recent_failed_runs(self, db):
        from apps.repositories.models import AnalysisRun, Repository
        from apps.analysis.tasks import cleanup_never_succeeded_repos

        repo = Repository.objects.create(
            url='https://github.com/new-failed/repo',
            owner='new-failed',
            name='repo',
        )
        AnalysisRun.objects.create(repo=repo, status='failed')
        # triggered_at is recent (auto_now_add) — should NOT be deleted
        cleanup_never_succeeded_repos()
        assert Repository.objects.filter(id=repo.id).exists()


# ---------------------------------------------------------------------------
# select_repo_of_week
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSelectRepoOfWeek:
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_creates_spotlight_when_repos_available(self, public_repo, completed_run_for_repo):
        from apps.analysis.tasks import select_repo_of_week
        from apps.repositories.models import RepoOfTheWeek

        select_repo_of_week()
        assert RepoOfTheWeek.objects.count() == 1
        spot = RepoOfTheWeek.objects.first()
        assert spot.repo == public_repo
        assert spot.pick_number == 1

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_idempotent_for_same_week(self, public_repo, completed_run_for_repo):
        from apps.analysis.tasks import select_repo_of_week
        from apps.repositories.models import RepoOfTheWeek

        select_repo_of_week()
        select_repo_of_week()
        assert RepoOfTheWeek.objects.count() == 1

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_no_op_when_no_eligible_repos(self, db):
        from apps.analysis.tasks import select_repo_of_week
        from apps.repositories.models import RepoOfTheWeek

        select_repo_of_week()
        assert RepoOfTheWeek.objects.count() == 0

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_watches_new_spotlight_repo(self, public_repo, completed_run_for_repo):
        from apps.analysis.tasks import select_repo_of_week

        select_repo_of_week()
        public_repo.refresh_from_db()
        assert public_repo.is_watched is True
        assert public_repo.watch_reason == 'spotlight'

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_unwatches_previous_week_spotlight(self, public_repo, completed_run_for_repo, db):
        from datetime import date, timedelta

        from apps.analysis.tasks import select_repo_of_week
        from apps.repositories.models import AnalysisRun, RepoOfTheWeek, Repository

        other = Repository.objects.create(
            url='https://github.com/other/prev',
            owner='other',
            name='prev',
            is_watched=True,
            watch_reason='spotlight',
        )
        AnalysisRun.objects.create(repo=other, status='completed')
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        prev_week = week_start - timedelta(days=7)
        RepoOfTheWeek.objects.create(repo=other, week_start=prev_week, pick_number=1)

        select_repo_of_week()
        other.refresh_from_db()
        public_repo.refresh_from_db()
        assert other.is_watched is False
        assert public_repo.is_watched is True

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_preserves_manual_watch_on_unrelated_repo(self, public_repo, completed_run_for_repo, db):
        from apps.analysis.tasks import select_repo_of_week
        from apps.repositories.models import Repository

        manual = Repository.objects.create(
            url='https://github.com/manual/other',
            owner='manual',
            name='other',
            is_watched=True,
            watch_reason='manual',
        )

        select_repo_of_week()
        manual.refresh_from_db()
        assert manual.is_watched is True


# ---------------------------------------------------------------------------
# reanalyze_watched_repos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestReanalyzeWatchedRepos:
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('apps.analysis.tasks.analyze_repository')
    @patch('apps.analysis.github_meta.fetch_latest_sha', return_value='newsha999')
    def test_queues_run_when_sha_changed(self, mock_sha, mock_task, public_repo):
        from apps.repositories.models import AnalysisRun
        from apps.analysis.tasks import reanalyze_watched_repos

        mock_task.delay.return_value = MagicMock(id='watch-task')
        public_repo.is_watched = True
        public_repo.save(update_fields=['is_watched'])

        reanalyze_watched_repos()
        assert AnalysisRun.objects.filter(repo=public_repo, status='pending').exists()
        mock_task.delay.assert_called_once()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('apps.analysis.tasks.analyze_repository')
    @patch('apps.analysis.github_meta.fetch_latest_sha', return_value='abc123')
    def test_skips_unchanged_repo(self, mock_sha, mock_task, public_repo):
        from apps.repositories.models import AnalysisRun
        from apps.analysis.tasks import reanalyze_watched_repos

        public_repo.is_watched = True
        public_repo.last_analyzed_at = timezone.now()
        public_repo.save(update_fields=['is_watched', 'last_analyzed_at'])

        reanalyze_watched_repos()
        mock_task.delay.assert_not_called()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_no_op_when_no_watched_repos(self, db):
        from apps.analysis.tasks import reanalyze_watched_repos
        reanalyze_watched_repos()  # should not raise
