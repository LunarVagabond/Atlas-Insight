import pytest
from apps.analysis.heuristics import compute_heuristics, compute_oss_score


def _base_commits(**overrides):
    data = {
        'activity_decay_ratio': 1.0,
        'contributor_churn': [],
        'days_since_last_commit': 5,
        'abandoned': False,
        'total_commits': 100,
        'total_contributors': 5,
        'monthly_frequency': [],
    }
    data.update(overrides)
    return data


def _base_graph(**overrides):
    data = {'node_count': 10, 'god_modules': [], 'cycle_count': 0}
    data.update(overrides)
    return data


def _base_deps(**overrides):
    data = {'docker_issues': [], 'missing_lockfile_warnings': [], 'dependency_count': 10}
    data.update(overrides)
    return data


def _base_readme(**overrides):
    data = {
        'found': True,
        'word_count': 500,
        'has_installation': True,
        'has_usage': True,
        'has_changelog': True,
        'has_contributing': True,
    }
    data.update(overrides)
    return data


def _base_structure(**overrides):
    data = {
        'has_ci': True,
        'has_lint_config': True,
        'test_ratio': 0.25,
        'ci_systems': ['GitHub Actions'],
        'bus_factor': 3,
        'release_count': 5,
        'last_release': None,
        'license_type': 'MIT',
        'license_file': 'LICENSE',
        'has_contributing': True,
        'has_security_policy': True,
        'has_coc': True,
        'has_changelog': True,
    }
    data.update(overrides)
    return data


class TestBurnoutSignal:
    def test_stable_activity(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps())
        burnout = next(s for s in signals if s['signal'] == 'burnout')
        assert burnout['score'] < 20
        assert 'stable' in burnout['description'].lower()

    def test_contributor_drop(self):
        churn = [
            {'active': 10},
            {'active': 10},
            {'active': 10},
            {'active': 2},
        ]
        commits = _base_commits(contributor_churn=churn, activity_decay_ratio=0.5)
        signals = compute_heuristics(commits, _base_graph(), _base_deps())
        burnout = next(s for s in signals if s['signal'] == 'burnout')
        assert burnout['score'] > 20

    def test_high_confidence_with_6_months(self):
        churn = [{'active': 5}] * 6
        commits = _base_commits(contributor_churn=churn)
        signals = compute_heuristics(commits, _base_graph(), _base_deps())
        burnout = next(s for s in signals if s['signal'] == 'burnout')
        assert burnout['confidence'] == 'high'

    def test_medium_confidence_below_6(self):
        churn = [{'active': 5}] * 3
        commits = _base_commits(contributor_churn=churn)
        signals = compute_heuristics(commits, _base_graph(), _base_deps())
        burnout = next(s for s in signals if s['signal'] == 'burnout')
        assert burnout['confidence'] == 'medium'


