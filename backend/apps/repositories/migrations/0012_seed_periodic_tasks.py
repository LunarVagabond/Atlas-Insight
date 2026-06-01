from django.db import migrations


TASKS = [
    {
        'name': 'check-stale-repos',
        'task': 'apps.analysis.tasks.check_stale_repos',
        'cron': {'minute': '0', 'hour': '*/6', 'day_of_week': '*', 'day_of_month': '*', 'month_of_year': '*'},
    },
    {
        'name': 'cleanup-old-runs',
        'task': 'apps.analysis.tasks.cleanup_old_runs',
        'cron': {'minute': '30', 'hour': '2', 'day_of_week': '*', 'day_of_month': '*', 'month_of_year': '*'},
    },
    {
        'name': 'evict-stale-clones',
        'task': 'apps.analysis.tasks.evict_stale_clones',
        'cron': {'minute': '0', 'hour': '3', 'day_of_week': '*', 'day_of_month': '*', 'month_of_year': '*'},
    },
    {
        'name': 'cleanup-old-logs',
        'task': 'apps.analysis.tasks.cleanup_old_logs',
        'cron': {'minute': '30', 'hour': '3', 'day_of_week': '*', 'day_of_month': '*', 'month_of_year': '*'},
    },
    {
        'name': 'select-repo-of-week',
        'task': 'apps.analysis.tasks.select_repo_of_week',
        'cron': {'minute': '0', 'hour': '0', 'day_of_week': '1', 'day_of_month': '*', 'month_of_year': '*'},
    },
    {
        'name': 'reanalyze-watched-repos',
        'task': 'apps.analysis.tasks.reanalyze_watched_repos',
        'cron': {'minute': '0', 'hour': '4', 'day_of_week': '*', 'day_of_month': '*', 'month_of_year': '*'},
    },
]


def seed_periodic_tasks(apps, schema_editor):
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    for task_def in TASKS:
        cron, _ = CrontabSchedule.objects.get_or_create(**task_def['cron'])
        PeriodicTask.objects.update_or_create(
            name=task_def['name'],
            defaults={
                'task': task_def['task'],
                'crontab': cron,
                'enabled': True,
            },
        )


def remove_periodic_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name__in=[t['name'] for t in TASKS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('repositories', '0011_repository_is_watched'),
        ('django_celery_beat', '0019_alter_periodictasks_options'),
    ]

    operations = [
        migrations.RunPython(seed_periodic_tasks, remove_periodic_tasks),
    ]
