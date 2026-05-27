from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sendmail", "0002_emailconfig_app_base_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailconfig",
            name="email_title",
            field=models.CharField(
                default="HR Attendance Monthly Report",
                max_length=200,
                help_text="Editable title shown in the email subject and header. Period is appended automatically.",
            ),
        ),
    ]
