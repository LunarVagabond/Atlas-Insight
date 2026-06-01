from apps.analysis.heuristics import compute_heuristics, compute_oss_score


def _commits(**overrides):
    base = {
        'activity_decay_ratio': 1.0,
        'contributor_churn': [],
        'days_since_last_commit': 0,
        'abandoned': False,
        'total_commits': 100,
    }
    base.update(overrides)
    return base


def _graph(**overrides):
    base = {'node_count': 10, 'god_modules': [], 'cycle_count': 0}
    base.update(overrides)
    return base


def _deps(**overrides):
    base = {'dependency_count': 5, 'docker_issues': [], 'missing_lockfile_warnings': []}
    base.update(overrides)
    return base


class TestComputeHeuristics:
    def test_returns_list_of_signal_dicts(self):
        signals = compute_heuristics(_commits(), _graph(), _deps())
        assert isinstance(signals, list)
        assert len(signals) > 0
        for s in signals:
            assert 'signal' in s
            assert 'score' in s
            assert 0 <= s['score'] <= 100

    def test_active_repo_low_abandonment(self):
        signals = compute_heuristics(_commits(days_since_last_commit=0), _graph(), _deps())
        abandon = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert abandon['score'] == 0

    def test_old_repo_high_abandonment(self):
        signals = compute_heuristics(_commits(days_since_last_commit=800, abandoned=True), _graph(), _deps())
        abandon = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert abandon['score'] >= 70

    def test_stable_team_low_burnout(self):
        signals = compute_heuristics(_commits(activity_decay_ratio=1.0), _graph(), _deps())
        burnout = next(s for s in signals if s['signal'] == 'burnout')
        assert burnout['score'] < 20

    def test_declining_team_higher_burnout(self):
        churn = [{'active': 10}, {'active': 10}, {'active': 2}]
        signals = compute_heuristics(_commits(contributor_churn=churn, activity_decay_ratio=0.3), _graph(), _deps())
        burnout = next(s for s in signals if s['signal'] == 'burnout')
        assert burnout['score'] > 30

    def test_god_modules_increase_monolith_score(self):
        signals = compute_heuristics(_commits(), _graph(god_modules=['a'] * 10), _deps())
        mono = next(s for s in signals if s['signal'] == 'monolith_growth')
        assert mono['score'] > 0

    def test_no_issues_low_dep_score(self):
        signals = compute_heuristics(_commits(), _graph(), _deps())
        dep = next(s for s in signals if s['signal'] == 'dependency_health')
        assert dep['score'] == 0

    def test_all_signals_have_confidence(self):
        signals = compute_heuristics(_commits(), _graph(), _deps())
        for s in signals:
            assert s.get('confidence') in ('high', 'medium', 'low')


class TestComputeOssScore:
    def test_returns_score_dict(self):
        signals = compute_heuristics(_commits(), _graph(), _deps())
        result = compute_oss_score(signals)
        assert isinstance(result, dict)
        assert 'score' in result
        assert 'badge' in result
        assert 'label' in result

    def test_score_in_range(self):
        signals = compute_heuristics(_commits(), _graph(), _deps())
        result = compute_oss_score(signals)
        assert 0.0 <= result['score'] <= 10.0

    def test_empty_signals_returns_midpoint(self):
        result = compute_oss_score([])
        assert result['score'] == 5.0

    def test_badge_matches_score(self):
        signals = compute_heuristics(_commits(), _graph(), _deps())
        result = compute_oss_score(signals)
        score = result['score']
        badge = result['badge']
        if score >= 9.0:
            assert badge == 'champion'
        elif score >= 7.5:
            assert badge == 'thriving'
        elif score >= 6.0:
            assert badge == 'growing'
        elif score >= 4.0:
            assert badge == 'seedling'
        elif score >= 2.0:
            assert badge == 'struggling'
        else:
            assert badge == 'dormant'
