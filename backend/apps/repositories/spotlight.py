from __future__ import annotations

from datetime import date, timedelta

from apps.repositories.models import RepoOfTheWeek, Repository


def apply_spotlight_watch_rollover(
    new_repo: Repository,
    week_start: date,
    *,
    replaced_repo: Repository | None = None,
) -> None:
    to_unwatch: set = set()

    prev_pick = (
        RepoOfTheWeek.objects.filter(week_start=week_start - timedelta(days=7))
        .select_related('repo')
        .first()
    )
    if prev_pick and prev_pick.repo_id != new_repo.pk:
        to_unwatch.add(prev_pick.repo_id)

    if replaced_repo and replaced_repo.pk != new_repo.pk:
        to_unwatch.add(replaced_repo.pk)

    if to_unwatch:
        Repository.objects.filter(pk__in=to_unwatch, is_watched=True).update(is_watched=False)

    if not new_repo.is_watched:
        Repository.objects.filter(pk=new_repo.pk).update(is_watched=True)
        new_repo.is_watched = True
