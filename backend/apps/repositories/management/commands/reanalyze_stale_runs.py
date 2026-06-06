"""Re-queue completed AnalysisRun records that are missing data from schema migration 0020.

Migration 0020 split the monolithic `result` JSONField into per-module columns.
Completed runs created before that migration have null for all data columns and
must be re-analyzed to populate them.

Usage:
    python manage.py reanalyze_stale_runs [--dry-run] [--limit N]
"""
from django.core.management.base import BaseCommand

from apps.analysis.tasks import analyze_repository
from apps.repositories.models import AnalysisRun


class Command(BaseCommand):
    help = 'Re-queue completed runs missing data after schema migration 0020'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='List stale runs without queuing')
        parser.add_argument('--limit', type=int, default=100, help='Max runs to process (default 100)')

    def handle(self, *args, **options):
        stale = (
            AnalysisRun.objects
            .filter(status='completed', commits_data__isnull=True, error_message__isnull=True)
            .select_related('repo')
            .order_by('-triggered_at')
        )[:options['limit']]

        count = len(stale)
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No stale runs found.'))
            return

        self.stdout.write(f'Found {count} stale completed run{"s" if count != 1 else ""}')

        if options['dry_run']:
            for run in stale:
                self.stdout.write(f'  {run.repo}  run={run.pk}  triggered={run.triggered_at:%Y-%m-%d %H:%M}')
            self.stdout.write(self.style.WARNING('Dry run — nothing queued.'))
            return

        queued = 0
        for run in stale:
            run.status = 'pending'
            run.progress_step = ''
            run.error_message = None
            run.save(update_fields=['status', 'progress_step', 'error_message'])
            analyze_repository.delay(str(run.pk))
            self.stdout.write(f'  Queued: {run.repo}  run={run.pk}')
            queued += 1

        self.stdout.write(self.style.SUCCESS(f'Queued {queued} run{"s" if queued != 1 else ""} for re-analysis.'))
