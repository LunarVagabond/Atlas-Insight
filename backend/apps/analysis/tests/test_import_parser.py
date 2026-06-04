import os
import tempfile
from pathlib import Path

import pytest
from apps.analysis.import_parser import (
    _is_external_cs,
    _is_external_elixir,
    _is_external_go,
    _is_external_java,
    _is_external_js,
    _is_external_python,
    _is_external_ruby,
    _is_external_scala,
    _is_external_swift,
    _read_go_module_path,
    parse_imports,
)


class TestIsExternalPython:
    def test_stdlib_module(self):
        assert _is_external_python('os') is True
        assert _is_external_python('sys') is True
        assert _is_external_python('json') is True

    def test_third_party(self):
        assert _is_external_python('django') is False
        assert _is_external_python('mypackage') is False


class TestIsExternalJs:
    def test_relative_import(self):
        assert _is_external_js('./utils') is False
        assert _is_external_js('../components/Button') is False

    def test_package_import(self):
        assert _is_external_js('react') is True
        assert _is_external_js('vue') is True


class TestIsExternalJava:
    def test_stdlib(self):
        assert _is_external_java('java.util.List') is True
        assert _is_external_java('javax.servlet.Filter') is True
        assert _is_external_java('sun.misc.Unsafe') is True

    def test_custom(self):
        assert _is_external_java('com.mycompany.MyClass') is False


class TestIsExternalCs:
    def test_stdlib(self):
        assert _is_external_cs('System.Collections.Generic') is True
        assert _is_external_cs('Microsoft.AspNetCore') is True

    def test_custom(self):
        assert _is_external_cs('MyApp.Controllers') is False


class TestIsExternalRuby:
    def test_stdlib(self):
        assert _is_external_ruby('json') is True
        assert _is_external_ruby('csv') is True

    def test_gem(self):
        assert _is_external_ruby('rails') is False


class TestIsExternalSwift:
    def test_stdlib(self):
        assert _is_external_swift('Foundation') is True
        assert _is_external_swift('UIKit') is True

    def test_custom(self):
        assert _is_external_swift('MyCustomFramework') is False


class TestIsExternalScala:
    def test_stdlib(self):
        assert _is_external_scala('scala.collection.mutable') is True
        assert _is_external_scala('java.util.List') is True

    def test_custom(self):
        assert _is_external_scala('com.mycompany.service') is False


class TestIsExternalElixir:
    def test_stdlib(self):
        assert _is_external_elixir('Enum') is True
        assert _is_external_elixir('GenServer') is True

    def test_custom(self):
        assert _is_external_elixir('MyApp.Repo') is False


class TestIsExternalGo:
    def test_stdlib_no_slash(self):
        assert _is_external_go('fmt', None) is True
        assert _is_external_go('os', None) is True

    def test_golang_org(self):
        assert _is_external_go('golang.org/x/net', None) is True

    def test_internal_with_module_path(self):
        assert _is_external_go('github.com/myorg/myapp/internal', 'github.com/myorg/myapp') is False

    def test_external_different_module(self):
        assert _is_external_go('github.com/other/pkg', 'github.com/myorg/myapp') is True

    def test_no_module_path_with_slash(self):
        assert _is_external_go('github.com/something/pkg', None) is False


class TestReadGoModulePath:
    def test_reads_module_path(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'go.mod').write_text('module github.com/myorg/myapp\n\ngo 1.21\n')
            result = _read_go_module_path(d)
        assert result == 'github.com/myorg/myapp'

    def test_no_go_mod(self):
        with tempfile.TemporaryDirectory() as d:
            result = _read_go_module_path(d)
        assert result is None


