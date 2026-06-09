from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('repositories', '0022_add_tools_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='watch_reason',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
