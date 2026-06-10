import subprocess
from pathlib import Path

import pytest
from git import Repo

from apps.analysis.junk_files import scan_junk_files


@pytest.fixture
def junk_repo(tmp_path):
    repo_dir = tmp_path / 'repo'
    repo_dir.mkdir()
    subprocess.run(['git', 'init'], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ['git', 'config', 'user.email', 'test@test.com'],
        cwd=repo_dir, check=True, capture_output=True,
    )
    subprocess.run(
        ['git', 'config', 'user.name', 'Test'],
        cwd=repo_dir, check=True, capture_output=True,
    )

    files = {
        'tmp.txt': 'temp content',
        '.DS_Store': 'junk',
        'app.log': 'log line\n',
        'dist/bundle.js': 'console.log()',
        'notes.txt': 'scratch notes',
        'template.txt': 'legitimate template',
        'README.md': '# Hello',
        'src/test_tmp_utils.py': 'def helper(): pass',
        'backup.bak': 'old',
    }
    for rel, content in files.items():
        path = repo_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    subprocess.run(['git', 'add', '-f', '.'], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ['git', 'commit', '-m', 'init'],
        cwd=repo_dir, check=True, capture_output=True,
    )
    return Repo(repo_dir), str(repo_dir)


class TestScanJunkFiles:
    def test_detects_junk_categories(self, junk_repo):
        repo_obj, repo_dir = junk_repo
        result = scan_junk_files(repo_obj, repo_dir)

        paths = {f['path'] for f in result['files']}
        assert 'tmp.txt' in paths
        assert '.DS_Store' in paths
        assert 'app.log' in paths
        assert 'dist/bundle.js' in paths
        assert 'notes.txt' in paths
        assert 'backup.bak' in paths

    def test_skips_legitimate_files(self, junk_repo):
        repo_obj, repo_dir = junk_repo
        result = scan_junk_files(repo_obj, repo_dir)

        paths = {f['path'] for f in result['files']}
        assert 'template.txt' not in paths
        assert 'README.md' not in paths
        assert 'src/test_tmp_utils.py' not in paths

    def test_category_assignment(self, junk_repo):
        repo_obj, repo_dir = junk_repo
        result = scan_junk_files(repo_obj, repo_dir)

        by_path = {f['path']: f for f in result['files']}
        assert by_path['tmp.txt']['category'] == 'temp_file'
        assert by_path['tmp.txt']['confidence'] == 'high'
        assert by_path['.DS_Store']['category'] == 'os_junk'
        assert by_path['notes.txt']['category'] == 'ai_scratch'
        assert by_path['notes.txt']['confidence'] == 'medium'
        assert by_path['dist/bundle.js']['category'] == 'gitignore_gap'

    def test_count_and_score(self, junk_repo):
        repo_obj, repo_dir = junk_repo
        result = scan_junk_files(repo_obj, repo_dir)

        assert result['count'] == len(result['files'])
        assert result['count'] > 0
        assert result['score'] > 0
        assert result['total_bytes'] > 0
        assert result['by_category']

    def test_empty_repo(self, tmp_path):
        repo_dir = tmp_path / 'empty'
        repo_dir.mkdir()
        subprocess.run(['git', 'init'], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ['git', 'config', 'user.email', 't@t.com'],
            cwd=repo_dir, check=True, capture_output=True,
        )
        subprocess.run(
            ['git', 'config', 'user.name', 'T'],
            cwd=repo_dir, check=True, capture_output=True,
        )
        readme = repo_dir / 'README.md'
        readme.write_text('# ok')
        subprocess.run(['git', 'add', '-f', '.'], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ['git', 'commit', '-m', 'init'],
            cwd=repo_dir, check=True, capture_output=True,
        )
        repo_obj = Repo(repo_dir)

        result = scan_junk_files(repo_obj, str(repo_dir))
        assert result['count'] == 0
        assert result['score'] == 0
        assert result['files'] == []
