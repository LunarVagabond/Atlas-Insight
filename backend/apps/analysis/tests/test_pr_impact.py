import pytest
from apps.analysis.pr_impact import affected_subsystems, suggest_reviewers, compute_complexity


def _result(subsystems=None, top_contributors=None):
    return {
        'ownership': {
            'subsystems': subsystems or [],
            'top_contributors': top_contributors or [],
            'bus_factor': 1,
        }
    }


def _sub(id, stype='other', activity=0.5, god_modules=None):
    return {
        'id': id,
        'name': f'{id} subsystem',
        'subsystem_type': stype,
        'activity_score': activity,
        'god_modules': god_modules or [],
        'hot_files': [],
    }


def _contrib(author, email='', files_touched=10):
    return {'author': author, 'email': email or f'{author}@example.com', 'files_touched': files_touched}


class TestAffectedSubsystems:
    def test_single_subsystem_match(self):
        result = _result(subsystems=[_sub('backend')])
        hits = affected_subsystems(['backend/apps/api.py'], result)
        assert len(hits) == 1
        assert hits[0]['id'] == 'backend'
        assert hits[0]['matched_files'] == 1

    def test_no_match_returns_empty(self):
        result = _result(subsystems=[_sub('backend')])
        hits = affected_subsystems(['frontend/src/App.vue'], result)
        assert hits == []

    def test_monorepo_two_level_subsystem(self):
        result = _result(subsystems=[_sub('frontend_src')])
        hits = affected_subsystems(['frontend/src/components/Foo.vue'], result)
        assert len(hits) == 1
        assert hits[0]['id'] == 'frontend_src'

    def test_multiple_subsystems_sorted_by_match_count(self):
        result = _result(subsystems=[_sub('backend'), _sub('frontend')])
        files = ['backend/a.py', 'backend/b.py', 'frontend/App.vue']
        hits = affected_subsystems(files, result)
        assert hits[0]['id'] == 'backend'
        assert hits[0]['matched_files'] == 2
        assert hits[1]['id'] == 'frontend'
        assert hits[1]['matched_files'] == 1

    def test_empty_changed_files(self):
        result = _result(subsystems=[_sub('backend')])
        assert affected_subsystems([], result) == []

    def test_no_subsystems_in_result(self):
        hits = affected_subsystems(['backend/a.py'], {})
        assert hits == []

    def test_exact_dir_name_matches(self):
        result = _result(subsystems=[_sub('src')])
        hits = affected_subsystems(['src'], result)
        assert len(hits) == 1

    def test_god_module_flag_propagated(self):
        sub = _sub('backend', god_modules=[{'module': 'backend/core.py', 'in_degree': 20}])
        result = _result(subsystems=[sub])
        hits = affected_subsystems(['backend/core.py'], result)
        assert hits[0]['has_god_modules'] is True

    def test_no_god_module_when_clear(self):
        result = _result(subsystems=[_sub('backend')])
        hits = affected_subsystems(['backend/utils.py'], result)
        assert hits[0]['has_god_modules'] is False


