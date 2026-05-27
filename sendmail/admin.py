from django.contrib import admin

from .models import EmailConfig, EmailLog


@admin.register(EmailConfig)
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ["sender_email", "smtp_host", "smtp_port", "schedule_enabled", "schedule_day", "updated_at"]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["sent_at", "month", "year", "status", "triggered_by", "recipients"]
    list_filter = ["status", "triggered_by"]
    readonly_fields = ["sent_at", "month", "year", "recipients", "status", "message", "triggered_by"]
