from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sendmail", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailconfig",
            name="app_base_url",
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text="Base URL of the HR Attendance app, e.g. http://192.168.1.10:8010",
            ),
        ),
    ]
