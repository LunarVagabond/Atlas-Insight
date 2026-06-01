from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0010_add_counts_and_spotlight'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='is_watched',
            field=models.BooleanField(default=False),
        ),
    ]
