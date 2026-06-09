import pytest
from apps.analysis.contribution_analysis.heuristics import generate_heuristic_opportunities


def _s(**kw):
    base = {
        'license_file': 'LICENSE', 'license_type': 'MIT',
        'has_contributing': True, 'has_changelog': True, 'has_coc': True,
        'has_security_policy': True, 'has_ci': True, 'has_lint_config': True,
        'test_ratio': 0.25, 'roadmap_file': None, 'bus_factor': 3,
        'top_contributors': [],
    }
    base.update(kw)
    return base


def _r(**kw):
    base = {'found': True, 'has_installation': True, 'has_usage': True}
    base.update(kw)
    return base


def _g(**kw):
    base = {'god_modules': [], 'cycle_count': 0, 'cycles': []}
    base.update(kw)
    return base


class TestBeginnerOpportunities:
    def test_add_license_when_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None,
            _s(license_file=None, license_type=None),
            None
        )
        ids = [o['id'] for o in opps]
        assert 'add_license' in ids

    def test_no_license_opp_when_present(self):
        opps = generate_heuristic_opportunities({}, _g(), {}, None, _s(), None)
        ids = [o['id'] for o in opps]
        assert 'add_license' not in ids

    def test_closed_source_skips_oss_community_opps(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None,
            _s(
                license_file=None, license_type=None,
                has_contributing=False, has_changelog=False, has_coc=False,
                has_security_policy=True,
            ),
            None,
            scoring_mode='closed_source',
        )
        ids = [o['id'] for o in opps]
        assert 'add_license' not in ids
        assert 'add_contributing' not in ids
        assert 'add_changelog' not in ids
        assert 'add_coc' not in ids

    def test_add_contributing_when_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(has_contributing=False), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_contributing' in ids

    def test_add_changelog_when_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(has_changelog=False), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_changelog' in ids

    def test_add_coc_when_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(has_coc=False), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_coc' in ids

    def test_add_security_policy_when_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(has_security_policy=False), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_security_policy' in ids

    def test_add_readme_when_missing(self):
        opps = generate_heuristic_opportunities({}, _g(), {}, {'found': False}, _s(), None)
        ids = [o['id'] for o in opps]
        assert 'add_readme' in ids

    def test_readme_installation_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, _r(has_installation=False), _s(), None
        )
        ids = [o['id'] for o in opps]
        assert 'readme_installation' in ids

    def test_readme_usage_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, _r(has_usage=False), _s(), None
        )
        ids = [o['id'] for o in opps]
        assert 'readme_usage' in ids

    def test_gitignore_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, None, {'gitignore_exists': False}
        )
        ids = [o['id'] for o in opps]
        assert 'add_gitignore' in ids

    def test_gitignore_gaps(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, None,
            {'gitignore_exists': True, 'gitignore_gaps': ['.env', 'node_modules']}
        )
        ids = [o['id'] for o in opps]
        assert 'gitignore_gaps' in ids

    def test_roadmap_file_opp(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(roadmap_file='ROADMAP.md'), None
        )
        ids = [o['id'] for o in opps]
        assert 'roadmap' in ids

    def test_lockfile_warning(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {'missing_lockfile_warnings': ['Python lockfile missing']},
            None, None, None
        )
        ids = [o['id'] for o in opps]
        assert 'lockfile_0' in ids

    def test_lockfile_capped_at_2(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {'missing_lockfile_warnings': ['A', 'B', 'C']},
            None, None, None
        )
        ids = [o['id'] for o in opps]
        assert 'lockfile_0' in ids
        assert 'lockfile_1' in ids
        assert 'lockfile_2' not in ids


