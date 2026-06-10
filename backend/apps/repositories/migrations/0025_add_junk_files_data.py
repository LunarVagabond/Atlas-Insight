from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0024_seed_feature_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysisrun',
            name='junk_files_data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
