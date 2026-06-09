from django.db import migrations


def seed_flags(apps, schema_editor):
    FeatureFlag = apps.get_model('repositories', 'FeatureFlag')
    defaults = [
        ('spotlight', 'Enable Repo of the Week spotlight and discovery pages'),
        ('trending', 'Enable trending repositories discovery page'),
    ]
    for name, description in defaults:
        FeatureFlag.objects.get_or_create(
            name=name,
            defaults={'enabled': True, 'description': description},
        )


def unseed_flags(apps, schema_editor):
    FeatureFlag = apps.get_model('repositories', 'FeatureFlag')
    FeatureFlag.objects.filter(name__in=['spotlight', 'trending']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0023_repository_watch_reason'),
    ]

    operations = [
        migrations.RunPython(seed_flags, unseed_flags),
    ]
