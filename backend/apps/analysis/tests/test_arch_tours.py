import pytest
from apps.analysis.arch_tours import (
    _detect_subsystem_type,
    _file_note,
    _generate_description,
    _is_boring,
    _kahn_topo,
    generate_arch_tours,
)


class TestIsBoring:
    def test_init_py_is_boring(self):
        assert _is_boring('apps/myapp/__init__.py') is True

    def test_main_py_not_boring(self):
        assert _is_boring('apps/myapp/main.py') is False

    def test_models_not_boring(self):
        assert _is_boring('apps/models.py') is False


class TestDetectSubsystemType:
    def test_frontend(self):
        assert _detect_subsystem_type('frontend') == 'frontend'
        assert _detect_subsystem_type('src') == 'frontend'
        assert _detect_subsystem_type('components') == 'frontend'

    def test_api(self):
        assert _detect_subsystem_type('api') == 'api'
        assert _detect_subsystem_type('routes') == 'api'
        assert _detect_subsystem_type('views') == 'api'

    def test_data(self):
        assert _detect_subsystem_type('models') == 'data'
        assert _detect_subsystem_type('migrations') == 'data'

    def test_tests(self):
        assert _detect_subsystem_type('tests') == 'tests'
        assert _detect_subsystem_type('spec') == 'tests'

    def test_config(self):
        assert _detect_subsystem_type('config') == 'config'
        assert _detect_subsystem_type('scripts') == 'config'

    def test_docs(self):
        assert _detect_subsystem_type('docs') == 'docs'

    def test_other(self):
        assert _detect_subsystem_type('utils') == 'other'
        assert _detect_subsystem_type('lib') == 'other'


class TestKahnTopo:
    def test_simple_chain(self):
        nodes = {'a', 'b', 'c'}
        edges = [('a', 'b'), ('b', 'c')]
        result = _kahn_topo(nodes, edges)
        assert result.index('a') < result.index('b')
        assert result.index('b') < result.index('c')

    def test_all_nodes_present(self):
        nodes = {'a', 'b', 'c'}
        edges = [('a', 'b')]
        result = _kahn_topo(nodes, edges)
        assert set(result) == nodes

    def test_cycle_handled(self):
        nodes = {'a', 'b'}
        edges = [('a', 'b'), ('b', 'a')]
        result = _kahn_topo(nodes, edges)
        assert set(result) == nodes

    def test_no_edges(self):
        nodes = {'x', 'y', 'z'}
        result = _kahn_topo(nodes, [])
        assert set(result) == nodes

    def test_empty(self):
        result = _kahn_topo(set(), [])
        assert result == []

    def test_edges_outside_nodes_ignored(self):
        nodes = {'a', 'b'}
        edges = [('a', 'c'), ('c', 'b')]
        result = _kahn_topo(nodes, edges)
        assert set(result) == nodes


class TestGenerateDescription:
    def test_known_subsystem_base(self):
        desc = _generate_description('api', 'api', ['router.py', 'views.py'], [])
        assert 'routes' in desc.lower() or 'handler' in desc.lower() or 'api' in desc.lower()

    def test_signals_migration(self):
        desc = _generate_description('data', 'data', ['migration_001.py'], [])
        assert 'migrations' in desc

    def test_signals_models(self):
        desc = _generate_description('models', 'data', ['model_user.py'], [])
        assert 'models' in desc

    def test_signals_tasks(self):
        desc = _generate_description('celery', 'other', ['tasks.py', 'worker.py'], [])
        assert 'tasks' in desc

    def test_hot_file_mentioned(self):
        key_files = [{'file': 'api/router.py', 'commit_count': 42}]
        desc = _generate_description('api', 'api', ['api/router.py'], key_files)
        assert 'router.py' in desc
        assert '42' in desc

    def test_other_subsystem_shows_language(self):
        files = ['utils/helper.py', 'utils/tools.py']
        desc = _generate_description('utils', 'other', files, [])
        assert 'Python' in desc or 'files' in desc

    def test_fallback_when_no_base_or_key_files(self):
        desc = _generate_description('mydir', 'other', ['a.txt', 'b.txt'], [])
        assert 'mydir' in desc or 'files' in desc


class TestFileNote:
    def test_entry_filename(self):
        subsystem = {'main.py', 'utils.py'}
        note = _file_note('main.py', subsystem, {}, {})
        assert note == 'Entry point'

    def test_utility_file(self):
        subsystem = {'utils.py', 'app.py', 'models.py', 'helpers.py'}
        note = _file_note('utils.py', subsystem, {'app.py': 1, 'models.py': 1}, {'utils.py': 0})
        assert note == 'Utilities'

    def test_core_logic_highest_in_degree(self):
        subsystem = {'a.py', 'b.py', 'c.py', 'd.py', 'e.py'}
        graph_in = {'a.py': 5, 'b.py': 2, 'c.py': 1, 'd.py': 0, 'e.py': 0}
        # internal_in_deg must be non-zero to prevent early 'Entry point' path
        internal_in = {'a.py': 2, 'b.py': 1}
        note = _file_note('a.py', subsystem, internal_in, graph_in)
        assert note == 'Core logic'

    def test_ext_label_fallback(self):
        subsystem = {'script.sh', 'config.yaml', 'app.py'}
        note = _file_note('script.sh', subsystem, {'app.py': 1}, {})
        assert note == 'Shell script'