class TestParseImports:
    def test_python_imports(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'main.py').write_text(
                'from mypackage.utils import helper\nimport mypackage.models\n'
            )
            edges = parse_imports(d)
        targets = [e['target'] for e in edges]
        assert 'mypackage.utils' in targets
        assert 'mypackage.models' in targets

    def test_python_stdlib_filtered(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'main.py').write_text('import os\nimport sys\nfrom json import dumps\n')
            edges = parse_imports(d)
        assert len(edges) == 0

    def test_js_relative_imports(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'app.js').write_text(
                "import { helper } from './utils';\nconst x = require('./components/Btn');\n"
            )
            edges = parse_imports(d)
        targets = [e['target'] for e in edges]
        assert './utils' in targets
        assert './components/Btn' in targets

    def test_js_package_imports_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'app.js').write_text("import React from 'react';\n")
            edges = parse_imports(d)
        assert len(edges) == 0

    def test_ts_file(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'app.ts').write_text("import { foo } from './foo';\n")
            edges = parse_imports(d)
        assert len(edges) == 1
        assert edges[0]['lang'] == 'js'

    def test_vue_file_script_block(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'App.vue').write_text(
                "<template><div/></template>\n"
                "<script>\nimport { helper } from './helper';\n</script>\n"
            )
            edges = parse_imports(d)
        assert len(edges) == 1
        assert edges[0]['lang'] == 'js'

    def test_vue_no_script_block(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'App.vue').write_text('<template><div/></template>\n')
            edges = parse_imports(d)
        assert len(edges) == 0

    def test_rust_use(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'main.rs').write_text('use crate::utils::helper;\nuse super::models;\n')
            edges = parse_imports(d)
        langs = {e['lang'] for e in edges}
        assert 'rust' in langs

    def test_ruby_require(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'app.rb').write_text("require 'mylib'\nrequire 'csv'\n")
            edges = parse_imports(d)
        targets = [e['target'] for e in edges]
        assert 'mylib' in targets
        assert 'csv' not in targets

    def test_go_imports(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'go.mod').write_text('module github.com/myorg/myapp\n')
            (Path(d) / 'main.go').write_text(
                'package main\n\nimport (\n    "github.com/myorg/myapp/internal"\n    "fmt"\n)\n'
            )
            edges = parse_imports(d)
        assert len(edges) == 1
        assert edges[0]['lang'] == 'go'

    def test_skips_large_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'big.py'
            p.write_text('from mypackage import thing\n' + 'x' * 600_000)
            edges = parse_imports(d)
        assert len(edges) == 0

    def test_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'node_modules').mkdir()
            (Path(d) / 'node_modules' / 'lib.js').write_text("import x from './internal';")
            edges = parse_imports(d)
        assert len(edges) == 0

    def test_java_imports(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'App.java').write_text(
                'import com.mycompany.model.User;\nimport java.util.List;\n'
            )
            edges = parse_imports(d)
        targets = [e['target'] for e in edges]
        assert 'com.mycompany.model.User' in targets
        assert not any('java.util' in t for t in targets)

    def test_kotlin_imports(self):
        # Kotlin uses same regex as Java which requires a trailing semicolon
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'App.kt').write_text('import com.mycompany.model.User;\n')
            edges = parse_imports(d)
        assert len(edges) == 1
        assert edges[0]['lang'] == 'kotlin'

    def test_csharp_using(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'App.cs').write_text('using MyApp.Controllers;\nusing System.Linq;\n')
            edges = parse_imports(d)
        targets = [e['target'] for e in edges]
        assert 'MyApp.Controllers' in targets
        assert 'System.Linq' not in targets

    def test_dart_package_imports(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'app.dart').write_text(
                "import 'package:myapp/utils.dart';\nimport 'dart:io';\n"
            )
            edges = parse_imports(d)
        assert len(edges) == 1
        assert edges[0]['target'] == 'myapp'

    def test_elixir_alias(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'app.ex').write_text('alias MyApp.Repo\nalias Enum\n')
            edges = parse_imports(d)
        targets = [e['target'] for e in edges]
        assert 'MyApp.Repo' in targets
        assert 'Enum' not in targets
