import json
import tempfile
from pathlib import Path

import pytest
from apps.analysis.repo_type import (
    _classify,
    _count_docker_compose_services,
    _dep_files_in_dir,
    _is_real_package_json,
    _quick_languages,
    detect_repo_type,
    SubProject,
)


def _make_sp(name: str) -> SubProject:
    return SubProject(name=name, path=name + '/', abs_path='/tmp/' + name)


class TestIsRealPackageJson:
    def test_with_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text(json.dumps({'name': 'myapp', 'dependencies': {'vue': '^3'}}))
            assert _is_real_package_json(p) is True

    def test_workspace_only_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text(json.dumps({'workspaces': ['packages/*']}))
            assert _is_real_package_json(p) is False

    def test_workspace_with_deps_included(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text(json.dumps({'workspaces': ['packages/*'], 'dependencies': {'vue': '^3'}}))
            assert _is_real_package_json(p) is True

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text('not json')
            assert _is_real_package_json(p) is False

    def test_name_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text(json.dumps({'name': 'myapp'}))
            assert _is_real_package_json(p) is True


class TestDepFilesInDir:
    def test_finds_requirements_txt(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'requirements.txt').write_text('django')
            result = _dep_files_in_dir(Path(d))
        assert 'requirements.txt' in result

    def test_finds_pyproject_toml(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'pyproject.toml').write_text('[project]')
            result = _dep_files_in_dir(Path(d))
        assert 'pyproject.toml' in result

    def test_finds_package_json(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {}}))
            result = _dep_files_in_dir(Path(d))
        assert 'package.json' in result

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            result = _dep_files_in_dir(Path(d))
        assert result == []

    def test_finds_go_mod(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'go.mod').write_text('module myapp')
            result = _dep_files_in_dir(Path(d))
        assert 'go.mod' in result


class TestClassify:
    def test_no_sub_roots_is_single(self):
        repo_type, _ = _classify('/tmp', [], False)
        assert repo_type == 'single'

    def test_frontend_and_backend_dirs_is_fullstack(self):
        sub_roots = [_make_sp('frontend'), _make_sp('backend')]
        repo_type, detected_by = _classify('/tmp', sub_roots, False)
        assert repo_type == 'fullstack'
        assert 'frontend_backend_dirs' in detected_by

    def test_client_and_server_dirs_is_fullstack(self):
        sub_roots = [_make_sp('client'), _make_sp('server')]
        repo_type, _ = _classify('/tmp', sub_roots, False)
        assert repo_type == 'fullstack'

    def test_many_sub_roots_is_monorepo(self):
        sub_roots = [_make_sp(f'svc{i}') for i in range(4)]
        repo_type, detected_by = _classify('/tmp', sub_roots, False)
        assert repo_type == 'monorepo'
        assert 'multiple_dep_roots' in detected_by

    def test_workspace_config_is_monorepo(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'nx.json').write_text('{}')
            sub_roots = [_make_sp('pkg1'), _make_sp('pkg2')]
            repo_type, detected_by = _classify(d, sub_roots, False)
        assert repo_type == 'monorepo'
        assert 'workspace_config' in detected_by

    def test_packages_dir_with_2_siblings_is_monorepo(self):
        sub_roots = [
            SubProject('packages/core', 'packages/core/', '/tmp/packages/core'),
            SubProject('packages/utils', 'packages/utils/', '/tmp/packages/utils'),
        ]
        repo_type, detected_by = _classify('/tmp', sub_roots, False)
        assert repo_type == 'monorepo'
        assert 'packages_dir' in detected_by

    def test_two_unrelated_dirs_is_single(self):
        sub_roots = [_make_sp('lib1'), _make_sp('lib2')]
        repo_type, _ = _classify('/tmp', sub_roots, False)
        assert repo_type == 'single'


class TestCountDockerComposeServices:
    def test_no_compose_file(self):
        with tempfile.TemporaryDirectory() as d:
            assert _count_docker_compose_services(d) == 0

    def test_counts_services_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            content = 'services:\n  web:\n    image: nginx\n  db:\n    image: postgres\n'
            (Path(d) / 'docker-compose.yml').write_text(content)
            count = _count_docker_compose_services(d)
        assert count == 2

    def test_yaml_extension(self):
        with tempfile.TemporaryDirectory() as d:
            content = 'services:\n  web:\n    image: nginx\n  redis:\n    image: redis\n  db:\n    image: postgres\n'
            (Path(d) / 'docker-compose.yaml').write_text(content)
            count = _count_docker_compose_services(d)
        assert count == 3


class TestQuickLanguages:
    def test_python_files(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(5):
                (Path(d) / f'file{i}.py').write_text('pass')
            langs = _quick_languages(d)
        assert 'Python' in langs

    def test_mixed_languages(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(7):
                (Path(d) / f'file{i}.py').write_text('pass')
            for i in range(3):
                (Path(d) / f'file{i}.ts').write_text('export {}')
            langs = _quick_languages(d)
        assert 'Python' in langs
        assert 'TypeScript' in langs

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            langs = _quick_languages(d)
        assert langs == []

    def test_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'node_modules').mkdir()
            for i in range(10):
                (Path(d) / 'node_modules' / f'f{i}.js').write_text('x')
            (Path(d) / 'main.py').write_text('pass')
            langs = _quick_languages(d)
        assert 'JavaScript' not in langs
        assert 'Python' in langs


class TestDetectRepoType:
    def test_single_repo(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'requirements.txt').write_text('django')
            result = detect_repo_type(d)
        assert result['type'] == 'single'
        assert result['sub_projects'] == []

    def test_fullstack_repo(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'backend').mkdir()
            (Path(d) / 'backend' / 'requirements.txt').write_text('django')
            (Path(d) / 'frontend').mkdir()
            (Path(d) / 'frontend' / 'package.json').write_text(
                json.dumps({'name': 'app', 'dependencies': {'vue': '^3'}})
            )
            result = detect_repo_type(d)
        assert result['type'] == 'fullstack'
        assert len(result['sub_projects']) == 2

    def test_monorepo_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'nx.json').write_text('{}')
            (Path(d) / 'packages').mkdir()
            (Path(d) / 'packages' / 'core').mkdir()
            (Path(d) / 'packages' / 'core' / 'package.json').write_text(
                json.dumps({'name': 'core', 'dependencies': {}})
            )
            (Path(d) / 'packages' / 'utils').mkdir()
            (Path(d) / 'packages' / 'utils' / 'package.json').write_text(
                json.dumps({'name': 'utils', 'dependencies': {}})
            )
            result = detect_repo_type(d)
        assert result['type'] == 'monorepo'

    def test_empty_dir_returns_single(self):
        with tempfile.TemporaryDirectory() as d:
            result = detect_repo_type(d)
        assert result['type'] == 'single'

    def test_sub_projects_have_languages(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'backend').mkdir()
            (Path(d) / 'backend' / 'requirements.txt').write_text('django')
            (Path(d) / 'backend' / 'app.py').write_text('pass')
            (Path(d) / 'frontend').mkdir()
            (Path(d) / 'frontend' / 'package.json').write_text(
                json.dumps({'name': 'app', 'dependencies': {'vue': '^3'}})
            )
            (Path(d) / 'frontend' / 'main.ts').write_text('export {}')
            result = detect_repo_type(d)
        backend = next(sp for sp in result['sub_projects'] if sp['name'] == 'backend')
        assert 'Python' in backend['languages']