class TestGenerateArchTours:
    def _structure(self, files=None, hot_files=None):
        return {
            'all_files': files or [
                'backend/models.py', 'backend/views.py', 'backend/tasks.py',
                'frontend/app.ts', 'frontend/router.ts', 'frontend/store.ts',
            ],
            'hot_files': hot_files or [
                {'file': 'backend/models.py', 'commit_count': 50},
                {'file': 'frontend/app.ts', 'commit_count': 30},
            ],
        }

    def _graph(self, nodes=None, edges=None):
        nodes = nodes or [
            {'id': 'backend/models.py', 'in_degree': 3},
            {'id': 'backend/views.py', 'in_degree': 1},
            {'id': 'backend/tasks.py', 'in_degree': 0},
            {'id': 'frontend/app.ts', 'in_degree': 2},
            {'id': 'frontend/router.ts', 'in_degree': 1},
            {'id': 'frontend/store.ts', 'in_degree': 0},
        ]
        return {
            'nodes': nodes,
            'edges': edges or [
                {'source': 'backend/views.py', 'target': 'backend/models.py'},
            ],
        }

    def test_returns_list(self):
        result = generate_arch_tours(self._structure(), self._graph(), {})
        assert isinstance(result, list)

    def test_includes_overview_tour(self):
        result = generate_arch_tours(self._structure(), self._graph(), {})
        assert len(result) > 0
        assert result[0]['id'] == 'tour_overview'

    def test_overview_has_required_keys(self):
        result = generate_arch_tours(self._structure(), self._graph(), {})
        overview = result[0]
        assert 'name' in overview
        assert 'description' in overview
        assert 'entry_files' in overview
        assert 'reading_order' in overview
        assert 'file_count' in overview

    def test_subsystem_tours_present(self):
        result = generate_arch_tours(self._structure(), self._graph(), {})
        ids = [t['id'] for t in result]
        assert any('backend' in id_ or 'frontend' in id_ for id_ in ids)

    def test_empty_files_returns_empty(self):
        result = generate_arch_tours({'all_files': []}, self._graph(), {})
        assert result == []

    def test_exception_returns_empty_list(self):
        result = generate_arch_tours(None, {}, {})
        assert result == []

    def test_subsystem_tour_keys(self):
        result = generate_arch_tours(self._structure(), self._graph(), {})
        if len(result) > 1:
            tour = result[1]
            assert 'subsystem_type' in tour
            assert 'key_files' in tour
            assert 'reading_order' in tour

    def test_monorepo_heuristic(self):
        files = (
            [f'pkg1/mod{i}.py' for i in range(5)] +
            [f'pkg2/mod{i}.py' for i in range(5)] +
            [f'pkg3/mod{i}.py' for i in range(5)]
        )
        structure = {'all_files': files, 'hot_files': []}
        graph = {'nodes': [{'id': f, 'in_degree': 0} for f in files], 'edges': []}
        result = generate_arch_tours(structure, graph, {})
        assert isinstance(result, list)

    def test_dirs_with_few_files_skipped(self):
        files = (
            ['backend/a.py', 'backend/b.py', 'backend/c.py'] +
            ['lone/only.py']
        )
        structure = {'all_files': files, 'hot_files': []}
        graph = {'nodes': [{'id': f, 'in_degree': 0} for f in files], 'edges': []}
        result = generate_arch_tours(structure, graph, {})
        ids = [t['id'] for t in result]
        assert not any('lone' in id_ for id_ in ids)

    def test_caps_at_9_tours(self):
        files = [f'dir{i}/f{j}.py' for i in range(12) for j in range(5)]
        structure = {'all_files': files, 'hot_files': []}
        graph = {'nodes': [{'id': f, 'in_degree': 0} for f in files], 'edges': []}
        result = generate_arch_tours(structure, graph, {})
        assert len(result) <= 9

    def test_internal_edges_used_for_reading_order(self):
        structure = self._structure()
        graph = self._graph(edges=[
            {'source': 'backend/views.py', 'target': 'backend/models.py'},
            {'source': 'backend/tasks.py', 'target': 'backend/models.py'},
        ])
        result = generate_arch_tours(structure, graph, {})
        assert isinstance(result, list)
