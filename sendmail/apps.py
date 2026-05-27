from __future__ import annotations

import os
import sys

from django.apps import AppConfig


class SendmailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sendmail"
    verbose_name = "Send Mail"

    def ready(self) -> None:
        # In dev, runserver spawns a reloader parent + a child (RUN_MAIN=true).
        # Skip starting the scheduler in the reloader parent; always start in production.
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return
        if any(cmd in sys.argv for cmd in ("migrate", "makemigrations", "collectstatic", "shell")):
            return
        self._start_scheduler()

    def _start_scheduler(self) -> None:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            from .tasks import check_and_send_scheduled

            scheduler = BackgroundScheduler(timezone="Europe/Budapest")
            scheduler.add_job(
                check_and_send_scheduled,
                CronTrigger(hour=7, minute=0),
                id="hr_monthly_report",
                replace_existing=True,
                misfire_grace_time=3600,
            )
            scheduler.start()
        except Exception:
            pass
