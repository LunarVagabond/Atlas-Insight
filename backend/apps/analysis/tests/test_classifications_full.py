import pytest
from apps.analysis.classifications import (
    classify_repo,
    _contribution_difficulty_score,
    _health_score,
    _complexity_score,
    _documentation_score,
    _compute_tags,
    _threshold_label,
    CONTRIBUTION_THRESHOLDS,
    HEALTH_THRESHOLDS,
    COMPLEXITY_THRESHOLDS,
    DOC_THRESHOLDS,
)


def _commits(**kw):
    base = {'days_since_last_commit': 5, 'abandoned': False, 'activity_decay_ratio': 1.0, 'total_contributors': 5}
    base.update(kw)
    return base


def _graph(**kw):
    base = {'god_modules': [], 'cycle_count': 0, 'node_count': 10}
    base.update(kw)
    return base


def _readme(**kw):
    base = {
        'found': True, 'word_count': 500,
        'has_installation': True, 'has_usage': True,
        'has_contributing': True, 'has_changelog': True, 'has_license': True,
    }
    base.update(kw)
    return base


def _structure(**kw):
    base = {
        'has_ci': True, 'has_lint_config': True, 'test_ratio': 0.25,
        'has_contributing': True, 'release_count': 5, 'has_changelog': True,
        'has_coc': True, 'license_type': 'MIT', 'license_file': 'LICENSE',
        'has_security_policy': True, 'bus_factor': 3,
    }
    base.update(kw)
    return base


class TestThresholdLabel:
    def test_first_threshold(self):
        result = _threshold_label(10, CONTRIBUTION_THRESHOLDS)
        assert result['key'] == 'very_easy'

    def test_last_threshold(self):
        result = _threshold_label(95, CONTRIBUTION_THRESHOLDS)
        assert result['key'] == 'very_hard'

    def test_score_preserved(self):
        result = _threshold_label(55, CONTRIBUTION_THRESHOLDS)
        assert result['score'] == 55


class TestContributionDifficultyScore:
    def test_ideal_project(self):
        score = _contribution_difficulty_score(
            _commits(), _readme(), _structure(), _graph()
        )
        assert score < 20

    def test_no_readme(self):
        score = _contribution_difficulty_score(_commits(), {'found': False}, _structure(), _graph())
        assert score >= 25

    def test_short_readme(self):
        score = _contribution_difficulty_score(_commits(), _readme(word_count=50), _structure(), _graph())
        assert score >= 20

    def test_medium_readme(self):
        score = _contribution_difficulty_score(_commits(), _readme(word_count=200), _structure(), _graph())
        assert score >= 10

    def test_no_contributing_file(self):
        score = _contribution_difficulty_score(
            _commits(), _readme(), _structure(has_contributing=False), _graph()
        )
        assert score >= 7

    def test_no_ci(self):
        score = _contribution_difficulty_score(_commits(), _readme(), _structure(has_ci=False), _graph())
        assert score >= 15

    def test_very_low_test_ratio(self):
        score = _contribution_difficulty_score(
            _commits(), _readme(), _structure(test_ratio=0.01), _graph()
        )
        assert score >= 10

    def test_abandoned(self):
        score = _contribution_difficulty_score(
            _commits(abandoned=True), _readme(), _structure(), _graph()
        )
        assert score >= 25

    def test_stale_over_365(self):
        score = _contribution_difficulty_score(
            _commits(days_since_last_commit=400), _readme(), _structure(), _graph()
        )
        assert score >= 20

    def test_stale_180_to_365(self):
        score = _contribution_difficulty_score(
            _commits(days_since_last_commit=200), _readme(), _structure(), _graph()
        )
        assert score >= 10

    def test_stale_60_to_180(self):
        score = _contribution_difficulty_score(
            _commits(days_since_last_commit=100), _readme(), _structure(), _graph()
        )
        assert score >= 3

    def test_low_decay(self):
        score = _contribution_difficulty_score(
            _commits(activity_decay_ratio=0.1), _readme(), _structure(), _graph()
        )
        assert score >= 5

    def test_god_modules_add_score(self):
        score = _contribution_difficulty_score(
            _commits(), _readme(), _structure(), _graph(god_modules=['a', 'b', 'c'])
        )
        assert score >= 6

    def test_cycles_add_score(self):
        score = _contribution_difficulty_score(
            _commits(), _readme(), _structure(), _graph(cycle_count=3)
        )
        assert score >= 6

    def test_missing_readme_sections(self):
        score = _contribution_difficulty_score(
            _commits(), _readme(has_installation=False, has_usage=False), _structure(), _graph()
        )
        assert score >= 8

    def test_none_readme(self):
        score = _contribution_difficulty_score(_commits(), None, _structure(), _graph())
        assert isinstance(score, int)

    def test_none_structure(self):
        score = _contribution_difficulty_score(_commits(), _readme(), None, _graph())
        assert isinstance(score, int)


