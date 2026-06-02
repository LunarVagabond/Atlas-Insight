import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── todo_scan ─────────────────────────────────────────────────────────────────

class TestScanTodos:
    def test_finds_todo_in_py(self):
        from apps.analysis.todo_scan import scan_todos
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'main.py').write_text('# TODO: refactor this\nx = 1\n')
            result = scan_todos(d)
        assert result['total'] == 1
        assert result['by_type']['TODO'] == 1
        assert result['items'][0]['type'] == 'TODO'
        assert result['items'][0]['line'] == 1

    def test_finds_fixme_and_bug(self):
        from apps.analysis.todo_scan import scan_todos
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'app.js').write_text('// FIXME: broken\n// BUG: crash here\n')
            result = scan_todos(d)
        assert result['total'] == 2
        assert 'FIXME' in result['by_type']
        assert 'BUG' in result['by_type']

    def test_skips_non_source_files(self):
        from apps.analysis.todo_scan import scan_todos
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'notes.md').write_text('# TODO: write docs\n')
            result = scan_todos(d)
        assert result['total'] == 0

    def test_skips_node_modules(self):
        from apps.analysis.todo_scan import scan_todos
        with tempfile.TemporaryDirectory() as d:
            nm = Path(d) / 'node_modules'
            nm.mkdir()
            (nm / 'lib.js').write_text('// TODO: upstream fix\n')
            (Path(d) / 'index.js').write_text('// real code\n')
            result = scan_todos(d)
        assert result['total'] == 0

    def test_captures_text(self):
        from apps.analysis.todo_scan import scan_todos
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'svc.py').write_text('# HACK: workaround for bug #42\n')
            result = scan_todos(d)
        assert 'workaround for bug #42' in result['items'][0]['text']

    def test_empty_directory(self):
        from apps.analysis.todo_scan import scan_todos
        with tempfile.TemporaryDirectory() as d:
            result = scan_todos(d)
        assert result == {'total': 0, 'by_type': {}, 'items': []}


# ── security_scan ─────────────────────────────────────────────────────────────

class TestScanSecurity:
    def _mock_repo(self, tracked_files=None):
        repo = MagicMock()
        repo.git.ls_files.return_value = '\n'.join(tracked_files or [])
        repo.git.log.return_value = 'abc123|||Alice'
        return repo

    def test_no_sensitive_files_clean(self):
        from apps.analysis.security_scan import scan_security
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / '.gitignore').write_text('.env\n*.pem\n*.key\nid_rsa\nnode_modules\n__pycache__\n.venv\nvenv\n*.log\ndist/\n')
            repo = self._mock_repo(['README.md', 'main.py'])
            result = scan_security(repo, d)
        assert result['gitignore_exists'] is True
        sensitive = [i for i in result['issues'] if i['type'] == 'sensitive_file_committed']
        assert len(sensitive) == 0

    def test_env_file_detected(self):
        from apps.analysis.security_scan import scan_security
        with tempfile.TemporaryDirectory() as d:
            repo = self._mock_repo(['.env'])
            result = scan_security(repo, d)
        sensitive = [i for i in result['issues'] if i['type'] == 'sensitive_file_committed']
        assert len(sensitive) == 1
        assert sensitive[0]['severity'] == 'high'

    def test_pem_file_detected(self):
        from apps.analysis.security_scan import scan_security
        with tempfile.TemporaryDirectory() as d:
            repo = self._mock_repo(['server.pem'])
            result = scan_security(repo, d)
        sensitive = [i for i in result['issues'] if i['type'] == 'sensitive_file_committed']
        assert any('pem' in i['detail'].lower() or 'key' in i['detail'].lower() for i in sensitive)

    def test_example_env_not_flagged(self):
        from apps.analysis.security_scan import scan_security
        with tempfile.TemporaryDirectory() as d:
            repo = self._mock_repo(['.env.example'])
            result = scan_security(repo, d)
        sensitive = [i for i in result['issues'] if i['type'] == 'sensitive_file_committed']
        assert len(sensitive) == 0

    def test_missing_gitignore_flagged(self):
        from apps.analysis.security_scan import scan_security
        with tempfile.TemporaryDirectory() as d:
            repo = self._mock_repo([])
            result = scan_security(repo, d)
        assert result['gitignore_exists'] is False
        assert any(i['type'] == 'no_gitignore' for i in result['issues'])

    def test_gitignore_gaps_detected(self):
        from apps.analysis.security_scan import scan_security
        with tempfile.TemporaryDirectory() as d:
            # Gitignore missing most patterns
            (Path(d) / '.gitignore').write_text('# empty\n')
            repo = self._mock_repo([])
            result = scan_security(repo, d)
        assert len(result['gitignore_gaps']) > 0

    def test_score_increases_with_issues(self):
        from apps.analysis.security_scan import scan_security
        with tempfile.TemporaryDirectory() as d:
            repo_clean = self._mock_repo([])
            (Path(d) / '.gitignore').write_text('.env\n*.pem\n*.key\nid_rsa\nnode_modules\n__pycache__\n.venv\nvenv\n*.log\ndist/\n')
            result_clean = scan_security(repo_clean, d)

        with tempfile.TemporaryDirectory() as d2:
            repo_dirty = self._mock_repo(['.env', 'server.pem'])
            result_dirty = scan_security(repo_dirty, d2)

        assert result_dirty['score'] > result_clean['score']