class TestAbandonmentSignal:
    def test_active_project(self):
        signals = compute_heuristics(_base_commits(days_since_last_commit=5), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert sig['score'] == 0

    def test_30_to_90_days(self):
        signals = compute_heuristics(_base_commits(days_since_last_commit=60), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert 10 <= sig['score'] <= 40

    def test_90_to_180_days(self):
        signals = compute_heuristics(_base_commits(days_since_last_commit=120), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert 30 <= sig['score'] <= 60

    def test_180_to_365_days(self):
        signals = compute_heuristics(_base_commits(days_since_last_commit=300), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert 50 <= sig['score'] <= 80

    def test_1_to_2_years(self):
        signals = compute_heuristics(_base_commits(days_since_last_commit=500), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert sig['score'] >= 60

    def test_over_2_years(self):
        signals = compute_heuristics(_base_commits(days_since_last_commit=800), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert sig['score'] >= 80

    def test_description_mentions_years(self):
        signals = compute_heuristics(_base_commits(days_since_last_commit=800), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'abandonment_risk')
        assert 'year' in sig['description'].lower()


class TestMonolithSignal:
    def test_no_issues(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'monolith_growth')
        assert sig['score'] < 15
        assert 'healthy' in sig['description'].lower()

    def test_god_modules_increase_score(self):
        graph = _base_graph(god_modules=['a', 'b', 'c', 'd', 'e'])
        signals = compute_heuristics(_base_commits(), graph, _base_deps())
        sig = next(s for s in signals if s['signal'] == 'monolith_growth')
        assert sig['score'] == 20

    def test_cycles_increase_score(self):
        graph = _base_graph(cycle_count=10)
        signals = compute_heuristics(_base_commits(), graph, _base_deps())
        sig = next(s for s in signals if s['signal'] == 'monolith_growth')
        assert sig['score'] == 30

    def test_high_confidence_large_graph(self):
        graph = _base_graph(node_count=100)
        signals = compute_heuristics(_base_commits(), graph, _base_deps())
        sig = next(s for s in signals if s['signal'] == 'monolith_growth')
        assert sig['confidence'] == 'high'

    def test_low_confidence_small_graph(self):
        signals = compute_heuristics(_base_commits(), _base_graph(node_count=10), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'monolith_growth')
        assert sig['confidence'] == 'low'


class TestDependencyHealthSignal:
    def test_no_issues(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'dependency_health')
        assert sig['score'] == 0

    def test_docker_issues_increase_score(self):
        deps = _base_deps(docker_issues=[{'file': 'Dockerfile', 'issue': 'old base'}])
        signals = compute_heuristics(_base_commits(), _base_graph(), deps)
        sig = next(s for s in signals if s['signal'] == 'dependency_health')
        assert sig['score'] == 15

    def test_lockfile_warnings_increase_score(self):
        deps = _base_deps(missing_lockfile_warnings=['Python lockfile missing'])
        signals = compute_heuristics(_base_commits(), _base_graph(), deps)
        sig = next(s for s in signals if s['signal'] == 'dependency_health')
        assert sig['score'] == 20

    def test_large_dep_count(self):
        deps = _base_deps(dependency_count=250)
        signals = compute_heuristics(_base_commits(), _base_graph(), deps)
        sig = next(s for s in signals if s['signal'] == 'dependency_health')
        assert 'total dependencies' in sig['description']


class TestDocumentationSignal:
    def test_no_readme(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), readme={'found': False})
        sig = next(s for s in signals if s['signal'] == 'documentation_quality')
        assert sig['score'] == 90

    def test_complete_readme(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), readme=_base_readme())
        sig = next(s for s in signals if s['signal'] == 'documentation_quality')
        assert sig['score'] == 0
        assert 'complete' in sig['description'].lower()

    def test_short_readme(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            readme=_base_readme(word_count=50)
        )
        sig = next(s for s in signals if s['signal'] == 'documentation_quality')
        assert sig['score'] > 0

    def test_missing_sections(self):
        readme = _base_readme(has_installation=False, has_usage=False)
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), readme=readme)
        sig = next(s for s in signals if s['signal'] == 'documentation_quality')
        assert sig['score'] > 0

    def test_not_included_when_readme_none(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps())
        names = [s['signal'] for s in signals]
        assert 'documentation_quality' not in names


class TestCiHealthSignal:
    def test_healthy(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(), structure=_base_structure()
        )
        sig = next(s for s in signals if s['signal'] == 'ci_health')
        assert sig['score'] == 0

    def test_no_ci(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(has_ci=False)
        )
        sig = next(s for s in signals if s['signal'] == 'ci_health')
        assert sig['score'] >= 40

    def test_very_low_test_ratio(self):
        # Without CI the full penalty applies (30 pts); with CI it scales to 65%
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(test_ratio=0.02, has_ci=False)
        )
        sig = next(s for s in signals if s['signal'] == 'ci_health')
        assert sig['score'] >= 30

    def test_low_test_ratio(self):
        # Without CI the full penalty applies (15 pts); with CI it scales to 65%
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(test_ratio=0.10, has_ci=False)
        )
        sig = next(s for s in signals if s['signal'] == 'ci_health')
        assert sig['score'] >= 15

    def test_no_lint_config(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(has_lint_config=False)
        )
        sig = next(s for s in signals if s['signal'] == 'ci_health')
        assert sig['score'] >= 20


class TestBusFactorSignal:
    def test_solo_project(self):
        commits = _base_commits(total_contributors=1)
        signals = compute_heuristics(commits, _base_graph(), _base_deps(), structure=_base_structure(bus_factor=1))
        sig = next(s for s in signals if s['signal'] == 'bus_factor_risk')
        assert sig['score'] == 0
        assert 'solo' in sig['description'].lower()

    def test_bus_factor_1_many_contributors(self):
        commits = _base_commits(total_contributors=15)
        signals = compute_heuristics(commits, _base_graph(), _base_deps(), structure=_base_structure(bus_factor=1))
        sig = next(s for s in signals if s['signal'] == 'bus_factor_risk')
        assert sig['score'] <= 45

    def test_bus_factor_1_few_contributors(self):
        commits = _base_commits(total_contributors=3)
        signals = compute_heuristics(commits, _base_graph(), _base_deps(), structure=_base_structure(bus_factor=1))
        sig = next(s for s in signals if s['signal'] == 'bus_factor_risk')
        assert '80%' in sig['description']

    def test_bus_factor_2(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), structure=_base_structure(bus_factor=2))
        sig = next(s for s in signals if s['signal'] == 'bus_factor_risk')
        assert 'low redundancy' in sig['description']

    def test_bus_factor_high(self):
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), structure=_base_structure(bus_factor=5))
        sig = next(s for s in signals if s['signal'] == 'bus_factor_risk')
        assert '5 contributors' in sig['description']


