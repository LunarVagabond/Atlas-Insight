from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('repositories', '0007_add_webhook_url_to_analysisrun'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysisrun',
            name='notification_email',
            field=models.EmailField(blank=True, default=''),
        ),
    ]
