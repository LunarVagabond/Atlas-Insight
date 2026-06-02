from datetime import datetime, timezone

from git import Repo

STALE_BRANCH_DAYS = 90


def detect_stale_branches(repo_obj: Repo) -> tuple[list[dict], int]:
    now = datetime.now(tz=timezone.utc)
    stale: list[dict] = []
    try:
        for ref in repo_obj.remote().refs:
            branch_name = ref.name
            if branch_name.endswith('/HEAD'):
                continue
            try:
                commit = ref.commit
                committed_dt = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
                days_ago = (now - committed_dt).days
                if days_ago >= STALE_BRANCH_DAYS:
                    stale.append({
                        'name': branch_name.split('/', 1)[-1],
                        'last_commit': committed_dt.isoformat(),
                        'days_ago': days_ago,
                    })
            except Exception:
                continue
    except Exception:
        pass
    stale.sort(key=lambda b: -b['days_ago'])
    return stale, len(stale)
