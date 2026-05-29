from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0002_repository_is_stale'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='last_fetched_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
