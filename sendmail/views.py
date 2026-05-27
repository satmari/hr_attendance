from __future__ import annotations

import calendar
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .models import EmailConfig, EmailLog
from .tasks import build_report_email_data, send_report_email


def _get_config() -> EmailConfig:
    config = EmailConfig.objects.first()
    if config is None:
        config = EmailConfig(smtp_host="localhost", smtp_port=25, schedule_day=10)
    return config


@login_required
def sendmail_index(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_config":
            return _save_config(request)
        if action == "send_now":
            return _send_now(request)

    config = _get_config()
    logs = EmailLog.objects.all()[:30]

    today = date.today()
    if today.month == 1:
        prev_month, prev_year = 12, today.year - 1
    else:
        prev_month, prev_year = today.month - 1, today.year

    return render(request, "sendmail/sendmail.html", {
        "config": config,
        "logs": logs,
        "months": [(i, calendar.month_name[i]) for i in range(1, 13)],
        "prev_month": prev_month,
        "prev_year": prev_year,
        "year_range": range(today.year - 3, today.year + 1),
    })


@login_required
def preview_email(request):
    try:
        month = int(request.GET.get("month", 0))
        year = int(request.GET.get("year", 0))
        if not (1 <= month <= 12) or year < 2000:
            raise ValueError
    except ValueError:
        return HttpResponse("Invalid month or year.", status=400)

    config = _get_config()
    from django.template.loader import render_to_string
    data = build_report_email_data(month, year)
    data["email_title"] = (getattr(config, "email_title", "") or "HR Attendance Monthly Report").strip()
    base = (getattr(config, "app_base_url", "") or "").rstrip("/")
    data["app_base_url"] = base
    data["report_links"] = [
        {"label": "Personnel Count",        "url": f"{base}/reports/pc/"},
        {"label": "Absenteeism",            "url": f"{base}/reports/abs/"},
        {"label": "Absenteeism SE",         "url": f"{base}/reports/abs-se-without-ki/"},
        {"label": "Turnover",               "url": f"{base}/reports/to/"},
        {"label": "Absenteeism Complete",   "url": f"{base}/reports/abs-comp/"},
        {"label": "Actual vs Budget",       "url": f"{base}/reports/actual-vs-budget/"},
    ] if base else []
    html = render_to_string("sendmail/email_report.html", data)
    return HttpResponse(html)


def _save_config(request):
    config = _get_config()
    config.email_title = request.POST.get("email_title", "").strip() or "HR Attendance Monthly Report"
    config.smtp_host = request.POST.get("smtp_host", "").strip()
    try:
        config.smtp_port = int(request.POST.get("smtp_port") or 25)
    except ValueError:
        config.smtp_port = 25
    config.sender_email = request.POST.get("sender_email", "").strip()
    config.recipient_emails = request.POST.get("recipient_emails", "").strip()
    config.app_base_url = request.POST.get("app_base_url", "").strip().rstrip("/")
    config.schedule_enabled = request.POST.get("schedule_enabled") == "on"
    try:
        config.schedule_day = max(1, min(28, int(request.POST.get("schedule_day") or 10)))
    except ValueError:
        config.schedule_day = 10
    config.save()
    messages.success(request, "Email configuration saved.")
    return redirect("sendmail_index")


def _send_now(request):
    config = _get_config()
    if not config.pk:
        messages.error(request, "Save email configuration first.")
        return redirect("sendmail_index")
    if not config.recipient_emails.strip():
        messages.error(request, "No recipient emails configured.")
        return redirect("sendmail_index")

    try:
        month = int(request.POST.get("month", 0))
        year = int(request.POST.get("year", 0))
        if not (1 <= month <= 12) or year < 2000:
            raise ValueError
    except ValueError:
        messages.error(request, "Invalid month or year.")
        return redirect("sendmail_index")

    recipients = ", ".join(r.strip() for r in config.recipient_emails.split(",") if r.strip())
    result = send_report_email(month, year, config)

    EmailLog.objects.create(
        month=month,
        year=year,
        recipients=recipients,
        status="success" if result == "ok" else "error",
        message="" if result == "ok" else result,
        triggered_by="manual",
    )

    if result == "ok":
        messages.success(request, f"Report for {calendar.month_name[month]} {year} sent successfully.")
    else:
        messages.error(request, f"Send failed: {result}")

    return redirect("sendmail_index")
