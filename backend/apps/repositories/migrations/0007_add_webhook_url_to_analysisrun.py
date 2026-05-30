from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0006_add_auth_token_to_repository'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysisrun',
            name='webhook_url',
            field=models.URLField(blank=True, default=''),
        ),
    ]