class TestHealthScore:
    def test_active_project(self):
        score = _health_score(_commits(), None)
        assert score == 0

    def test_high_decay(self):
        score = _health_score(_commits(activity_decay_ratio=0.0), None)
        assert score >= 40

    def test_stale_730_plus(self):
        score = _health_score(_commits(days_since_last_commit=800), None)
        assert score >= 40

    def test_stale_365_to_730(self):
        score = _health_score(_commits(days_since_last_commit=400), None)
        assert score >= 30

    def test_stale_180_to_365(self):
        score = _health_score(_commits(days_since_last_commit=200), None)
        assert score >= 15

    def test_stale_90_to_180(self):
        score = _health_score(_commits(days_since_last_commit=100), None)
        assert score >= 5

    def test_archived_maxes_score(self):
        score = _health_score(_commits(), {'archived': True})
        assert score == 100

    def test_caps_at_100(self):
        score = _health_score(_commits(activity_decay_ratio=0.0, days_since_last_commit=1000), None)
        assert score <= 100


class TestComplexityScore:
    def test_simple_project(self):
        score = _complexity_score(_graph(), None)
        assert score == 0

    def test_god_modules(self):
        score = _complexity_score(_graph(god_modules=['a'] * 10), None)
        assert score == 40

    def test_cycles(self):
        score = _complexity_score(_graph(cycle_count=10), None)
        assert score == 30

    def test_large_graph(self):
        score = _complexity_score(_graph(node_count=600), None)
        assert score >= 20

    def test_medium_graph(self):
        score = _complexity_score(_graph(node_count=250), None)
        assert score >= 10

    def test_moderate_graph(self):
        score = _complexity_score(_graph(node_count=100), None)
        assert score >= 5

    def test_large_codebase(self):
        score = _complexity_score(_graph(), _structure())
        assert isinstance(score, int)

    def test_with_many_lines(self):
        score = _complexity_score(_graph(), {'total_lines': 600_000})
        assert score >= 20

    def test_with_100k_lines(self):
        score = _complexity_score(_graph(), {'total_lines': 150_000})
        assert score >= 10

    def test_caps_at_100(self):
        score = _complexity_score(
            _graph(god_modules=['x'] * 30, cycle_count=50, node_count=1000),
            {'total_lines': 1_000_000}
        )
        assert score == 100


class TestDocumentationScore:
    def test_no_readme(self):
        assert _documentation_score(None, None) == 100
        assert _documentation_score({'found': False}, None) == 100

    def test_complete_readme(self):
        score = _documentation_score(_readme(), _structure())
        assert score == 0

    def test_very_short_readme(self):
        score = _documentation_score(_readme(word_count=30), None)
        assert score >= 40

    def test_short_readme(self):
        score = _documentation_score(_readme(word_count=100), None)
        assert score >= 20

    def test_medium_readme(self):
        score = _documentation_score(_readme(word_count=300), None)
        assert score >= 10

    def test_missing_sections(self):
        score = _documentation_score(
            _readme(has_installation=False, has_usage=False, has_contributing=False),
            None
        )
        assert score >= 26

    def test_no_contributing_file(self):
        score = _documentation_score(_readme(), _structure(has_contributing=False))
        assert score >= 10

    def test_no_changelog(self):
        score = _documentation_score(_readme(has_changelog=False), _structure(has_changelog=False))
        assert score >= 10

    def test_no_coc(self):
        score = _documentation_score(_readme(), _structure(has_coc=False))
        assert score >= 3


