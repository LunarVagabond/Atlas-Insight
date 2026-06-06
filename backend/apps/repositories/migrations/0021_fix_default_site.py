from django.conf import settings
from django.db import migrations


def _set_site(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    domain = getattr(settings, 'SITE_DOMAIN', 'atlas.dsyndicate.dev')
    name = getattr(settings, 'SITE_NAME', 'Atlas Insight')
    Site.objects.update_or_create(id=1, defaults={'domain': domain, 'name': name})


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0020_remove_analysisrun_result_analysisrun_abandoned_and_more'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(_set_site, _noop),
    ]
