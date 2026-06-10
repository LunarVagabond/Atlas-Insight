from datetime import datetime, timedelta, timezone

from apps.analysis.commit_analysis import _build_contributor_stats


class _FakeStats:
    def __init__(self, insertions=0, deletions=0):
        self.total = {'insertions': insertions, 'deletions': deletions}
        self.files = {}


class _FakeAuthor:
    def __init__(self, name, email):
        self.name = name
        self.email = email


class _FakeCommit:
    def __init__(self, name, email, ts, insertions=0, deletions=0):
        self.author = _FakeAuthor(name, email)
        self.committed_date = ts
        self.stats = _FakeStats(insertions, deletions)


def _ts(days_ago: int) -> float:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.timestamp()


class TestBuildContributorStats:
    def test_aggregates_by_author(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=730)
        commits = [
            _FakeCommit('Alice', 'alice@example.com', _ts(10), 100, 20),
            _FakeCommit('Alice', 'alice@example.com', _ts(20), 50, 10),
            _FakeCommit('Bob', 'bob@example.com', _ts(15), 30, 5),
        ]
        stats = _build_contributor_stats(commits, cutoff)
        assert len(stats) == 2
        assert stats[0]['author'] == 'Alice'
        assert stats[0]['commits'] == 2
        assert stats[0]['lines_added'] == 150
        assert stats[0]['lines_removed'] == 30
        bob = next(s for s in stats if s['author'] == 'Bob')
        assert bob['commits'] == 1
        assert bob['lines_added'] == 30

    def test_monthly_buckets(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=730)
        month_a = datetime(2025, 4, 15, tzinfo=timezone.utc)
        month_b = datetime(2025, 6, 15, tzinfo=timezone.utc)
        commits = [
            _FakeCommit('Alice', 'alice@example.com', month_a.timestamp(), 10, 2),
            _FakeCommit('Alice', 'alice@example.com', month_b.timestamp(), 20, 4),
        ]
        stats = _build_contributor_stats(commits, cutoff)
        alice = stats[0]
        assert len(alice['monthly']) == 2
        month_keys = sorted(alice['monthly'].keys())
        assert month_keys == ['2025-04', '2025-06']
        assert alice['monthly'][month_keys[0]]['commits'] == 1
        assert alice['monthly'][month_keys[1]]['commits'] == 1

    def test_excludes_bots(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=730)
        commits = [
            _FakeCommit('dependabot[bot]', 'dependabot@users.noreply.github.com', _ts(5)),
            _FakeCommit('Human', 'human@example.com', _ts(5)),
        ]
        stats = _build_contributor_stats(commits, cutoff)
        assert len(stats) == 1
        assert stats[0]['author'] == 'Human'

    def test_excludes_before_cutoff(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=730)
        commits = [
            _FakeCommit('Old', 'old@example.com', _ts(800)),
            _FakeCommit('Recent', 'recent@example.com', _ts(10)),
        ]
        stats = _build_contributor_stats(commits, cutoff)
        assert len(stats) == 1
        assert stats[0]['author'] == 'Recent'