# ── vuln_scan ─────────────────────────────────────────────────────────────────

class TestExtractVersion:
    def test_exact_pin(self):
        from apps.analysis.vuln_scan import _extract_version
        assert _extract_version('==2.0.0') == '2.0.0'

    def test_gte(self):
        from apps.analysis.vuln_scan import _extract_version
        assert _extract_version('>=1.5.0') == '1.5.0'

    def test_bare_version(self):
        from apps.analysis.vuln_scan import _extract_version
        assert _extract_version('3.1.2') == '3.1.2'

    def test_range_takes_lower_bound(self):
        from apps.analysis.vuln_scan import _extract_version
        assert _extract_version('>=1.0.0,<2.0.0') == '1.0.0'

    def test_star_returns_empty(self):
        from apps.analysis.vuln_scan import _extract_version
        assert _extract_version('*') == ''

    def test_empty_returns_empty(self):
        from apps.analysis.vuln_scan import _extract_version
        assert _extract_version('') == ''


class TestIsOpenRange:
    def test_gte_is_range(self):
        from apps.analysis.vuln_scan import _is_open_range
        assert _is_open_range('>=2.0.0') is True

    def test_gt_is_range(self):
        from apps.analysis.vuln_scan import _is_open_range
        assert _is_open_range('>2.0.0') is True

    def test_tilde_eq_is_range(self):
        from apps.analysis.vuln_scan import _is_open_range
        assert _is_open_range('~=2.0.0') is True

    def test_caret_is_range(self):
        from apps.analysis.vuln_scan import _is_open_range
        assert _is_open_range('^2.0.0') is True

    def test_exact_pin_not_range(self):
        from apps.analysis.vuln_scan import _is_open_range
        assert _is_open_range('==2.0.0') is False

    def test_bare_version_not_range(self):
        from apps.analysis.vuln_scan import _is_open_range
        assert _is_open_range('2.0.0') is False

    def test_empty_not_range(self):
        from apps.analysis.vuln_scan import _is_open_range
        assert _is_open_range('') is False


class TestScanVulnerabilities:
    def test_empty_deps_returns_empty(self):
        from apps.analysis.vuln_scan import scan_vulnerabilities
        result = scan_vulnerabilities({'dependencies': []})
        assert result == []

    def test_range_result_has_note(self):
        from apps.analysis.vuln_scan import scan_vulnerabilities
        osv_batch = {'results': [{'vulns': [{'id': 'GHSA-test-1234-abcd'}]}]}
        osv_detail = {
            'summary': 'Test vuln',
            'database_specific': {'severity': 'HIGH'},
            'severity': [],
        }
        deps = {
            'dependencies': [{
                'name': 'vulnerable-pkg',
                'version_spec': '>=1.0.0',
                'source': 'requirements.txt',
            }]
        }
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = osv_batch
            mock_post.return_value.raise_for_status = MagicMock()
            mock_get.return_value.ok = True
            mock_get.return_value.json.return_value = osv_detail
            result = scan_vulnerabilities(deps)

        assert len(result) == 1
        assert result[0]['version_is_range'] is True
        assert result[0]['note'] is not None
        assert '>=1.0.0' in result[0]['note']
        assert result[0]['version'] == '>=1.0.0'

    def test_pinned_result_has_no_note(self):
        from apps.analysis.vuln_scan import scan_vulnerabilities
        osv_batch = {'results': [{'vulns': [{'id': 'GHSA-test-5678-efgh'}]}]}
        osv_detail = {
            'summary': 'Test vuln pinned',
            'database_specific': {'severity': 'MODERATE'},
            'severity': [],
        }
        deps = {
            'dependencies': [{
                'name': 'pinned-pkg',
                'version_spec': '==1.0.0',
                'source': 'requirements.txt',
            }]
        }
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = osv_batch
            mock_post.return_value.raise_for_status = MagicMock()
            mock_get.return_value.ok = True
            mock_get.return_value.json.return_value = osv_detail
            result = scan_vulnerabilities(deps)

        assert len(result) == 1
        assert result[0]['version_is_range'] is False
        assert result[0]['note'] is None
        assert result[0]['version'] == '1.0.0'
