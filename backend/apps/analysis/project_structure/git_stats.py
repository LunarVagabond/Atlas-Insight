import collections
from datetime import datetime, timezone

from git import Repo


def get_releases(repo_obj: Repo) -> tuple[int, list[dict]]:
    try:
        tags = sorted(repo_obj.tags, key=lambda t: t.commit.committed_date, reverse=True)
        recent = [
            {
                'name': t.name,
                'date': datetime.fromtimestamp(
                    t.commit.committed_date, tz=timezone.utc
                ).isoformat(),
            }
            for t in tags[:20]
        ]
        return len(tags), recent
    except Exception:
        return 0, []


def get_repo_age(repo_obj: Repo) -> int | None:
    try:
        count_str = repo_obj.git.rev_list('HEAD', '--count', '--first-parent')
        total = int(count_str.strip())
        skip = max(0, total - 1)
        ts_str = repo_obj.git.log(f'--skip={skip}', '-1', '--format=%ct', 'HEAD', '--first-parent')
        if ts_str.strip():
            first_date = datetime.fromtimestamp(int(ts_str.strip()), tz=timezone.utc)
            return (datetime.now(timezone.utc) - first_date).days
    except Exception:
        pass
    return None


def compute_bus_factor(repo_obj: Repo) -> tuple[int, list[dict]]:
    author_files: dict[str, set] = collections.defaultdict(set)
    email_to_name: dict[str, str] = {}
    try:
        output = repo_obj.git.log('--format=AUTHOR:%ae|%an', '--name-only', '-300', 'HEAD')
        current_author: str | None = None
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('AUTHOR:'):
                parts = line[7:].split('|', 1)
                current_author = parts[0]
                if current_author and len(parts) > 1 and parts[1]:
                    email_to_name[current_author] = parts[1]
            elif current_author:
                author_files[current_author].add(line)
    except Exception:
        return 1, []

    if not author_files:
        return 1, []

    all_files: set[str] = set()
    for files in author_files.values():
        all_files.update(files)

    sorted_authors = sorted(author_files.items(), key=lambda x: -len(x[1]))
    top_contributors = [
        {
            'author': email_to_name.get(a, a),
            'email': a,
            'files_touched': len(f),
        }
        for a, f in sorted_authors[:10]
    ]

    total_authors = len(author_files)
    target = len(all_files) * 0.8
    covered: set[str] = set()
    bus_factor = 0
    for author, files in sorted_authors:
        covered.update(files)
        bus_factor += 1
        if len(covered) >= target:
            break

    return min(max(1, bus_factor), total_authors), top_contributors


def get_hot_files(repo_obj: Repo) -> list[dict]:
    file_counts: dict[str, int] = collections.Counter()
    try:
        output = repo_obj.git.log('--format=', '--name-only', '-300', 'HEAD')
        for line in output.splitlines():
            line = line.strip()
            if line:
                file_counts[line] += 1
    except Exception:
        return []
    return [{'file': f, 'commit_count': c} for f, c in file_counts.most_common(20)]
