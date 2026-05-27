from __future__ import annotations

import calendar
from datetime import date

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send the monthly HR attendance report email."

    def add_arguments(self, parser):
        parser.add_argument("--month", type=int, help="Month 1-12 (default: previous month)")
        parser.add_argument("--year", type=int, help="Year (default: current/previous month year)")

    def handle(self, *args, **options):
        from sendmail.models import EmailConfig, EmailLog
        from sendmail.tasks import send_report_email

        config = EmailConfig.objects.first()
        if not config:
            self.stderr.write(self.style.ERROR(
                "No email configuration found. Configure it in the web UI at /sendmail/ first."
            ))
            return

        today = date.today()
        if options["month"]:
            month = options["month"]
            year = options["year"] or today.year
        else:
            if today.month == 1:
                month, year = 12, today.year - 1
            else:
                month, year = today.month - 1, today.year

        self.stdout.write(f"Sending report for {calendar.month_name[month]} {year}...")

        result = send_report_email(month, year, config)
        recipients = ", ".join(r.strip() for r in config.recipient_emails.split(",") if r.strip())

        EmailLog.objects.create(
            month=month,
            year=year,
            recipients=recipients,
            status="success" if result == "ok" else "error",
            message="" if result == "ok" else result,
            triggered_by="management_command",
        )

        if result == "ok":
            self.stdout.write(self.style.SUCCESS("Report sent successfully."))
        else:
            self.stderr.write(self.style.ERROR(f"Failed: {result}"))
