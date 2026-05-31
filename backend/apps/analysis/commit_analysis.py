import collections
from datetime import datetime, timedelta, timezone

from git import Repo


def analyze_commits(repo: Repo) -> dict:
    now = datetime.now(timezone.utc)
    commits = list(repo.iter_commits('HEAD'))

    # Weekly/monthly frequency (last 2 years)
    cutoff = now - timedelta(days=730)
    weekly: dict[str, int] = collections.defaultdict(int)
    monthly: dict[str, int] = collections.defaultdict(int)
    contributors: set[str] = set()
    contributor_by_period: dict[str, set] = collections.defaultdict(set)

    recent_90 = 0
    prior_90 = 0
    last_commit_date = None

    monthly_commits: dict[str, list] = collections.defaultdict(list)
    reverted_commits: list[dict] = []

    for commit in commits:
        dt = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
        if last_commit_date is None:
            last_commit_date = dt.isoformat()

        author = commit.author.email or commit.author.name
        contributors.add(author)

        if dt >= cutoff:
            week_key = dt.strftime('%Y-W%W')
            month_key = dt.strftime('%Y-%m')
            weekly[week_key] += 1
            monthly[month_key] += 1
            contributor_by_period[month_key].add(author)
            if len(monthly_commits[month_key]) < 30:
                monthly_commits[month_key].append({
                    'sha': commit.hexsha[:7],
                    'message': commit.message.split('\n')[0][:80],
                    'author': commit.author.name or commit.author.email,
                    'date': dt.date().isoformat(),
                })

        if len(reverted_commits) < 100 and commit.message.strip().startswith('Revert '):
            try:
                files = list(commit.stats.files.keys())[:10]
            except Exception:
                files = []
            reverted_commits.append({
                'sha': commit.hexsha[:7],
                'message': commit.message.split('\n')[0][:120],
                'date': dt.date().isoformat(),
                'files': files,
            })

        delta = now - dt
        if delta.days <= 90:
            recent_90 += 1
        elif delta.days <= 180:
            prior_90 += 1

    activity_decay = round(recent_90 / max(prior_90, 1), 3)
    days_since_last = (
        (now - datetime.fromtimestamp(commits[0].committed_date, tz=timezone.utc)).days
        if commits
        else None
    )
    abandoned = days_since_last is not None and days_since_last > 365

    # Contributor churn per month
    months = sorted(contributor_by_period.keys())
    churn = []
    for i, m in enumerate(months):
        prev = contributor_by_period[months[i - 1]] if i > 0 else set()
        curr = contributor_by_period[m]
        churn.append(
            {
                'month': m,
                'active': len(curr),
                'new': len(curr - prev),
                'lost': len(prev - curr),
            }
        )

    return {
        'total_commits': len(commits),
        'total_contributors': len(contributors),
        'last_commit_date': last_commit_date,
        'days_since_last_commit': days_since_last,
        'abandoned': abandoned,
        'activity_decay_ratio': activity_decay,
        'weekly_frequency': [{'week': k, 'count': v} for k, v in sorted(weekly.items())],
        'monthly_frequency': [{'month': k, 'count': v} for k, v in sorted(monthly.items())],
        'contributor_churn': churn,
        'monthly_commits': dict(monthly_commits),
        'reverted_commits': reverted_commits,
    }
