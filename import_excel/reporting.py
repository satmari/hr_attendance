from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from .models import BudgetPlanData, PersonnelActualData, PersonnelMasterRecord, PersonnelPresence

SEWING_DEPARTMENTS = {
    "SUB": "SEWING OPERATORS",
    "KIK": "SEWING OPERATORS KIKINDA",
    "SEN": "SEWING OPERATORS SENTA",
}


@dataclass
class ReportRow:
    label: str
    values: list[object]
    kind: str = "value"
    extra_values: list[object] | None = None


@dataclass
class ReportSection:
    title: str
    rows: list[ReportRow]


def normalize(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip().upper()


def is_one(value: object) -> bool:
    return normalize(value) == "1"


def is_x(value: object) -> bool:
    return normalize(value) == "X"


def is_dash(value: object) -> bool:
    return normalize(value) == "-"


def is_blank(value: object) -> bool:
    return normalize(value) == ""


def period_day_headers(year: int, month: int) -> list[dict[str, object]]:
    days = calendar.monthrange(year, month)[1]
    return [
        {"day": day, "weekday": date(year, month, day).strftime("%a").upper(), "exists": True}
        for day in range(1, days + 1)
    ]


def load_period_records(month: int, year: int) -> list[PersonnelPresence]:
    return list(
        PersonnelPresence.objects.filter(month=month, year=year)
        .select_related(
            "personnelpresencedepartment",
            "personnelpresencelocation",
            "personnelpresenceshift",
            "personnelpresenceinteos",
            "personnelpresencezucchetti",
        )
        .order_by("employee_code")
    )


def _daily_attr(instance: object, day: int) -> str:
    if instance is None:
        return ""
    return normalize(getattr(instance, f"day{day}", ""))


def _constant_row(label: str, day_count: int, value: object) -> ReportRow:
    return ReportRow(label=label, values=[value for _ in range(day_count)])


def _sum_row(label: str, rows: list[ReportRow]) -> ReportRow:
    values: list[int] = []
    for index in range(len(rows[0].values)):
        total = 0
        for row in rows:
            total += int(row.values[index] or 0)
        values.append(total)
    return ReportRow(label=label, values=values, kind="total")


def _fmt_avg(floats: list[float]) -> str:
    return f"{sum(floats) / len(floats):.2f}%" if floats else ""


def _ratio_row(
    label: str,
    numerator: ReportRow,
    denominator: ReportRow,
    holiday_mask: list[bool] | None = None,
) -> ReportRow:
    values: list[object] = []
    precise: list[float] = []
    for index in range(len(numerator.values)):
        if holiday_mask and holiday_mask[index]:
            values.append("")
            continue
        den = int(denominator.values[index] or 0)
        num = int(numerator.values[index] or 0)
        if den > 0:
            pct = num / den * 100
            values.append(f"{pct:.2f}%")
            precise.append(pct)
        else:
            values.append("")
    return ReportRow(label=label, values=values, kind="percent", extra_values=[_fmt_avg(precise)])


def _pct_total_row(
    label: str,
    absent_rows: list[ReportRow],
    total_rows: list[ReportRow],
    holiday_mask: list[bool] | None = None,
) -> ReportRow:
    day_count = len(absent_rows[0].values)
    values: list[object] = []
    precise: list[float] = []
    for d in range(day_count):
        if holiday_mask and holiday_mask[d]:
            values.append("")
            continue
        day_num = sum(int(a.values[d] or 0) for a, t in zip(absent_rows, total_rows) if int(t.values[d] or 0) > 0)
        day_den = sum(int(t.values[d] or 0) for t in total_rows)
        if day_den > 0:
            pct = day_num / day_den * 100
            values.append(f"{pct:.2f}%")
            precise.append(pct)
        else:
            values.append("")
    return ReportRow(label=label, values=values, kind="percent", extra_values=[_fmt_avg(precise)])


def _average_non_zero(values: list[object]) -> str:
    numeric_values = [float(value) for value in values if value not in ("", None, 0)]
    if not numeric_values:
        return ""
    return f"{sum(numeric_values) / len(numeric_values):.2f}"


def _count_days(
    day_count: int,
    predicate: Callable[[PersonnelPresence, int], bool],
    records: list[PersonnelPresence],
) -> list[int]:
    return [
        sum(1 for record in records if predicate(record, day))
        for day in range(1, day_count + 1)
    ]


def build_pc_report(month: int, year: int) -> dict[str, object]:
    records = load_period_records(month, year)
    headers = period_day_headers(year, month)
    day_count = len(headers)

    # ALL LOGGED OPERATORS: COUNTIFS(SUB{day}=site, {day}.=1, {day}=1)
    def logged_site(site: str, day: int, shift: str | None = None) -> int:
        total = 0
        for record in records:
            location = _daily_attr(getattr(record, "personnelpresencelocation", None), day)
            inteos = _daily_attr(getattr(record, "personnelpresenceinteos", None), day)
            zucchetti = _daily_attr(getattr(record, "personnelpresencezucchetti", None), day)
            day_shift = _daily_attr(getattr(record, "personnelpresenceshift", None), day)
            if location != site or inteos != "1" or zucchetti != "1":
                continue
            if shift and day_shift != shift:
                continue
            total += 1
        return total

    sub_vals = [logged_site("SUB", d) for d in range(1, day_count + 1)]
    kik_a_vals = [logged_site("KIK", d, "A") for d in range(1, day_count + 1)]
    kik_b_vals = [logged_site("KIK", d, "B") for d in range(1, day_count + 1)]
    kik_tot_vals = [a + b for a, b in zip(kik_a_vals, kik_b_vals)]
    sen_vals = [logged_site("SEN", d) for d in range(1, day_count + 1)]

    rows = [
        ReportRow("SUB", sub_vals, extra_values=[_average_non_zero(sub_vals)]),
        ReportRow("KIK", kik_tot_vals, extra_values=[_average_non_zero(kik_tot_vals)]),
        ReportRow("SEN", sen_vals, extra_values=[_average_non_zero(sen_vals)]),
    ]
    total_row = _sum_row("TOTAL", rows)
    pr_cadre_sum = sum(
        float(row.extra_values[0]) for row in rows if row.extra_values and row.extra_values[0] not in ("", None)
    )
    total_row.extra_values = [f"{pr_cadre_sum:.2f}"]
    rows.append(total_row)

    return {
        "title": "PC",
        "headers": headers,
        "sections": [ReportSection("All Logged Operators", rows)],
        "records": len(records),
        "extra_headers": ["PR.CADRE"],
    }


def build_abs_report(month: int, year: int) -> dict[str, object]:
    records = load_period_records(month, year)
    headers = period_day_headers(year, month)
    day_count = len(headers)

    # NOT ACTIVE: COUNTIFS(DEP{day}=dept, Zucchetti{day}="X")
    def not_active(dept: str) -> list[int]:
        return _count_days(
            day_count,
            lambda r, d: _daily_attr(getattr(r, "personnelpresencedepartment", None), d) == dept
            and is_x(_daily_attr(getattr(r, "personnelpresencezucchetti", None), d)),
            records,
        )

    # ACTIVE NOT PRESENT: COUNTIFS(SUB{day}=site, Inteos{day}=1, Zucchetti{day}="-")
    def absent(site: str) -> list[int]:
        return [
            sum(1 for r in records
                if _daily_attr(getattr(r, "personnelpresencelocation", None), day) == site
                and _daily_attr(getattr(r, "personnelpresenceinteos", None), day) == "1"
                and is_dash(_daily_attr(getattr(r, "personnelpresencezucchetti", None), day)))
            for day in range(1, day_count + 1)
        ]

    # ACTIVE PRESENT: COUNTIFS(SUB{day}=site, Inteos{day}=1, Zucchetti{day}="1")
    def present(site: str) -> list[int]:
        return [
            sum(1 for r in records
                if _daily_attr(getattr(r, "personnelpresencelocation", None), day) == site
                and _daily_attr(getattr(r, "personnelpresenceinteos", None), day) == "1"
                and is_one(_daily_attr(getattr(r, "personnelpresencezucchetti", None), day)))
            for day in range(1, day_count + 1)
        ]

    sub_na  = not_active(SEWING_DEPARTMENTS["SUB"])
    kik_na  = not_active(SEWING_DEPARTMENTS["KIK"])
    sen_na  = not_active(SEWING_DEPARTMENTS["SEN"])

    sub_abs = absent("SUB")
    kik_abs = absent("KIK")
    sen_abs = absent("SEN")

    sub_pres = present("SUB")
    kik_pres = present("KIK")
    sen_pres = present("SEN")

    # TOTAL ACTIVE: IF(present=0, 0, absent+present)
    def total_active(abs_vals: list[int], pres_vals: list[int]) -> list[int]:
        return [0 if p == 0 else a + p for a, p in zip(abs_vals, pres_vals)]

    sub_tot  = total_active(sub_abs, sub_pres)
    kik_tot  = total_active(kik_abs, kik_pres)
    sen_tot  = total_active(sen_abs, sen_pres)

    # --- Tab 2: detail (4 tables) ---
    not_active_rows = [
        ReportRow("Sew.op. SUB", sub_na),
        ReportRow("Sew.op. KIK", kik_na),
        ReportRow("Sew.op. SEN", sen_na),
    ]
    not_active_rows.append(_sum_row("TOTAL", not_active_rows))

    absent_rows = [
        ReportRow("Sew.op. SUB", sub_abs),
        ReportRow("Sew.op. KIK", kik_abs),
        ReportRow("Sew.op. SEN", sen_abs),
    ]
    absent_rows.append(_sum_row("TOTAL", absent_rows))

    present_rows = [
        ReportRow("Sew.op. SUB", sub_pres),
        ReportRow("Sew.op. KIK", kik_pres),
        ReportRow("Sew.op. SEN", sen_pres),
    ]
    present_rows.append(_sum_row("TOTAL", present_rows))

    total_rows = [
        ReportRow("Sew.op. SUB", sub_tot),
        ReportRow("Sew.op. KIK", kik_tot),
        ReportRow("Sew.op. SEN", sen_tot),
    ]
    tot_total_vals = [s + k + n for s, k, n in zip(sub_tot, kik_tot, sen_tot)]
    total_rows.append(ReportRow("TOTAL", tot_total_vals, kind="total"))

    # --- Tab 1: ABS% TOTAL ACTIVE: IF(total=0, "", absent/total) ---
    all_tot  = [s + k + n for s, k, n in zip(sub_tot, kik_tot, sen_tot)]
    # For TOTAL abs: only count absents from sites that have active employees that day (tot > 0),
    # to avoid inflating the ratio with absents from sites where present=0.
    all_abs_active = [
        (sub_abs[i] if sub_tot[i] > 0 else 0)
        + (kik_abs[i] if kik_tot[i] > 0 else 0)
        + (sen_abs[i] if sen_tot[i] > 0 else 0)
        for i in range(day_count)
    ]

    def _site_holiday_mask(abs_vals: list[int], tot_vals: list[int]) -> list[bool]:
        return [tot > 0 and abs_ / tot * 100 > 90 for abs_, tot in zip(abs_vals, tot_vals)]

    abs_pct_rows = [
        _ratio_row("Sew.op. SUB", ReportRow("", sub_abs), ReportRow("", sub_tot), _site_holiday_mask(sub_abs, sub_tot)),
        _ratio_row("Sew.op. KIK", ReportRow("", kik_abs), ReportRow("", kik_tot), _site_holiday_mask(kik_abs, kik_tot)),
        _ratio_row("Sew.op. SEN", ReportRow("", sen_abs), ReportRow("", sen_tot), _site_holiday_mask(sen_abs, sen_tot)),
    ]
    abs_pct_rows.append(_ratio_row("TOTAL", ReportRow("", all_abs_active), ReportRow("", all_tot), _site_holiday_mask(all_abs_active, all_tot)))

    return {
        "title": "Absentizm",
        "headers": headers,
        "records": len(records),
        "tab_main": {
            "sections": [ReportSection("ABS% — Total Active", abs_pct_rows)],
            "extra_headers": ["% ABS"],
        },
        "tab_detail": {
            "sections": [
                ReportSection("Not Active", not_active_rows),
                ReportSection("Active Not Present", absent_rows),
                ReportSection("Active Present", present_rows),
                ReportSection("Total Active", total_rows),
            ],
            "extra_headers": [],
        },
    }


def build_abs_se_without_ki_report(month: int, year: int) -> dict[str, object]:
    records = load_period_records(month, year)
    headers = period_day_headers(year, month)
    day_count = len(headers)

    # SEN only, excluding employees who moved to KIK (ki_to_se != "")
    def sen_val(day: int, zucchetti_value: str) -> int:
        return sum(
            1 for r in records
            if _daily_attr(getattr(r, "personnelpresencelocation", None), day) == "SEN"
            and _daily_attr(getattr(r, "personnelpresenceinteos", None), day) == "1"
            and _daily_attr(getattr(r, "personnelpresencezucchetti", None), day) == zucchetti_value
            and is_blank(r.ki_to_se)
        )

    sen_abs  = [sen_val(d, "-") for d in range(1, day_count + 1)]
    sen_pres = [sen_val(d, "1") for d in range(1, day_count + 1)]
    sen_tot  = [0 if p == 0 else a + p for a, p in zip(sen_abs, sen_pres)]

    absent_rows  = [ReportRow("Sew.op. SEN", sen_abs),  _sum_row("TOTAL", [ReportRow("", sen_abs)])]
    present_rows = [ReportRow("Sew.op. SEN", sen_pres), _sum_row("TOTAL", [ReportRow("", sen_pres)])]
    total_rows   = [ReportRow("Sew.op. SEN", sen_tot),  _sum_row("TOTAL", [ReportRow("", sen_tot)])]

    sen_holiday_mask = [tot > 0 and abs_ / tot * 100 > 90 for abs_, tot in zip(sen_abs, sen_tot)]
    abs_pct_rows = [
        _ratio_row("Sew.op. SEN", ReportRow("", sen_abs), ReportRow("", sen_tot), sen_holiday_mask),
        _ratio_row("TOTAL",       ReportRow("", sen_abs), ReportRow("", sen_tot), sen_holiday_mask),
    ]

    return {
        "title": "Absenteeism SE without KI",
        "headers": headers,
        "records": len(records),
        "tab_main": {
            "sections": [ReportSection("ABS% — Total Active", abs_pct_rows)],
            "extra_headers": ["% ABS"],
        },
        "tab_detail": {
            "sections": [
                ReportSection("Active Not Present", absent_rows),
                ReportSection("Active Present", present_rows),
                ReportSection("Total Active", total_rows),
            ],
            "extra_headers": [],
        },
    }


def build_to_report(month: int, year: int) -> dict[str, object]:
    records = load_period_records(month, year)
    month_prefix = f"{year:04d}-{month:02d}"

    all_mat = list(PersonnelMasterRecord.objects.filter(month=month, year=year))
    mat_by_code = {m.employee_code: m for m in all_mat}

    SITES = ["SUB", "KIK", "SEN"]
    sewing_depts = set(SEWING_DEPARTMENTS.values())

    presence_by_code = {r.employee_code: r for r in records}

    def _terminated(r: PersonnelPresence) -> bool:
        m = mat_by_code.get(r.employee_code)
        return bool(m and m.termination_date and str(m.termination_date).startswith(month_prefix))

    def _seniority(r: PersonnelPresence) -> float | None:
        m = mat_by_code.get(r.employee_code)
        if not m or not m.seniority_months:
            return None
        try:
            return float(m.seniority_months)
        except (ValueError, TypeError):
            return None

    def _category(r: PersonnelPresence) -> str:
        m = mat_by_code.get(r.employee_code)
        return str(m.category).strip() if m and m.category else ""

    site_all = {s: [r for r in records if normalize(r.current_location) == s] for s in SITES}
    site_sew = {
        s: [r for r in site_all[s] if normalize(r.current_department) in sewing_depts]
        for s in SITES
    }

    # Recruited counts from mat table directly (captures new hires not yet in main sheet).
    # A new hire with no PersonnelPresence record is assumed to be a sewing operator.
    rec_total: dict[str, int] = {s: 0 for s in SITES}
    rec_sew: dict[str, int] = {s: 0 for s in SITES}
    for m in all_mat:
        if not (m.hire_date and str(m.hire_date).startswith(month_prefix)):
            continue
        site = normalize(m.department)
        if site not in SITES:
            continue
        rec_total[site] += 1
        pres = presence_by_code.get(m.employee_code)
        if pres is None or normalize(pres.current_department) in sewing_depts:
            rec_sew[site] += 1

    def _make_total_row(label: str, getter, kind: str = "value") -> ReportRow:
        vals = [getter(s) for s in SITES]
        vals.append(sum(v for v in vals if isinstance(v, (int, float))))
        return ReportRow(label=label, values=vals, kind=kind)

    def _lost(s): return sum(1 for r in site_all[s] if _terminated(r))
    def _lost_sew(s): return sum(1 for r in site_sew[s] if _terminated(r))
    def _hc(s): return len(site_all[s]) - _lost(s)
    def _hc_sew(s): return len(site_sew[s]) - _lost_sew(s)
    def _rate(s): return f"{_lost(s) / _hc(s) * 100:.2f}%" if _hc(s) else "0.00%"
    def _rate_sew(s): return f"{_lost_sew(s) / _hc_sew(s) * 100:.2f}%" if _hc_sew(s) else "0.00%"

    def _net_total(s): return rec_total[s] - _lost(s)
    def _net_sew(s): return rec_sew[s] - _lost_sew(s)

    def _total_rate(sites):
        lost = sum(_lost(s) for s in sites)
        hc = sum(_hc(s) for s in sites)
        return f"{lost / hc * 100:.2f}%" if hc else "0.00%"

    def _total_rate_sew(sites):
        lost = sum(_lost_sew(s) for s in sites)
        hc = sum(_hc_sew(s) for s in sites)
        return f"{lost / hc * 100:.2f}%" if hc else "0.00%"

    def _row(label: str, per_site, total_val=None, kind: str = "value") -> ReportRow:
        vals = [per_site(s) for s in SITES]
        if total_val is not None:
            vals.append(total_val())
        else:
            vals.append(sum(v for v in vals if isinstance(v, (int, float))))
        return ReportRow(label=label, values=vals, kind=kind)

    sec_total = [
        _row("total lost", _lost),
        _row("total recruited", lambda s: rec_total[s]),
        _row("lost VS recruited", _net_total),
        _row("total headcount*", _hc),
        _row("TOTAL T/O", _rate, total_val=lambda: _total_rate(SITES), kind="total"),
    ]

    sec_opil = [
        _row("lost op. in line", _lost_sew),
        _row("recruited op. in line", lambda s: rec_sew[s]),
        _row("lost VS recruited", _net_sew),
        _row("op. in line headcount*", _hc_sew),
        _row("OP. IN LINE T/O", _rate_sew, total_val=lambda: _total_rate_sew(SITES), kind="total"),
    ]

    total_lost_vals = [sum(1 for r in site_all[s] if _terminated(r)) for s in SITES]
    total_lost_vals.append(sum(total_lost_vals))
    total_lost_row = ReportRow("TOTAL LOST", total_lost_vals, kind="total")

    def _sen_row(label: str, pred) -> ReportRow:
        vals = [sum(1 for r in site_all[s] if _terminated(r) and pred(_seniority(r))) for s in SITES]
        vals.append(sum(vals))
        return ReportRow(label=label, values=vals)

    sec_seniority = [
        _sen_row("total lost seniority <6m", lambda v: v is not None and v < 6),
        _sen_row("total lost seniority >6m", lambda v: v is not None and v >= 6),
        total_lost_row,
    ]

    def _cat_row(label: str, cat_val: str) -> ReportRow:
        vals = [sum(1 for r in site_all[s] if _terminated(r) and _category(r) == cat_val) for s in SITES]
        vals.append(sum(vals))
        return ReportRow(label=label, values=vals)

    sec_reasons = [
        _cat_row("total lost: RESIGNATION (employee decision)", "1"),
        _cat_row("total lost: DISMISSAL (employer decision)", "2"),
        _cat_row("total lost: MIX (resigned but would be dismissed)", "3"),
        _cat_row("total lost: EXTERNAL (teh.surplus or retirement)", "-"),
        total_lost_row,
    ]

    return {
        "title": "Turnover",
        "summary_mode": True,
        "summary_columns": ["SUB", "KIK", "SEN", "TOTAL"],
        "sections": [
            ReportSection("Total", sec_total),
            ReportSection("Op. in Line (Sewing Operators)", sec_opil),
            ReportSection("Seniority Breakdown", sec_seniority),
            ReportSection("By Exit Reason", sec_reasons),
        ],
        "records": len(records),
    }


def build_abs_comp_report(month: int, year: int) -> dict[str, object]:
    from itertools import groupby as _groupby

    records = load_period_records(month, year)
    headers = period_day_headers(year, month)

    def _trend(pct: float | None) -> str:
        if pct is None:
            return ""
        if pct <= 9.0:
            return "check"
        if pct <= 11.0:
            return "warning"
        return "danger"

    def _count_day(site: str, day: int, ki_filter: bool = False) -> tuple[int, int, int]:
        active = present = not_present = 0
        for r in records:
            if ki_filter and not is_blank(r.ki_to_se):
                continue
            location = _daily_attr(getattr(r, "personnelpresencelocation", None), day)
            inteos = _daily_attr(getattr(r, "personnelpresenceinteos", None), day)
            zucchetti = _daily_attr(getattr(r, "personnelpresencezucchetti", None), day)
            if location != site or inteos != "1":
                continue
            if zucchetti == "1":
                present += 1
                active += 1
            elif zucchetti == "-":
                not_present += 1
                active += 1
        return active, present, not_present

    def _make_day(h: dict, active: int, present: int, not_present: int, ki_data: dict | None = None) -> dict:
        day = h["day"]
        pct = not_present / active * 100 if active > 0 else None
        # Holiday detection: >90% absence on a nominally active day → treat as non-working
        is_holiday = pct is not None and pct > 90
        is_working = active > 0 and not is_holiday
        row = {
            "year": year,
            "month": month,
            "day": day,
            "weekday": h["weekday"],
            "iso_week": date(year, month, day).isocalendar()[1],
            "active": active if is_working else "",
            "present": present if is_working else "",
            "not_present": not_present if is_working else "",
            "abs_pct": pct if is_working else None,
            "abs_pct_display": f"{pct:.2f}%" if is_working and pct is not None else "",
            "trend": _trend(pct) if is_working else "",
            "is_working": is_working,
            "is_holiday": is_holiday,
        }
        if ki_data is not None:
            row["abs_pct_woki_display"] = ki_data.get("abs_pct_woki_display", "")
        return row

    def _build_days(site: str, ki_filter: bool = False) -> list[dict]:
        result = []
        for h in headers:
            a, p, np_ = _count_day(site, h["day"], ki_filter)
            result.append(_make_day(h, a, p, np_))
        return result

    def _compute_total(days: list[dict], woki_days: list[dict] | None = None) -> dict:
        working = [d for d in days if d["is_working"]]
        if not working:
            t: dict = {"active": 0, "present": 0, "not_present": 0, "abs_pct_display": "", "trend": ""}
            if woki_days is not None:
                t["abs_pct_woki_display"] = ""
            return t
        n = len(working)
        sum_a  = sum(int(d["active"] or 0) for d in working)
        sum_p  = sum(int(d["present"] or 0) for d in working)
        sum_np = sum(int(d["not_present"] or 0) for d in working)
        daily_pcts = [d["abs_pct"] for d in working if d["abs_pct"] is not None]
        pct = sum(daily_pcts) / len(daily_pcts) if daily_pcts else None
        t = {
            "active": round(sum_a / n),
            "present": round(sum_p / n),
            "not_present": round(sum_np / n),
            "abs_pct_display": f"{pct:.2f}%" if pct is not None else "",
            "trend": _trend(pct),
        }
        if woki_days is not None:
            woki_working = [d for d in woki_days if d["is_working"]]
            if woki_working:
                woki_daily_pcts = [d["abs_pct"] for d in woki_working if d["abs_pct"] is not None]
                w_pct = sum(woki_daily_pcts) / len(woki_daily_pcts) if woki_daily_pcts else None
                t["abs_pct_woki_display"] = f"{w_pct:.1f}%" if w_pct is not None else ""
            else:
                t["abs_pct_woki_display"] = ""
        return t

    def _group_weeks(days: list[dict]) -> list[dict]:
        weeks = []
        for iso_week, grp in _groupby(days, key=lambda d: d["iso_week"]):
            week_days = list(grp)
            weeks.append({"label": f"w{iso_week}", "days": week_days, "rowspan": len(week_days)})
        return weeks

    sub_days = _build_days("SUB")
    kik_days = _build_days("KIK")
    sen_days = _build_days("SEN")
    sen_woki_days = _build_days("SEN", ki_filter=True)

    for d, dw in zip(sen_days, sen_woki_days):
        if not d["is_working"]:
            d["abs_pct_woki_display"] = ""
            continue
        a = int(dw["active"] or 0)
        np_ = int(dw["not_present"] or 0)
        pct_woki = np_ / a * 100 if a > 0 else None
        d["abs_pct_woki_display"] = f"{pct_woki:.2f}%" if pct_woki is not None else ""

    gordon_days = []
    for i, h in enumerate(headers):
        a = int(sub_days[i]["active"] or 0) + int(kik_days[i]["active"] or 0) + int(sen_days[i]["active"] or 0)
        p = int(sub_days[i]["present"] or 0) + int(kik_days[i]["present"] or 0) + int(sen_days[i]["present"] or 0)
        np_ = int(sub_days[i]["not_present"] or 0) + int(kik_days[i]["not_present"] or 0) + int(sen_days[i]["not_present"] or 0)
        gordon_days.append(_make_day(h, a, p, np_))

    def _make_site(name: str, days: list[dict], total: dict, show_ki: bool = False) -> dict:
        weeks = _group_weeks(days)
        site_rowspan = sum(len(w["days"]) for w in weeks) + 1
        for wi, w in enumerate(weeks):
            for di, day in enumerate(w["days"]):
                day["first_in_site"] = wi == 0 and di == 0
                day["first_in_week"] = di == 0
        return {"name": name, "weeks": weeks, "total": total, "show_ki": show_ki, "site_rowspan": site_rowspan}

    sites = [
        _make_site("SUB", sub_days, _compute_total(sub_days)),
        _make_site("KIK", kik_days, _compute_total(kik_days)),
        _make_site("SEN", sen_days, _compute_total(sen_days, sen_woki_days), show_ki=True),
        _make_site("GORDON TOTAL", gordon_days, _compute_total(gordon_days)),
    ]

    return {"title": "ABS Complete", "sites": sites, "records": len(records)}


def build_analytics_data(periods: list[dict]) -> dict[str, object]:
    """
    Build multi-period analytics data for SUB, KIK, SEN sites.
    periods: list of {"month": int, "year": int} dicts, sorted oldest-first.
    """
    SITES = ["SUB", "KIK", "SEN"]

    labels: list[str] = []
    abs_data: dict[str, list] = {s: [] for s in SITES + ["TOTAL", "SEN_WOKI"]}
    pc_data: dict[str, list] = {s: [] for s in SITES + ["TOTAL"]}
    to_data: dict[str, list] = {s: [] for s in SITES + ["TOTAL"]}
    comparison: list[dict] = []

    for period in periods:
        month = period["month"]
        year = period["year"]
        label = f"{month}/{year}"
        labels.append(label)

        records = load_period_records(month, year)
        headers = period_day_headers(year, month)
        day_count = len(headers)

        # --- ABS% and PC avg per site (and GORDON TOTAL) ---
        abs_vals: dict[str, float | None] = {}
        pc_vals: dict[str, float | None] = {}

        site_da: dict[str, list[int]] = {}
        site_dnp: dict[str, list[int]] = {}
        site_dp: dict[str, list[int]] = {}

        for site in SITES:
            da: list[int] = []
            dnp: list[int] = []
            dp: list[int] = []
            for day in range(1, day_count + 1):
                a = np_ = p = 0
                for r in records:
                    loc = _daily_attr(getattr(r, "personnelpresencelocation", None), day)
                    inteos = _daily_attr(getattr(r, "personnelpresenceinteos", None), day)
                    zucchetti = _daily_attr(getattr(r, "personnelpresencezucchetti", None), day)
                    if loc != site or inteos != "1":
                        continue
                    if zucchetti == "1":
                        p += 1
                        a += 1
                    elif zucchetti == "-":
                        np_ += 1
                        a += 1
                da.append(a)
                dnp.append(np_)
                dp.append(p)
            site_da[site] = da
            site_dnp[site] = dnp
            site_dp[site] = dp

            wi = [i for i, v in enumerate(da) if v > 0 and dnp[i] / v * 100 <= 90]
            if wi:
                sum_a = sum(da[i] for i in wi)
                sum_np = sum(dnp[i] for i in wi)
                sum_p = sum(dp[i] for i in wi)
                abs_vals[site] = round(sum_np / sum_a * 100, 2) if sum_a else None
                pc_vals[site] = round(sum_p / len(wi), 1)
            else:
                abs_vals[site] = None
                pc_vals[site] = None

        # --- Woki (SEN only, ABS% without KI) ---
        woki_da: list[int] = []
        woki_dnp: list[int] = []
        for day in range(1, day_count + 1):
            a = np_ = 0
            for r in records:
                if not is_blank(r.ki_to_se):
                    continue
                loc = _daily_attr(getattr(r, "personnelpresencelocation", None), day)
                inteos = _daily_attr(getattr(r, "personnelpresenceinteos", None), day)
                zucchetti = _daily_attr(getattr(r, "personnelpresencezucchetti", None), day)
                if loc != "SEN" or inteos != "1":
                    continue
                if zucchetti == "1":
                    a += 1
                elif zucchetti == "-":
                    np_ += 1
                    a += 1
            woki_da.append(a)
            woki_dnp.append(np_)

        # Per-site holiday flags (>90% absent that day)
        site_holiday = {
            s: [v > 0 and site_dnp[s][i] / v * 100 > 90 for i, v in enumerate(site_da[s])]
            for s in SITES
        }
        # GORDON TOTAL: sum only from non-holiday sites each day
        tot_da  = [sum(site_da[s][i]  for s in SITES if not site_holiday[s][i]) for i in range(day_count)]
        tot_dnp = [sum(site_dnp[s][i] for s in SITES if not site_holiday[s][i]) for i in range(day_count)]
        tot_dp  = [sum(site_dp[s][i]  for s in SITES if not site_holiday[s][i]) for i in range(day_count)]
        tot_wi = [i for i, v in enumerate(tot_da) if v > 0 and tot_dnp[i] / v * 100 <= 90]
        if tot_wi:
            t_sum_a = sum(tot_da[i] for i in tot_wi)
            t_sum_np = sum(tot_dnp[i] for i in tot_wi)
            t_sum_p = sum(tot_dp[i] for i in tot_wi)
            abs_vals["TOTAL"] = round(t_sum_np / t_sum_a * 100, 2) if t_sum_a else None
            pc_vals["TOTAL"] = round(t_sum_p / len(tot_wi), 1)
        else:
            abs_vals["TOTAL"] = None
            pc_vals["TOTAL"] = None

        # Woki working days: align with main SEN working days (same holiday filter)
        sen_wi = [i for i, v in enumerate(site_da["SEN"]) if v > 0 and site_dnp["SEN"][i] / v * 100 <= 90]
        if sen_wi:
            w_sum_a = sum(woki_da[i] for i in sen_wi)
            w_sum_np = sum(woki_dnp[i] for i in sen_wi)
            abs_vals["SEN_WOKI"] = round(w_sum_np / w_sum_a * 100, 2) if w_sum_a else None
        else:
            abs_vals["SEN_WOKI"] = None

        # --- T/O Rate per site ---
        month_prefix = f"{year:04d}-{month:02d}"
        mat_by_code = {
            m.employee_code: m
            for m in PersonnelMasterRecord.objects.filter(month=month, year=year)
        }

        def _was_terminated(employee_code: str) -> bool:
            m = mat_by_code.get(employee_code)
            return bool(m and m.termination_date and str(m.termination_date).startswith(month_prefix))

        to_vals: dict[str, float | None] = {}
        for site in SITES:
            site_records = [r for r in records if normalize(r.current_location) == site]
            lost = sum(1 for r in site_records if _was_terminated(r.employee_code))
            headcount = len(site_records) - lost
            to_vals[site] = round(lost / headcount * 100, 2) if headcount > 0 else None

        # TOTAL T/O
        all_lost = sum(1 for r in records if _was_terminated(r.employee_code))
        all_hc = len(records) - all_lost
        to_vals["TOTAL"] = round(all_lost / all_hc * 100, 2) if all_hc > 0 else None

        # Append to time series
        for key in SITES + ["TOTAL"]:
            abs_data[key].append(abs_vals.get(key))
            pc_data[key].append(pc_vals.get(key))
            to_data[key].append(to_vals.get(key))
        abs_data["SEN_WOKI"].append(abs_vals.get("SEN_WOKI"))

        comparison.append({
            "label": label,
            "abs": {k: abs_vals.get(k) for k in SITES + ["TOTAL", "SEN_WOKI"]},
            "pc": {k: pc_vals.get(k) for k in SITES + ["TOTAL"]},
            "to": {k: to_vals.get(k) for k in SITES + ["TOTAL"]},
        })

    return {
        "labels": labels,
        "abs": abs_data,
        "pc": pc_data,
        "to": to_data,
        "comparison": comparison,
    }


_SITE_PREFIX_MAP = {"SU_": "SUB", "KI_": "KIK", "SE_": "SEN"}

# Categories that form "Op. in line TOTAL" (must appear in this order)
_INLINE_CATS = [
    ("OP. IN LINE", "Sew. op. in line"),
    ("QC IN LINE", "Qc in line"),
    ("TRAIN IN LINE", "Training in line"),
    ("PERM. NO LOG", "Perm. not logging in"),
]

# Categories that are outside Op. in line TOTAL (site-specific)
_EXTRA_CATS_SUB = [
    ("TRAIN C.", "Op. in training center"),
    ("PREP", "Op. in preproduction"),
    ("BOND", "Op. on bonding (temp.)"),
    ("MOVED", "Op. moved (temp.)"),
    ("FROM CUTTING", "Op. from cutting"),
]
_EXTRA_CATS_KIK = [
    ("TRAIN C.", "Op. in training center"),
    ("PREP", "Op. in preproduction"),
    ("MOVED", "Op. moved (temp.)"),
]
_EXTRA_CATS_SEN = [
    ("TRAIN C.", "Op. in training center"),
    ("PREP", "Op. in preproduction"),
    ("MOVED", "Op. moved (temp.)"),
]

# Position codes that count as "logging" for the summary metric
_LOGGING_CATS = {"OP. IN LINE", "QC IN LINE"}


def _parse_position(pos: str) -> tuple[str, str]:
    """Returns (site_code, category_key) e.g. ('SUB', 'OP. IN LINE')."""
    p = pos.strip().upper()
    for prefix, site in _SITE_PREFIX_MAP.items():
        if p.startswith(prefix):
            return site, p[len(prefix):]
    return "", ""


def build_actual_vs_budget_report(month: int, year: int) -> dict[str, object] | None:
    from django.db.models import Count

    qs = PersonnelActualData.objects.filter(month=month, year=year)
    if not qs.exists():
        return None

    # Count per position for after and before separately
    after_counts: dict[str, int] = {}
    before_counts: dict[str, int] = {}
    for row in qs.values("actual_pos_after", "actual_pos_before"):
        a = row["actual_pos_after"].strip().upper() if row["actual_pos_after"] else ""
        b = row["actual_pos_before"].strip().upper() if row["actual_pos_before"] else ""
        if a:
            after_counts[a] = after_counts.get(a, 0) + 1
        if b:
            before_counts[b] = before_counts.get(b, 0) + 1

    def site_data(site: str, extra_cats: list) -> dict:
        prefix = site[:2].upper() + "_"  # "SU_", "KI_", "SE_"

        def get(cat_key: str, counts: dict) -> int:
            return counts.get(prefix + cat_key, 0)

        # Inline rows
        inline_rows = []
        inline_after = 0
        inline_before = 0
        for cat_key, label in _INLINE_CATS:
            a = get(cat_key, after_counts)
            b = get(cat_key, before_counts)
            inline_rows.append({"label": label, "after": a, "before": b})
            inline_after += a
            inline_before += b

        # Extra rows
        extra_rows = []
        extra_after = 0
        extra_before = 0
        for cat_key, label in extra_cats:
            a = get(cat_key, after_counts)
            b = get(cat_key, before_counts)
            extra_rows.append({"label": label, "after": a, "before": b})
            extra_after += a
            extra_before += b

        total_after = inline_after + extra_after
        total_before = inline_before + extra_before
        logging_after = get("OP. IN LINE", after_counts) + get("QC IN LINE", after_counts)
        logging_before = get("OP. IN LINE", before_counts) + get("QC IN LINE", before_counts)
        delta = logging_after - logging_before

        # rowspan = len(inline_rows) + 1 (subtotal) + len(extra_rows) + 1 (Op. TOTAL)
        rowspan = len(inline_rows) + 1 + len(extra_rows) + 1

        return {
            "name": f"Op. in line {site}",
            "inline_rows": inline_rows,
            "inline_total_after": inline_after,
            "inline_total_before": inline_before,
            "extra_rows": extra_rows,
            "total_after": total_after,
            "total_before": total_before,
            "logging_after": logging_after,
            "logging_before": logging_before,
            "delta": delta,
            "direction": "↑" if delta > 0 else ("↓" if delta < 0 else "→"),
            "rowspan": rowspan,
        }

    sites = [
        site_data("SUB", _EXTRA_CATS_SUB),
        site_data("KIK", _EXTRA_CATS_KIK),
        site_data("SEN", _EXTRA_CATS_SEN),
    ]

    # Attach budget plan data per site
    budget_qs = BudgetPlanData.objects.filter(month=month, year=year)
    budget_by_site: dict[str, BudgetPlanData] = {b.site: b for b in budget_qs}
    gordon_target = 0
    gordon_max_capacity = 0
    for s in sites:
        b = budget_by_site.get(s["name"].split()[-1])  # "Op. in line SUB" → "SUB"
        if b:
            s["max_capacity"] = b.max_capacity
            gap_pct = b.budgeted_turnover_gap
            s["budgeted_turnover_gap"] = f"{float(gap_pct)*100:.2f}%" if gap_pct is not None else None
            s["target"] = b.target
            s["actual_minus_target"] = (s["logging_after"] - b.target) if b.target is not None else None
            if b.max_capacity:
                s["actual_turnover_gap"] = f"{(b.max_capacity - s['logging_after']) / b.max_capacity * 100:.2f}%"
            else:
                s["actual_turnover_gap"] = None
            gordon_target += b.target or 0
            gordon_max_capacity += b.max_capacity or 0
        else:
            s["max_capacity"] = None
            s["budgeted_turnover_gap"] = None
            s["target"] = None
            s["actual_minus_target"] = None
            s["actual_turnover_gap"] = None

    gordon_logging_after = sum(s["logging_after"] for s in sites)
    gordon_logging_before = sum(s["logging_before"] for s in sites)
    gordon_total_after = sum(s["total_after"] for s in sites)
    gordon_total_before = sum(s["total_before"] for s in sites)
    gordon_delta = gordon_logging_after - gordon_logging_before
    gordon_actual_minus_target = (gordon_logging_after - gordon_target) if gordon_target else None
    if gordon_max_capacity:
        gordon_actual_turnover_gap = f"{(gordon_max_capacity - gordon_logging_after) / gordon_max_capacity * 100:.2f}%"
    else:
        gordon_actual_turnover_gap = None

    return {
        "title": "ACTUAL vs BUDGET",
        "sites": sites,
        "gordon": {
            "logging_after": gordon_logging_after,
            "logging_before": gordon_logging_before,
            "total_after": gordon_total_after,
            "total_before": gordon_total_before,
            "delta": gordon_delta,
            "direction": "↑" if gordon_delta > 0 else ("↓" if gordon_delta < 0 else "→"),
            "max_capacity": gordon_max_capacity or None,
            "target": gordon_target or None,
            "actual_minus_target": gordon_actual_minus_target,
            "actual_turnover_gap": gordon_actual_turnover_gap,
        },
        "has_budget": bool(budget_by_site),
    }