class TestComputeTags:
    def _call(self, commits=None, graph=None, deps=None, readme=None,
              structure=None, security=None, github_meta=None,
              health_score=0, complexity_score=0, doc_score=0):
        return _compute_tags(
            commits or _commits(),
            graph or _graph(),
            deps or {},
            readme,
            structure,
            security,
            github_meta,
            health_score, complexity_score, doc_score
        )

    def test_archived(self):
        tags = self._call(github_meta={'archived': True})
        assert 'archived' in tags

    def test_abandoned(self):
        tags = self._call(commits=_commits(abandoned=True))
        assert 'abandoned' in tags

    def test_actively_maintained(self):
        tags = self._call(health_score=5)
        assert 'actively-maintained' in tags

    def test_wildly_popular(self):
        tags = self._call(github_meta={'stars': 60_000, 'archived': False})
        assert 'wildly-popular' in tags

    def test_popular(self):
        tags = self._call(github_meta={'stars': 15_000, 'archived': False})
        assert 'popular' in tags

    def test_well_known(self):
        tags = self._call(github_meta={'stars': 2_000, 'archived': False})
        assert 'well-known' in tags

    def test_large_community(self):
        tags = self._call(commits=_commits(total_contributors=600))
        assert 'large-community' in tags

    def test_thriving_community(self):
        tags = self._call(commits=_commits(total_contributors=150))
        assert 'thriving-community' in tags

    def test_solo_project(self):
        tags = self._call(commits=_commits(total_contributors=1))
        assert 'solo-project' in tags

    def test_highly_complex(self):
        tags = self._call(complexity_score=85)
        assert 'highly-complex' in tags

    def test_simple_codebase(self):
        tags = self._call(complexity_score=10)
        assert 'simple-codebase' in tags

    def test_well_documented(self):
        tags = self._call(doc_score=5)
        assert 'well-documented' in tags

    def test_sparse_docs(self):
        tags = self._call(doc_score=80)
        assert 'sparse-docs' in tags

    def test_well_tested(self):
        tags = self._call(structure=_structure(has_ci=True, test_ratio=0.25))
        assert 'well-tested' in tags

    def test_no_ci(self):
        tags = self._call(structure=_structure(has_ci=False))
        assert 'no-ci' in tags

    def test_frequent_releases(self):
        tags = self._call(structure=_structure(release_count=15))
        assert 'frequent-releases' in tags

    def test_license_tag(self):
        tags = self._call(structure=_structure(license_type='MIT'))
        assert 'license:MIT' in tags

    def test_welcoming(self):
        tags = self._call(structure=_structure(has_contributing=True))
        assert 'welcoming' in tags

    def test_clean_secrets(self):
        tags = self._call(security={'score': 0})
        assert 'clean-secrets' in tags

    def test_security_concerns(self):
        tags = self._call(security={'score': 50})
        assert 'security-concerns' in tags

    def test_single_maintainer(self):
        tags = self._call(structure=_structure(bus_factor=1))
        assert 'single-maintainer' in tags

    def test_fork(self):
        tags = self._call(github_meta={'is_fork': True})
        assert 'fork' in tags

    def test_highly_forked(self):
        tags = self._call(github_meta={'forks': 10_000})
        assert 'highly-forked' in tags


class TestClassifyRepo:
    def test_returns_all_keys(self):
        result = classify_repo(
            _commits(), _graph(), {}, _readme(), _structure(), None, None
        )
        assert 'contribution_difficulty' in result
        assert 'project_health' in result
        assert 'code_complexity' in result
        assert 'documentation_grade' in result
        assert 'tags' in result

    def test_scores_in_result(self):
        result = classify_repo(
            _commits(), _graph(), {}, _readme(), _structure(), None, None
        )
        assert 'contribution_difficulty_score' in result
        assert 'project_health_score' in result

    def test_contribution_difficulty_label_is_dict(self):
        result = classify_repo(
            _commits(), _graph(), {}, _readme(), _structure(), None, None
        )
        assert isinstance(result['contribution_difficulty'], dict)
        assert 'key' in result['contribution_difficulty']
        assert 'label' in result['contribution_difficulty']
