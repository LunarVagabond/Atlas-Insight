import collections
import re
from datetime import datetime, timezone

from git import Repo

_BOT_RE = re.compile(r'\[bot\]|dependabot|github-actions|renovate|snyk-bot|codecov', re.IGNORECASE)


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
    # Keyed by lowercased display name — deduplicates same person with multiple emails
    author_files: dict[str, set] = collections.defaultdict(set)
    name_display: dict[str, str] = {}  # canonical display name (first seen)
    name_email: dict[str, str] = {}    # one email per name (first seen)
    try:
        output = repo_obj.git.log('--format=AUTHOR:%ae|%an', '--name-only', '-300', 'HEAD')
        current_key: str | None = None
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('AUTHOR:'):
                parts = line[7:].split('|', 1)
                email = parts[0]
                name = parts[1] if len(parts) > 1 else email
                if _BOT_RE.search(email) or _BOT_RE.search(name):
                    current_key = None
                    continue
                current_key = name.lower() or email.lower()
                if current_key not in name_display:
                    name_display[current_key] = name
                    name_email[current_key] = email
            elif current_key:
                author_files[current_key].add(line)
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
            'author': name_display.get(k, k),
            'email': name_email.get(k, k),
            'files_touched': len(f),
        }
        for k, f in sorted_authors[:10]
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
