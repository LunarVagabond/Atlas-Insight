import django.db.models.deletion
import uuid_extensions
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Repository',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid_extensions.uuid7,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('url', models.URLField(unique=True)),
                ('owner', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('last_commit_sha', models.CharField(blank=True, default='', max_length=40)),
                ('last_analyzed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name_plural': 'repositories'},
        ),
        migrations.CreateModel(
            name='AnalysisRun',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid_extensions.uuid7,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    'repo',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='runs',
                        to='repositories.repository',
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('running', 'Running'),
                            ('completed', 'Completed'),
                            ('failed', 'Failed'),
                        ],
                        default='pending',
                        max_length=20,
                    ),
                ),
                ('triggered_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('result', models.JSONField(blank=True, null=True)),
                ('celery_task_id', models.CharField(blank=True, default='', max_length=255)),
            ],
        ),
    ]
