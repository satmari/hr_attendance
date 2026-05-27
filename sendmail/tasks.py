from __future__ import annotations

import calendar
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.template.loader import render_to_string

from import_excel.reporting import (
    build_abs_comp_report,
    build_abs_report,
    build_abs_se_without_ki_report,
    build_actual_vs_budget_report,
    build_pc_report,
    build_to_report,
)


def _abs_color(pct_str: str) -> str:
    """Return hex color for an ABS% string like '8.45%'."""
    if not pct_str:
        return "#9ca3af"
    try:
        pct = float(str(pct_str).rstrip("%"))
        if pct <= 9.0:
            return "#16a34a"
        if pct <= 11.0:
            return "#d97706"
        return "#dc2626"
    except (ValueError, TypeError):
        return "#9ca3af"


def _to_color(to_str: str) -> str:
    """Return hex color for a turnover rate string like '3.50%'."""
    if not to_str:
        return "#9ca3af"
    try:
        pct = float(str(to_str).rstrip("%"))
        if pct <= 3.0:
            return "#16a34a"
        if pct <= 6.0:
            return "#d97706"
        return "#dc2626"
    except (ValueError, TypeError):
        return "#374151"


def _extract_pc_summary(pc: dict) -> list[dict]:
    rows = []
    for section in pc["sections"]:
        for row in section.rows:
            rows.append({
                "label": row.label,
                "avg": row.extra_values[0] if row.extra_values else "—",
                "kind": row.kind,
            })
    return rows


def _extract_abs_summary(report: dict) -> list[dict]:
    rows = []
    for section in report["tab_main"]["sections"]:
        for row in section.rows:
            avg = row.extra_values[0] if row.extra_values else "—"
            rows.append({
                "label": row.label,
                "avg": avg,
                "kind": row.kind,
                "color": _abs_color(avg),
            })
    return rows


def _extract_to_summary(report: dict) -> dict:
    cols = report.get("summary_columns", ["SUB", "KIK", "SEN", "TOTAL"])
    sections = []
    for section in report["sections"][:2]:  # Total + Op. in Line only
        rows = []
        for row in section.rows:
            color = ""
            if row.kind == "total":
                # Last value is the TOTAL column
                total_val = str(row.values[-1]) if row.values else ""
                color = _to_color(total_val)
            rows.append({
                "label": row.label,
                "values": row.values,
                "kind": row.kind,
                "color": color,
            })
        sections.append({"title": section.title, "rows": rows})
    return {"columns": cols, "sections": sections}


def _extract_abs_comp_summary(report: dict) -> list[dict]:
    rows = []
    for site in report["sites"]:
        total = site["total"]
        pct = total.get("abs_pct_display", "—") or "—"
        rows.append({
            "name": site["name"],
            "active": total.get("active", "—"),
            "present": total.get("present", "—"),
            "not_present": total.get("not_present", "—"),
            "abs_pct": pct,
            "color": _abs_color(pct),
        })
    return rows


def build_report_email_data(month: int, year: int) -> dict:
    pc = build_pc_report(month, year)
    abs_r = build_abs_report(month, year)
    abs_se = build_abs_se_without_ki_report(month, year)
    to_r = build_to_report(month, year)
    abs_comp = build_abs_comp_report(month, year)
    avb = build_actual_vs_budget_report(month, year)

    return {
        "month": month,
        "year": year,
        "month_name": calendar.month_name[month],
        "records": pc.get("records", 0),
        "pc": _extract_pc_summary(pc),
        "abs": _extract_abs_summary(abs_r),
        "abs_se": _extract_abs_summary(abs_se),
        "turnover": _extract_to_summary(to_r),
        "abs_comp": _extract_abs_comp_summary(abs_comp),
        "avb": avb,
    }


def send_report_email(month: int, year: int, config) -> str:
    """Build and send the monthly HR report email. Returns 'ok' or error string."""
    data = build_report_email_data(month, year)
    title = (getattr(config, "email_title", "") or "HR Attendance Monthly Report").strip()
    data["email_title"] = title
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
    html_body = render_to_string("sendmail/email_report.html", data)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{title} — {data['month_name']} {year}"
    msg["From"] = config.sender_email
    recipients = [r.strip() for r in config.recipient_emails.split(",") if r.strip()]
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as smtp:
            smtp.sendmail(config.sender_email, recipients, msg.as_bytes())
        return "ok"
    except Exception as exc:
        return str(exc)


def check_and_send_scheduled() -> None:
    """Called by background scheduler daily at 07:00. Sends if today matches schedule_day."""
    from django.utils import timezone

    from .models import EmailConfig, EmailLog

    try:
        config = EmailConfig.objects.first()
    except Exception:
        return

    if not config or not config.schedule_enabled:
        return

    today = timezone.localdate()
    if today.day != config.schedule_day:
        return

    # Report covers the previous month
    if today.month == 1:
        r_month, r_year = 12, today.year - 1
    else:
        r_month, r_year = today.month - 1, today.year

    # Skip if already sent for this period
    if config.last_sent_month == r_month and config.last_sent_year == r_year:
        return

    recipients = ", ".join(r.strip() for r in config.recipient_emails.split(",") if r.strip())
    result = send_report_email(r_month, r_year, config)

    EmailLog.objects.create(
        month=r_month,
        year=r_year,
        recipients=recipients,
        status="success" if result == "ok" else "error",
        message="" if result == "ok" else result,
        triggered_by="schedule",
    )

    if result == "ok":
        config.last_sent_month = r_month
        config.last_sent_year = r_year
        config.save(update_fields=["last_sent_month", "last_sent_year"])