class TestIntermediateOpportunities:
    def test_add_ci_when_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(has_ci=False), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_ci' in ids

    def test_add_linting_when_missing(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(has_lint_config=False), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_linting' in ids

    def test_add_tests_very_low_ratio(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(test_ratio=0.02), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_tests' in ids

    def test_improve_tests_low_ratio(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(test_ratio=0.10), None
        )
        ids = [o['id'] for o in opps]
        assert 'improve_tests' in ids

    def test_no_test_opp_when_ratio_ok(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(test_ratio=0.25), None
        )
        ids = [o['id'] for o in opps]
        assert 'add_tests' not in ids
        assert 'improve_tests' not in ids

    def test_docker_issues(self):
        deps = {'docker_issues': [{'file': 'Dockerfile', 'issue': 'Deprecated base'}]}
        opps = generate_heuristic_opportunities({}, _g(), deps, None, _s(), None)
        ids = [o['id'] for o in opps]
        assert 'docker_0' in ids

    def test_docker_capped_at_3(self):
        deps = {'docker_issues': [
            {'file': f'Dockerfile{i}', 'issue': 'Old'} for i in range(5)
        ]}
        opps = generate_heuristic_opportunities({}, _g(), deps, None, _s(), None)
        ids = [o['id'] for o in opps]
        assert 'docker_0' in ids
        assert 'docker_2' in ids
        assert 'docker_3' not in ids


class TestAdvancedOpportunities:
    def test_god_module_refactor(self):
        graph = _g(god_modules=[{'module': 'core.py', 'in_degree': 20}])
        opps = generate_heuristic_opportunities({}, graph, {}, None, None, None)
        ids = [o['id'] for o in opps]
        assert 'refactor_core.py' in ids

    def test_god_modules_capped_at_3(self):
        graph = _g(god_modules=[{'module': f'mod{i}.py', 'in_degree': 5} for i in range(5)])
        opps = generate_heuristic_opportunities({}, graph, {}, None, None, None)
        ids = [o['id'] for o in opps]
        refactor_ids = [id_ for id_ in ids if id_.startswith('refactor_')]
        assert len(refactor_ids) == 3

    def test_break_cycles(self):
        graph = _g(cycle_count=3)
        opps = generate_heuristic_opportunities({}, graph, {}, None, None, None)
        ids = [o['id'] for o in opps]
        assert 'break_cycles' in ids

    def test_break_cycles_with_sample(self):
        graph = _g(cycle_count=2, cycles=[['a.py', 'b.py', 'c.py']])
        opps = generate_heuristic_opportunities({}, graph, {}, None, None, None)
        cycle_opp = next(o for o in opps if o['id'] == 'break_cycles')
        assert any('a.py' in h for h in cycle_opp['hints'])

    def test_no_cycle_opp_when_zero(self):
        opps = generate_heuristic_opportunities({}, _g(cycle_count=0), {}, None, None, None)
        ids = [o['id'] for o in opps]
        assert 'break_cycles' not in ids

    def test_bus_factor_opp(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(bus_factor=1), None
        )
        ids = [o['id'] for o in opps]
        assert 'bus_factor' in ids

    def test_bus_factor_opp_uses_top_contributor(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None,
            _s(bus_factor=1, top_contributors=[{'author': 'alice@example.com'}]),
            None
        )
        bf_opp = next(o for o in opps if o['id'] == 'bus_factor')
        assert 'alice@example.com' in bf_opp['description']

    def test_no_bus_factor_opp_when_ok(self):
        opps = generate_heuristic_opportunities(
            {}, _g(), {}, None, _s(bus_factor=3), None
        )
        ids = [o['id'] for o in opps]
        assert 'bus_factor' not in ids


class TestEdgeCases:
    def test_none_structure(self):
        opps = generate_heuristic_opportunities({}, _g(), {}, None, None, None)
        assert isinstance(opps, list)

    def test_none_readme(self):
        opps = generate_heuristic_opportunities({}, _g(), {}, None, _s(), None)
        assert isinstance(opps, list)

    def test_none_security(self):
        opps = generate_heuristic_opportunities({}, _g(), {}, _r(), _s(), None)
        assert isinstance(opps, list)

    def test_each_opp_has_required_keys(self):
        opps = generate_heuristic_opportunities(
            {}, _g(god_modules=[{'module': 'a.py', 'in_degree': 5}]),
            {'missing_lockfile_warnings': ['warn']},
            _r(has_installation=False), _s(has_ci=False), None
        )
        for opp in opps:
            assert 'id' in opp
            assert 'title' in opp
            assert 'description' in opp
            assert 'difficulty' in opp
            assert 'risk' in opp
            assert 'hints' in opp
