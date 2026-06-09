import pytest
from django.db import IntegrityError

from apps.repositories.models import AnalysisRun, FeatureFlag, Repository, WebhookDelivery


@pytest.mark.django_db
class TestRepository:
    def test_create(self):
        repo = Repository.objects.create(
            url='https://github.com/testorg/testrepo',
            owner='testorg',
            name='testrepo',
        )
        assert repo.pk is not None
        assert str(repo) == 'testorg/testrepo'

    def test_url_unique(self):
        Repository.objects.create(
            url='https://github.com/testorg/testrepo',
            owner='testorg',
            name='testrepo',
        )
        with pytest.raises(IntegrityError):
            Repository.objects.create(
                url='https://github.com/testorg/testrepo',
                owner='testorg',
                name='testrepo',
            )

    def test_owner_name(self):
        repo = Repository.objects.create(
            url='https://github.com/myorg/myproject',
            owner='myorg',
            name='myproject',
        )
        assert repo.owner == 'myorg'
        assert repo.name == 'myproject'

    def test_defaults(self):
        repo = Repository.objects.create(
            url='https://github.com/a/b',
            owner='a',
            name='b',
        )
        assert repo.is_stale is False
        assert repo.is_private is False
        assert repo.view_count == 0
        assert repo.scan_count == 0


@pytest.mark.django_db
class TestAnalysisRun:
    def test_create_with_fk(self):
        repo = Repository.objects.create(
            url='https://github.com/testorg/runtest',
            owner='testorg',
            name='runtest',
        )
        run = AnalysisRun.objects.create(repo=repo, status='pending')
        assert run.pk is not None
        assert run.repo == repo
        assert run.status == 'pending'
        assert 'testorg/runtest' in str(run)

    def test_status_choices(self):
        repo = Repository.objects.create(
            url='https://github.com/testorg/status',
            owner='testorg',
            name='status',
        )
        for status in ('pending', 'running', 'completed', 'failed'):
            run = AnalysisRun.objects.create(repo=repo, status=status)
            assert run.status == status

    def test_scoring_mode_round_trip(self):
        repo = Repository.objects.create(
            url='https://github.com/testorg/scoring',
            owner='testorg',
            name='scoring',
        )
        run = AnalysisRun.objects.create(repo=repo, status='completed')
        run.result = {
            'commits': {'total_commits': 1},
            'oss_score': {
                'score': 7.5,
                'badge': 'thriving',
                'label': 'Thriving',
                'mode': 'closed_source',
            },
            'scoring_mode': 'closed_source',
            'scoring_mode_reason': 'private repository',
        }
        run.save()
        run.refresh_from_db()
        assert run.result['scoring_mode'] == 'closed_source'
        assert run.result['scoring_mode_reason'] == 'private repository'
        assert run.oss_score_data['mode_reason'] == 'private repository'


@pytest.mark.django_db
class TestWebhookDelivery:
    def test_create(self):
        d = WebhookDelivery.objects.create(
            delivery_id='test-delivery-id',
            event_type='push',
            repo_url='https://github.com/a/b',
        )
        assert d.triggered_reanalysis is False
        assert d.run is None
        assert 'push' in str(d)

    def test_delivery_id_unique(self):
        WebhookDelivery.objects.create(delivery_id='dup', event_type='push')
        with pytest.raises(IntegrityError):
            WebhookDelivery.objects.create(delivery_id='dup', event_type='push')


@pytest.mark.django_db
class TestFeatureFlag:
    def test_create_disabled_by_default(self):
        flag = FeatureFlag.objects.create(name='my-feature')
        assert flag.enabled is False
        assert 'off' in str(flag)

    def test_enable(self):
        flag = FeatureFlag.objects.create(name='my-feature', enabled=True)
        assert flag.enabled is True
        assert 'on' in str(flag)

    def test_name_unique(self):
        FeatureFlag.objects.create(name='unique-flag')
        with pytest.raises(IntegrityError):
            FeatureFlag.objects.create(name='unique-flag')
