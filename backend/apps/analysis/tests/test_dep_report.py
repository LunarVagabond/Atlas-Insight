import json
import tempfile
from pathlib import Path

import pytest
from apps.analysis.dep_report import (
    _parse_build_gradle,
    _parse_cargo_toml,
    _parse_composer_json,
    _parse_gemfile,
    _parse_go_mod,
    _parse_package_json,
    _parse_pom_xml,
    _parse_pyproject_toml,
    _parse_requirements_txt,
    _scan_dockerfiles,
    _should_skip,
    analyze_dependencies,
)


class TestShouldSkip:
    def test_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = base / 'node_modules' / 'lib.js'
            p.parent.mkdir()
            p.touch()
            assert _should_skip(p, base) is True

    def test_allows_normal_path(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = base / 'src' / 'main.py'
            p.parent.mkdir()
            p.touch()
            assert _should_skip(p, base) is False


class TestParseRequirementsTxt:
    def test_basic_dep(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'requirements.txt'
            p.write_text('django>=4.0\ncelery==5.3.0\n')
            deps = _parse_requirements_txt(p)
        assert len(deps) == 2
        assert deps[0]['name'] == 'django'
        assert deps[0]['version_spec'] == '>=4.0'

    def test_skips_comments_and_flags(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'requirements.txt'
            p.write_text('# comment\n-r other.txt\nrequests\n')
            deps = _parse_requirements_txt(p)
        assert len(deps) == 1
        assert deps[0]['name'] == 'requests'

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'requirements.txt'
            p.write_text('')
            deps = _parse_requirements_txt(p)
        assert deps == []

    def test_no_version_spec(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'requirements.txt'
            p.write_text('flask\n')
            deps = _parse_requirements_txt(p)
        assert deps[0]['version_spec'] == ''


class TestParsePackageJson:
    def test_parses_deps_and_devdeps(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text(json.dumps({
                'dependencies': {'vue': '^3.0.0'},
                'devDependencies': {'vitest': '^1.0.0'},
            }))
            deps = _parse_package_json(p)
        names = [d['name'] for d in deps]
        assert 'vue' in names
        assert 'vitest' in names
        dev_dep = next(d for d in deps if d['name'] == 'vitest')
        assert dev_dep['dev'] is True

    def test_invalid_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text('not valid json')
            deps = _parse_package_json(p)
        assert deps == []

    def test_empty_sections(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'package.json'
            p.write_text(json.dumps({'name': 'myapp'}))
            deps = _parse_package_json(p)
        assert deps == []


class TestParseGoMod:
    def test_parses_require_block(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'go.mod'
            p.write_text('module myapp\ngo 1.21\n\nrequire (\n    github.com/gin-gonic/gin v1.9.0\n    github.com/stretchr/testify v1.8.4\n)\n')
            deps = _parse_go_mod(p)
        names = [d['name'] for d in deps]
        assert 'github.com/gin-gonic/gin' in names

    def test_parses_single_require(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'go.mod'
            p.write_text('module myapp\nrequire github.com/some/pkg v1.0.0\n')
            deps = _parse_go_mod(p)
        assert len(deps) == 1
        assert deps[0]['version_spec'] == 'v1.0.0'

    def test_ignores_comments_in_block(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'go.mod'
            p.write_text('module myapp\nrequire (\n    // indirect\n    github.com/pkg v1.0.0\n)\n')
            deps = _parse_go_mod(p)
        assert all(not d['name'].startswith('//') for d in deps)


class TestParseCargoToml:
    def test_parses_deps(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'Cargo.toml'
            p.write_text('[dependencies]\nserde = "1.0"\ntokio = { version = "1.28" }\n')
            deps = _parse_cargo_toml(p)
        names = [d['name'] for d in deps]
        assert 'serde' in names
        assert 'tokio' in names

    def test_dev_dependencies_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'Cargo.toml'
            p.write_text('[dev-dependencies]\nassert_matches = "1.5"\n')
            deps = _parse_cargo_toml(p)
        assert deps[0]['dev'] is True

    def test_invalid_toml_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'Cargo.toml'
            p.write_text('not valid toml {{{}')
            deps = _parse_cargo_toml(p)
        assert deps == []


class TestParsePyprojectToml:
    def test_pep621_deps(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'pyproject.toml'
            p.write_text('[project]\ndependencies = [\n  "django>=4.0",\n  "celery>=5.0",\n]\n')
            deps = _parse_pyproject_toml(p)
        names = [d['name'] for d in deps]
        assert 'django' in names
        assert 'celery' in names

    def test_poetry_deps(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'pyproject.toml'
            p.write_text('[tool.poetry.dependencies]\npython = "^3.11"\nrequests = "^2.28"\n')
            deps = _parse_pyproject_toml(p)
        names = [d['name'] for d in deps]
        assert 'requests' in names
        assert 'python' not in names

    def test_invalid_toml_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'pyproject.toml'
            p.write_text('invalid = {{{')
            deps = _parse_pyproject_toml(p)
        assert deps == []


class TestParseGemfile:
    def test_parses_gems(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'Gemfile'
            p.write_text("source 'https://rubygems.org'\ngem 'rails', '~> 7.0'\ngem 'pg'\n")
            deps = _parse_gemfile(p)
        names = [d['name'] for d in deps]
        assert 'rails' in names
        assert 'pg' in names

    def test_version_spec_captured(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'Gemfile'
            p.write_text("gem 'rails', '~> 7.0'\n")
            deps = _parse_gemfile(p)
        assert deps[0]['version_spec'] == '~> 7.0'


class TestParseComposerJson:
    def test_parses_require(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'composer.json'
            p.write_text(json.dumps({
                'require': {'laravel/framework': '^10.0', 'php': '^8.1'},
                'require-dev': {'phpunit/phpunit': '^10.0'},
            }))
            deps = _parse_composer_json(p)
        names = [d['name'] for d in deps]
        assert 'laravel/framework' in names
        assert 'php' not in names
        assert 'phpunit/phpunit' in names

    def test_invalid_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'composer.json'
            p.write_text('broken')
            deps = _parse_composer_json(p)
        assert deps == []

    def test_ext_packages_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'composer.json'
            p.write_text(json.dumps({'require': {'ext-json': '*', 'mylib/pkg': '1.0'}}))
            deps = _parse_composer_json(p)
        names = [d['name'] for d in deps]
        assert 'ext-json' not in names


class TestParsePomXml:
    def test_parses_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'pom.xml'
            p.write_text('''<project>
<dependencies>
<dependency>
<groupId>org.springframework</groupId>
<artifactId>spring-core</artifactId>
<version>5.3.0</version>
</dependency>
</dependencies>
</project>''')
            deps = _parse_pom_xml(p)
        assert len(deps) >= 1
        assert 'org.springframework/spring-core' in [d['name'] for d in deps]


class TestParseBuildGradle:
    def test_parses_implementation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'build.gradle'
            p.write_text("dependencies {\n    implementation 'com.google.guava:guava:31.0-jre'\n    testImplementation 'junit:junit:4.13'\n}\n")
            deps = _parse_build_gradle(p)
        names = [d['name'] for d in deps]
        assert 'com.google.guava/guava' in names


class TestScanDockerfiles:
    def test_no_dockerfiles(self):
        with tempfile.TemporaryDirectory() as d:
            result = _scan_dockerfiles(d)
        assert result == []

    def test_deprecated_base_image(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'Dockerfile').write_text('FROM python:3.6\nRUN pip install app\n')
            result = _scan_dockerfiles(d)
        assert len(result) == 1
        assert 'Deprecated' in result[0]['issue']

    def test_modern_base_image(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'Dockerfile').write_text('FROM python:3.12\nRUN pip install app\n')
            result = _scan_dockerfiles(d)
        assert result == []

    def test_ubuntu_old(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'Dockerfile').write_text('FROM ubuntu:18.04\n')
            result = _scan_dockerfiles(d)
        assert len(result) == 1

    def test_skips_venv(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / '.venv').mkdir()
            (Path(d) / '.venv' / 'Dockerfile').write_text('FROM python:3.6\n')
            result = _scan_dockerfiles(d)
        assert result == []


class TestAnalyzeDependencies:
    def test_full_python_project(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'requirements.txt').write_text('django>=4.0\ncelery\n')
            result = analyze_dependencies(d)
        assert result['dependency_count'] == 2
        assert result['docker_issues'] == []

    def test_lockfile_warning_python(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'requirements.txt').write_text('django\n')
            result = analyze_dependencies(d)
        assert len(result['missing_lockfile_warnings']) == 1

    def test_lockfile_warning_node(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'package.json').write_text(json.dumps({'name': 'app', 'dependencies': {'vue': '^3'}}))
            result = analyze_dependencies(d)
        assert any('Node' in w for w in result['missing_lockfile_warnings'])

    def test_no_lockfile_warning_when_lockfile_present(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'requirements.txt').write_text('django\n')
            (Path(d) / 'poetry.lock').write_text('')
            result = analyze_dependencies(d)
        assert not any('Python' in w for w in result['missing_lockfile_warnings'])

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            result = analyze_dependencies(d)
        assert result['dependency_count'] == 0
        assert result['dependencies'] == []

    def test_go_mod(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'go.mod').write_text('module myapp\nrequire github.com/gin-gonic/gin v1.9.0\n')
            result = analyze_dependencies(d)
        assert result['dependency_count'] == 1

    def test_skips_venv_package_json(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / '.venv').mkdir()
            (Path(d) / '.venv' / 'package.json').write_text(json.dumps({'dependencies': {'x': '1'}}))
            result = analyze_dependencies(d)
        assert result['dependency_count'] == 0
