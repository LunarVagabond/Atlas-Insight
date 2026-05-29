from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('repositories', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='is_stale',
            field=models.BooleanField(default=False),
        ),
    ]
