import pytest
from apps.analysis.ownership_analysis import _primary_language, analyze_ownership


def _structure(**kw):
    base = {
        'all_files': [
            'backend/models.py', 'backend/views.py', 'backend/tasks.py',
            'backend/admin.py', 'backend/urls.py',
            'frontend/app.ts', 'frontend/router.ts', 'frontend/store.ts',
            'frontend/main.ts', 'frontend/utils.ts',
        ],
        'hot_files': [
            {'file': 'backend/models.py', 'commit_count': 50},
            {'file': 'backend/views.py', 'commit_count': 30},
            {'file': 'frontend/app.ts', 'commit_count': 20},
        ],
        'top_contributors': [{'author': 'alice', 'email': 'a@test.com', 'files_touched': 20}],
        'bus_factor': 2,
    }
    base.update(kw)
    return base


def _graph(**kw):
    base = {'god_modules': [], 'cycle_count': 0}
    base.update(kw)
    return base


class TestPrimaryLanguage:
    def test_python_files(self):
        files = ['app.py', 'models.py', 'views.py']
        assert _primary_language(files) == 'Python'

    def test_typescript_files(self):
        files = ['app.ts', 'router.ts', 'store.ts']
        assert _primary_language(files) == 'TypeScript'

    def test_mixed_returns_dominant(self):
        files = ['a.py', 'b.py', 'c.py', 'main.ts']
        assert _primary_language(files) == 'Python'

    def test_no_known_extension(self):
        files = ['README.md', 'config.txt', 'notes']
        result = _primary_language(files)
        assert result == ''

    def test_empty_list(self):
        assert _primary_language([]) == ''

    def test_files_without_extension(self):
        files = ['Makefile', 'LICENSE', 'README']
        assert _primary_language(files) == ''


class TestAnalyzeOwnership:
    def test_returns_subsystems(self):
        result = analyze_ownership(_structure(), {}, _graph())
        assert 'subsystems' in result
        assert 'bus_factor' in result
        assert 'top_contributors' in result

    def test_empty_files_returns_empty(self):
        result = analyze_ownership(_structure(all_files=[]), {}, _graph())
        assert result == {}

    def test_subsystem_has_required_keys(self):
        result = analyze_ownership(_structure(), {}, _graph())
        assert len(result['subsystems']) > 0
        sub = result['subsystems'][0]
        assert 'id' in sub
        assert 'name' in sub
        assert 'subsystem_type' in sub
        assert 'file_count' in sub
        assert 'activity_score' in sub
        assert 'hot_files' in sub
        assert 'god_modules' in sub
        assert 'primary_language' in sub

    def test_dirs_with_few_files_excluded(self):
        files = (
            ['backend/a.py', 'backend/b.py', 'backend/c.py', 'backend/d.py', 'backend/e.py'] +
            ['small/only.py']
        )
        result = analyze_ownership(
            _structure(all_files=files, hot_files=[]),
            {}, _graph()
        )
        subsystem_ids = [s['id'] for s in result['subsystems']]
        assert not any('small' in id_ for id_ in subsystem_ids)

    def test_hot_files_within_subsystem(self):
        result = analyze_ownership(_structure(), {}, _graph())
        backend_sub = next((s for s in result['subsystems'] if 'backend' in s['id']), None)
        if backend_sub:
            assert any(h['file'].startswith('backend/') for h in backend_sub['hot_files'])

    def test_god_modules_within_subsystem(self):
        god_mods = [{'module': 'backend/models.py', 'in_degree': 10}]
        result = analyze_ownership(_structure(), {}, _graph(god_modules=god_mods))
        backend_sub = next((s for s in result['subsystems'] if 'backend' in s['id']), None)
        if backend_sub:
            assert len(backend_sub['god_modules']) > 0

    def test_activity_score_is_fraction(self):
        result = analyze_ownership(_structure(), {}, _graph())
        for sub in result['subsystems']:
            assert 0 <= sub['activity_score'] <= 1

    def test_bus_factor_from_structure(self):
        result = analyze_ownership(_structure(bus_factor=3), {}, _graph())
        assert result['bus_factor'] == 3

    def test_caps_at_10_subsystems(self):
        files = [f'dir{i}/file{j}.py' for i in range(15) for j in range(6)]
        result = analyze_ownership(_structure(all_files=files, hot_files=[]), {}, _graph())
        assert len(result['subsystems']) <= 10

    def test_exception_returns_empty_dict(self):
        result = analyze_ownership(None, {}, _graph())
        assert result == {}

    def test_monorepo_heuristic(self):
        files = (
            [f'pkg1/mod{i}.py' for i in range(6)] +
            [f'pkg2/mod{i}.py' for i in range(6)] +
            [f'pkg3/mod{i}.py' for i in range(6)]
        )
        result = analyze_ownership(
            _structure(all_files=files, hot_files=[]),
            {}, _graph()
        )
        assert isinstance(result['subsystems'], list)
