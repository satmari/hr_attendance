from __future__ import annotations

from django.db import models


class EmailConfig(models.Model):
    email_title = models.CharField(
        max_length=200,
        default="HR Attendance Monthly Report",
        help_text="Editable title shown in the email subject and header. Period is appended automatically.",
    )
    smtp_host = models.CharField(max_length=255, default="localhost")
    smtp_port = models.PositiveIntegerField(default=25)
    sender_email = models.CharField(max_length=254, blank=True)
    recipient_emails = models.TextField(blank=True, help_text="Comma-separated email addresses")
    schedule_enabled = models.BooleanField(default=False)
    schedule_day = models.PositiveSmallIntegerField(default=10, help_text="Day of month to send report")
    app_base_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Base URL of the HR Attendance app, e.g. http://192.168.1.10:8010",
    )
    last_sent_month = models.PositiveSmallIntegerField(null=True, blank=True)
    last_sent_year = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Configuration"

    def __str__(self) -> str:
        return f"Email Config ({self.sender_email or 'unconfigured'})"


class EmailLog(models.Model):
    sent_at = models.DateTimeField(auto_now_add=True)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    recipients = models.TextField()
    status = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    triggered_by = models.CharField(max_length=20, default="manual")

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Email Log"

    def __str__(self) -> str:
        return f"Email {self.month}/{self.year} — {self.status}"