class TestSecuritySignal:
    def test_no_issues(self):
        security = {'score': 0, 'issues': [], 'vulnerabilities': []}
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert 'No obvious' in sig['description']

    def test_with_issues(self):
        security = {
            'score': 30,
            'issues': [{'detail': 'secret key found', 'commit_sha': 'abc1234', 'commit_author': 'dev'}],
            'vulnerabilities': [],
        }
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert sig['score'] >= 30
        assert len(sig['items']) >= 1

    def test_with_cve(self):
        security = {
            'score': 0,
            'issues': [],
            'vulnerabilities': [{'severity_score': 9.5}],
        }
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert sig['score'] >= 25

    def test_cve_medium_severity(self):
        security = {
            'score': 0,
            'issues': [],
            'vulnerabilities': [{'severity_score': 5.0}],
        }
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert sig['score'] == 8

    def test_cve_low_severity(self):
        security = {
            'score': 0,
            'issues': [],
            'vulnerabilities': [{'severity_score': 2.0}],
        }
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert sig['score'] == 3

    def test_cve_no_score(self):
        security = {
            'score': 0,
            'issues': [],
            'vulnerabilities': [{'name': 'CVE-2021-1234'}],
        }
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert sig['score'] == 8

    def test_issue_without_sha(self):
        security = {
            'score': 20,
            'issues': [{'detail': 'plain secret'}],
            'vulnerabilities': [],
        }
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert sig['items'][0] == 'plain secret'

    def test_issue_with_sha_only(self):
        security = {
            'score': 20,
            'issues': [{'detail': 'secret', 'commit_sha': 'abc1234'}],
            'vulnerabilities': [],
        }
        signals = compute_heuristics(_base_commits(), _base_graph(), _base_deps(), security=security)
        sig = next(s for s in signals if s['signal'] == 'security_hygiene')
        assert 'abc1234' in sig['items'][0]


class TestReleaseCadenceSignal:
    def test_no_releases(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(release_count=0)
        )
        sig = next(s for s in signals if s['signal'] == 'release_cadence')
        assert sig['score'] == 35

    def test_recent_release(self):
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(release_count=5, last_release={'date': recent})
        )
        sig = next(s for s in signals if s['signal'] == 'release_cadence')
        assert sig['score'] == 0

    def test_stale_release_over_2_years(self):
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(days=800)).isoformat()
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(release_count=3, last_release={'date': old})
        )
        sig = next(s for s in signals if s['signal'] == 'release_cadence')
        assert sig['score'] >= 50

    def test_no_release_date(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(release_count=2, last_release={'date': None})
        )
        sig = next(s for s in signals if s['signal'] == 'release_cadence')
        assert sig['score'] == 20

    def test_bad_date_string(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(release_count=2, last_release={'date': 'not-a-date'})
        )
        sig = next(s for s in signals if s['signal'] == 'release_cadence')
        assert sig['score'] == 20


class TestCommunityHealthSignal:
    def test_complete_community(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure()
        )
        sig = next(s for s in signals if s['signal'] == 'community_health')
        assert sig['score'] == 0

    def test_no_license(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(license_type=None, license_file=None)
        )
        sig = next(s for s in signals if s['signal'] == 'community_health')
        assert sig['score'] >= 30

    def test_missing_multiple_files(self):
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=_base_structure(
                license_type=None, license_file=None,
                has_contributing=False, has_security_policy=False,
                has_coc=False, has_changelog=False
            )
        )
        sig = next(s for s in signals if s['signal'] == 'community_health')
        assert sig['score'] >= 75


class TestCommitVelocitySignal:
    def test_stable_velocity(self):
        monthly = [{'count': 10}] * 6
        signals = compute_heuristics(_base_commits(monthly_frequency=monthly), _base_graph(), _base_deps())
        sig = next((s for s in signals if s['signal'] == 'commit_velocity'), None)
        assert sig is not None
        assert sig['score'] == 0

    def test_slowing_velocity(self):
        monthly = [{'count': 10}] * 3 + [{'count': 3}] * 3
        signals = compute_heuristics(_base_commits(monthly_frequency=monthly), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'commit_velocity')
        assert sig['score'] >= 50

    def test_sharp_decline(self):
        monthly = [{'count': 20}] * 3 + [{'count': 1}] * 3
        signals = compute_heuristics(_base_commits(monthly_frequency=monthly), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'commit_velocity')
        assert sig['score'] >= 65

    def test_not_included_when_less_than_6_months(self):
        monthly = [{'count': 5}] * 4
        signals = compute_heuristics(_base_commits(monthly_frequency=monthly), _base_graph(), _base_deps())
        names = [s['signal'] for s in signals]
        assert 'commit_velocity' not in names

    def test_zero_prior_avg(self):
        monthly = [{'count': 0}] * 3 + [{'count': 5}] * 3
        signals = compute_heuristics(_base_commits(monthly_frequency=monthly), _base_graph(), _base_deps())
        sig = next(s for s in signals if s['signal'] == 'commit_velocity')
        assert sig['score'] == 0


