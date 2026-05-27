from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("smtp_host", models.CharField(default="localhost", max_length=255)),
                ("smtp_port", models.PositiveIntegerField(default=25)),
                ("sender_email", models.CharField(blank=True, max_length=254)),
                ("recipient_emails", models.TextField(blank=True, help_text="Comma-separated email addresses")),
                ("schedule_enabled", models.BooleanField(default=False)),
                ("schedule_day", models.PositiveSmallIntegerField(default=10, help_text="Day of month to send report")),
                ("last_sent_month", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("last_sent_year", models.PositiveIntegerField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Email Configuration"},
        ),
        migrations.CreateModel(
            name="EmailLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                ("month", models.PositiveSmallIntegerField()),
                ("year", models.PositiveIntegerField()),
                ("recipients", models.TextField()),
                ("status", models.CharField(max_length=20)),
                ("message", models.TextField(blank=True)),
                ("triggered_by", models.CharField(default="manual", max_length=20)),
            ],
            options={"ordering": ["-sent_at"], "verbose_name": "Email Log"},
        ),
    ]
