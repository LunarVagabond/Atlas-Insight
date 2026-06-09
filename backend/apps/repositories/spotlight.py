from __future__ import annotations

from datetime import date, timedelta

from apps.repositories.models import RepoOfTheWeek, Repository


def _current_week_start(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def sync_spotlight_watches(week_start: date | None = None) -> None:
    week_start = week_start or _current_week_start()
    current = (
        RepoOfTheWeek.objects.filter(week_start=week_start)
        .select_related('repo')
        .first()
    )
    current_repo_id = current.repo_id if current else None

    Repository.objects.filter(watch_reason='spotlight').exclude(pk=current_repo_id).update(
        is_watched=False,
        watch_reason='',
    )

    if current_repo_id:
        Repository.objects.filter(pk=current_repo_id).update(
            is_watched=True,
            watch_reason='spotlight',
        )


def apply_spotlight_watch_rollover(
    new_repo: Repository,
    week_start: date,
    *,
    replaced_repo: Repository | None = None,
) -> None:
    del replaced_repo
    sync_spotlight_watches(week_start)