class TestSuggestReviewers:
    def test_file_history_primary_path(self):
        author_pr_files = {
            'alice@x.com': {'backend/api.py', 'backend/auth.py'},
            'bob@x.com': {'backend/api.py'},
        }
        author_names = {'alice@x.com': 'Alice', 'bob@x.com': 'Bob'}
        reviewers = suggest_reviewers([], [], {}, author_pr_files, author_names)
        assert reviewers[0]['author'] == 'Alice'
        assert reviewers[0]['pr_files_touched'] == 2
        assert reviewers[0]['match_reason'] == 'file_history'
        assert reviewers[1]['pr_files_touched'] == 1

    def test_file_history_limits_to_5(self):
        author_pr_files = {f'dev{i}@x.com': {'file.py'} for i in range(10)}
        reviewers = suggest_reviewers([], [], {}, author_pr_files, {})
        assert len(reviewers) <= 5

    def test_returns_top_contributors_when_no_subsystem_match(self):
        result = _result(top_contributors=[_contrib('alice'), _contrib('bob')])
        reviewers = suggest_reviewers(['docs/README.md'], [], result)
        assert len(reviewers) == 2
        assert reviewers[0]['match_reason'] == 'top_contributor'

    def test_subsystem_match_scores_contributors(self):
        sub = _sub('backend', activity=0.8)
        result = _result(
            subsystems=[sub],
            top_contributors=[_contrib('alice', files_touched=30), _contrib('bob', files_touched=5)],
        )
        hit = {**sub, 'has_god_modules': False, 'matched_files': 1}
        reviewers = suggest_reviewers(['backend/api.py'], [hit], result)
        assert reviewers[0]['author'] == 'alice'
        assert reviewers[0]['match_reason'] == 'subsystem_match'

    def test_limits_to_5_reviewers(self):
        contribs = [_contrib(f'dev{i}') for i in range(10)]
        result = _result(top_contributors=contribs)
        reviewers = suggest_reviewers(['docs/x.md'], [], result)
        assert len(reviewers) <= 5

    def test_empty_contributors_returns_empty(self):
        result = _result()
        reviewers = suggest_reviewers(['backend/a.py'], [], result)
        assert reviewers == []

    def test_no_result_ownership_falls_back_to_structure(self):
        result = {
            'ownership': {},
            'structure': {'top_contributors': [_contrib('alice')]},
        }
        reviewers = suggest_reviewers(['x.py'], [], result)
        assert len(reviewers) == 1
        assert reviewers[0]['author'] == 'alice'


class TestComputeComplexity:
    def _run(self, additions=10, deletions=5, files=None, subsystems=None):
        return compute_complexity(
            additions, deletions,
            files or ['src/foo.py'],
            subsystems or [],
            {},
        )

    def test_small_pr_is_low(self):
        result = self._run(additions=20, deletions=10, files=['src/utils.py'])
        assert result['label'] == 'low'
        assert result['score'] < 30

    def test_many_files_raises_score(self):
        files = [f'src/file{i}.py' for i in range(35)]
        result = compute_complexity(50, 30, files, [], {})
        assert result['score'] >= 30

    def test_large_diff_raises_score(self):
        result = compute_complexity(800, 300, ['src/big.py'], [], {})
        assert result['score'] >= 20

    def test_dep_file_detected(self):
        result = compute_complexity(5, 2, ['package.json'], [], {})
        assert result['touches_deps'] is True
        assert result['score'] >= 10

    def test_god_module_detected(self):
        sub = {'id': 'src', 'has_god_modules': True, 'activity_score': 0.3, 'subsystem_type': 'other', 'matched_files': 1, 'name': 'src'}
        result = compute_complexity(5, 2, ['src/core.py'], [sub], {})
        assert result['touches_god_module'] is True
        assert result['score'] >= 10

    def test_multi_subsystem_high_complexity(self):
        subs = [
            {'id': f's{i}', 'has_god_modules': False, 'activity_score': 0.2, 'subsystem_type': 'other', 'matched_files': 1, 'name': f's{i}'}
            for i in range(5)
        ]
        files = [f's{i}/file.py' for i in range(5)] + [f'src/file{i}.py' for i in range(20)]
        result = compute_complexity(200, 100, files, subs, {})
        assert result['label'] in ('medium', 'high')

    def test_score_capped_at_100(self):
        subs = [
            {'id': f's{i}', 'has_god_modules': True, 'activity_score': 0.9, 'subsystem_type': 'other', 'matched_files': 5, 'name': f's{i}'}
            for i in range(6)
        ]
        files = [f's{i}/f{j}.py' for i in range(6) for j in range(10)] + ['package.json']
        result = compute_complexity(2000, 1000, files, subs, {})
        assert result['score'] <= 100

    def test_high_label_threshold(self):
        subs = [
            {'id': f's{i}', 'has_god_modules': False, 'activity_score': 0.1, 'subsystem_type': 'other', 'matched_files': 1, 'name': f's{i}'}
            for i in range(5)
        ]
        files = [f'src/file{i}.py' for i in range(35)]
        result = compute_complexity(1200, 500, files, subs, {})
        assert result['label'] == 'high'

    def test_notes_populated_for_notable_signals(self):
        files = [f'src/file{i}.py' for i in range(35)]
        result = compute_complexity(1500, 500, files, [], {})
        assert len(result['notes']) > 0

    def test_no_dep_file_not_flagged(self):
        result = compute_complexity(5, 2, ['src/util.py'], [], {})
        assert result['touches_deps'] is False
