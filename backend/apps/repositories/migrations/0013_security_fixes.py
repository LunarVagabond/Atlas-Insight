from django.db import migrations, models

import apps.utils.encryption


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0012_seed_periodic_tasks'),
    ]

    operations = [
        # S1: encrypt Repository.auth_token (CharField → EncryptedCharField/TextField)
        migrations.AlterField(
            model_name='repository',
            name='auth_token',
            field=apps.utils.encryption.EncryptedCharField(blank=True, default=''),
        ),
        # S6: indexes on hot filter/sort columns
        migrations.AddIndex(
            model_name='analysisrun',
            index=models.Index(fields=['status'], name='analysisrun_status_idx'),
        ),
        migrations.AddIndex(
            model_name='analysisrun',
            index=models.Index(fields=['triggered_at'], name='analysisrun_triggered_at_idx'),
        ),
        migrations.AddIndex(
            model_name='repository',
            index=models.Index(fields=['is_watched'], name='repository_is_watched_idx'),
        ),
        migrations.AddIndex(
            model_name='repository',
            index=models.Index(fields=['is_private'], name='repository_is_private_idx'),
        ),
    ]