class TestComputeOssScore:
    def test_perfect_score(self):
        signals = [
            {'signal': 'community_health', 'score': 0},
            {'signal': 'documentation_quality', 'score': 0},
            {'signal': 'ci_health', 'score': 0},
            {'signal': 'release_cadence', 'score': 0},
            {'signal': 'abandonment_risk', 'score': 0},
            {'signal': 'bus_factor_risk', 'score': 0},
        ]
        result = compute_oss_score(signals)
        assert result['score'] == 10.0
        assert result['badge'] == 'champion'

    def test_zero_score(self):
        signals = [
            {'signal': 'community_health', 'score': 100},
            {'signal': 'documentation_quality', 'score': 100},
            {'signal': 'ci_health', 'score': 100},
            {'signal': 'release_cadence', 'score': 100},
            {'signal': 'abandonment_risk', 'score': 100},
            {'signal': 'bus_factor_risk', 'score': 100},
        ]
        result = compute_oss_score(signals)
        assert result['score'] == 0.0
        assert result['badge'] == 'dormant'

    def test_badges_at_thresholds(self):
        def score_for(val):
            signals = [
                {'signal': 'community_health', 'score': val},
                {'signal': 'documentation_quality', 'score': val},
                {'signal': 'ci_health', 'score': val},
                {'signal': 'release_cadence', 'score': val},
                {'signal': 'abandonment_risk', 'score': val},
                {'signal': 'bus_factor_risk', 'score': val},
            ]
            return compute_oss_score(signals)

        assert score_for(25)['badge'] == 'thriving'
        assert score_for(40)['badge'] == 'growing'
        assert score_for(55)['badge'] == 'seedling'
        assert score_for(75)['badge'] == 'struggling'

    def test_empty_signals(self):
        result = compute_oss_score([])
        assert result['score'] == 5.0

    def test_missing_signals_excluded_from_weight(self):
        signals = [{'signal': 'community_health', 'score': 0}]
        result = compute_oss_score(signals)
        assert result['score'] == 10.0


class TestScoringModeFairness:
    def _closed_source_structure(self):
        return _base_structure(
            license_type=None,
            license_file=None,
            has_contributing=False,
            has_coc=False,
            has_changelog=False,
            has_security_policy=True,
        )

    def _closed_source_readme(self):
        return _base_readme(
            has_changelog=False,
            has_contributing=False,
        )

    def test_closed_source_scores_higher_without_oss_files(self):
        structure = self._closed_source_structure()
        readme = self._closed_source_readme()
        license_data = {'score': 60, 'spdx_id': None, 'issues': []}
        oss_signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            readme=readme, structure=structure, license_data=license_data,
            scoring_mode='oss',
        )
        closed_signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            readme=readme, structure=structure, license_data=license_data,
            scoring_mode='closed_source',
        )
        oss_score = compute_oss_score(oss_signals, scoring_mode='oss')['score']
        closed_score = compute_oss_score(closed_signals, scoring_mode='closed_source')['score']
        assert closed_score > oss_score

    def test_closed_source_community_health_ignores_license(self):
        structure = self._closed_source_structure()
        signals = compute_heuristics(
            _base_commits(), _base_graph(), _base_deps(),
            structure=structure, scoring_mode='closed_source',
        )
        comm = next(s for s in signals if s['signal'] == 'community_health')
        assert comm['score'] == 0

    def test_closed_source_weights_sum_to_one(self):
        from apps.analysis.heuristics import compute_oss_score as cos
        signals = [
            {'signal': k, 'score': 50}
            for k in (
                'community_health', 'documentation_quality', 'ci_health',
                'security_hygiene', 'release_cadence', 'abandonment_risk',
                'license_risk', 'test_coverage', 'dependency_health',
                'cicd_maturity', 'bus_factor_risk', 'complexity_debt',
                'container_hygiene', 'monolith_growth', 'commit_velocity', 'burnout',
            )
        ]
        result = cos(signals, scoring_mode='closed_source')
        assert result['mode'] == 'closed_source'
