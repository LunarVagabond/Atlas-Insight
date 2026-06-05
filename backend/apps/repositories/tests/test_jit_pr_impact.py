import uuid
import pytest
from unittest.mock import patch, MagicMock
from django.test import Client
from django.core.cache import cache

from apps.repositories.models import AnalysisRun, Repository


def _make_run(db, status='completed', result=None):
    repo = Repository.objects.create(
        url=f'https://github.com/testorg/pr-{uuid.uuid4().hex[:6]}',
        owner='testorg',
        name='testrepo',
    )
    return AnalysisRun.objects.create(
        repo=repo,
        status=status,
        result=result or {
            'ownership': {
                'subsystems': [
                    {
                        'id': 'backend',
                        'name': 'API (backend/)',
                        'subsystem_type': 'api',
                        'activity_score': 0.6,
                        'god_modules': [],
                        'hot_files': [],
                    }
                ],
                'top_contributors': [
                    {'author': 'Alice', 'email': 'alice@example.com', 'files_touched': 40},
                    {'author': 'Bob', 'email': 'bob@example.com', 'files_touched': 15},
                ],
                'bus_factor': 2,
            }
        },
    )


_COMMIT_HISTORY = [
    {'commit': {'author': {'email': 'alice@example.com', 'name': 'Alice'}}},
    {'commit': {'author': {'email': 'bob@example.com', 'name': 'Bob'}}},
]


def _mock_github(pr_data=None, files_data=None, commit_history=None):
    def _make_response(data, status=200):
        m = MagicMock()
        m.ok = status == 200
        m.status_code = status
        m.json.return_value = data
        return m

    default_pr = {
        'number': 42,
        'title': 'Add auth middleware',
        'state': 'open',
        'html_url': 'https://github.com/testorg/testrepo/pull/42',
        'user': {'login': 'alice'},
        'additions': 120,
        'deletions': 30,
    }
    default_files = [
        {'filename': 'backend/apps/auth.py', 'additions': 80, 'deletions': 10},
        {'filename': 'backend/apps/middleware.py', 'additions': 40, 'deletions': 20},
    ]
    resolved_files = files_data or default_files
    history = commit_history if commit_history is not None else _COMMIT_HISTORY

    # PR detail, files list, then one commit-history response per file
    responses = [
        _make_response(pr_data or default_pr),
        _make_response(resolved_files),
    ] + [_make_response(history) for _ in resolved_files]
    return responses


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestPrImpactEndpoint:
    def setup_method(self):
        self.client = Client()

    @patch('requests.get')
    def test_returns_impact_structure(self, mock_get, db):
        run = _make_run(db)
        mock_get.side_effect = _mock_github()
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=42')
        assert resp.status_code == 200
        data = resp.json()
        assert data['pr_number'] == 42
        assert 'complexity_score' in data
        assert 'complexity_label' in data
        assert 'affected_subsystems' in data
        assert 'suggested_reviewers' in data
        assert 'touches_deps' in data
        assert 'touches_god_module' in data
        assert 'complexity_notes' in data

    @patch('requests.get')
    def test_backend_files_hit_backend_subsystem(self, mock_get, db):
        run = _make_run(db)
        mock_get.side_effect = _mock_github()
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=42')
        data = resp.json()
        sub_ids = [s['id'] for s in data['affected_subsystems']]
        assert 'backend' in sub_ids

    @patch('requests.get')
    def test_suggests_reviewers_from_file_history(self, mock_get, db):
        run = _make_run(db)
        mock_get.side_effect = _mock_github()
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=42')
        data = resp.json()
        reviewers = data['suggested_reviewers']
        assert len(reviewers) >= 1
        assert reviewers[0]['author'] in ('Alice', 'Bob')
        assert reviewers[0]['match_reason'] == 'file_history'
        assert reviewers[0]['pr_files_touched'] >= 1

    @patch('requests.get')
    def test_cache_hit_skips_github(self, mock_get, db):
        run = _make_run(db)
        cached = {
            'pr_number': 42, 'title': 'Fix bug', 'state': 'open',
            'pr_url': 'https://github.com/test/repo/pull/42', 'author': 'alice',
            'additions': 10, 'deletions': 2, 'files_changed': 1,
            'complexity_score': 15.0, 'complexity_label': 'low',
            'touches_god_module': False, 'touches_deps': False,
            'complexity_notes': [], 'affected_subsystems': [], 'suggested_reviewers': [],
        }
        cache.set(f'jit_{run.id}_pr_impact_42', cached, 900)
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=42')
        assert resp.status_code == 200
        assert resp.json()['pr_number'] == 42
        mock_get.assert_not_called()

    def test_unknown_run_returns_404(self):
        resp = self.client.get(f'/api/v1/repositories/runs/{uuid.uuid4()}/pr-impact?pr=1')
        assert resp.status_code == 404

    @patch('requests.get')
    def test_github_404_returns_404(self, mock_get, db):
        run = _make_run(db)
        not_found = MagicMock()
        not_found.ok = False
        not_found.status_code = 404
        mock_get.return_value = not_found
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=9999')
        assert resp.status_code == 404

    def test_pending_run_returns_422(self, db):
        run = _make_run(db, status='pending', result=None)
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=1')
        assert resp.status_code == 422

    @patch('requests.get')
    def test_dep_file_in_pr_flagged(self, mock_get, db):
        run = _make_run(db)
        mock_get.side_effect = _mock_github(
            files_data=[
                {'filename': 'package.json', 'additions': 3, 'deletions': 1},
                {'filename': 'frontend/App.vue', 'additions': 10, 'deletions': 5},
            ]
        )
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=42')
        assert resp.json()['touches_deps'] is True

    @patch('requests.get')
    def test_pr_meta_fields_present(self, mock_get, db):
        run = _make_run(db)
        mock_get.side_effect = _mock_github()
        resp = self.client.get(f'/api/v1/repositories/runs/{run.id}/pr-impact?pr=42')
        data = resp.json()
        assert data['title'] == 'Add auth middleware'
        assert data['author'] == 'alice'
        assert data['additions'] == 120
        assert data['deletions'] == 30
        assert data['files_changed'] == 2
