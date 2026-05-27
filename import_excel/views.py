from __future__ import annotations

import json
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import (
    PersonnelMasterRecordForm,
    PersonnelPresenceDepartmentForm,
    PersonnelPresenceForm,
    PersonnelPresenceInteosForm,
    PersonnelPresenceLocationForm,
    PersonnelPresenceShiftForm,
    PersonnelPresenceZucchettiForm,
)
from .models import BudgetPlanData, PersonnelActualData, ExcelImportLog, PersonnelMasterRecord, PersonnelPresence
from .reporting import (
    build_abs_comp_report,
    build_abs_report,
    build_abs_se_without_ki_report,
    build_actual_vs_budget_report,
    build_analytics_data,
    build_pc_report,
    build_to_report,
)
from .services import import_workbook, preview_workbook, delete_period_data


@login_required
def home(request: HttpRequest) -> HttpResponse:
    latest_import = ExcelImportLog.objects.first()
    context = {"latest_import": latest_import}
    return render(request, "import_excel/home.html", context)


@login_required
def import_center(request: HttpRequest) -> HttpResponse:
    periods = (
        PersonnelPresence.objects.values("month", "year")
        .annotate(total=Count("id"))
        .order_by("-year", "-month")
    )
    recent_imports = ExcelImportLog.objects.all()[:8]
    return render(
        request,
        "import_excel/index.html",
        {
            "existing_periods": periods,
            "recent_imports": recent_imports,
        },
    )


def _report_period_context(request: HttpRequest) -> dict[str, object]:
    periods = list(
        PersonnelPresence.objects.values("month", "year")
        .annotate(total=Count("id"))
        .order_by("-year", "-month")
    )
    month_param = request.GET.get("month", "").strip()
    year_param = request.GET.get("year", "").strip()

    selected_period = periods[0] if periods else {"month": None, "year": None}
    if month_param.isdigit() and year_param.isdigit():
        selected_period = {"month": int(month_param), "year": int(year_param)}

    return {
        "periods": periods,
        "selected_month": selected_period["month"],
        "selected_year": selected_period["year"],
    }


@login_required
def personnel_presence_list(request: HttpRequest) -> HttpResponse:
    queryset = PersonnelPresence.objects.all()
    month = request.GET.get("month", "").strip()
    year = request.GET.get("year", "").strip()
    search = request.GET.get("search", "").strip()

    if month.isdigit():
        queryset = queryset.filter(month=int(month))
    if year.isdigit():
        queryset = queryset.filter(year=int(year))
    if search:
        queryset = queryset.filter(Q(employee_code__icontains=search) | Q(employee_name__icontains=search))
    queryset = queryset.order_by("year", "month", "employee_code", "employee_name")

    # Da bismo prikazali podatke iz MAT table (maticna_knjiga), 
    # moramo ih dobaviti za isti period.
    results = list(queryset[:250])
    for p in results:
        p.master_record = PersonnelMasterRecord.objects.filter(
            employee_code=p.employee_code, 
            month=p.month, 
            year=p.year
        ).first()

    periods = (
        PersonnelPresence.objects.values("month", "year")
        .annotate(total=Count("id"))
        .order_by("-year", "-month")
    )
    return render(
        request,
        "import_excel/personnel_presence_list.html",
        {
            "records": results,
            "record_count": queryset.count(),
            "periods": periods,
            "filters": {"month": month, "year": year, "search": search},
        },
    )


def _render_sheet_report(request: HttpRequest, report_builder, report_key: str, page_title: str) -> HttpResponse:
    period_context = _report_period_context(request)
    month = period_context["selected_month"]
    year = period_context["selected_year"]
    report = None
    if month and year:
        report = report_builder(month, year)
    return render(
        request,
        "import_excel/report_sheet.html",
        {
            "report": report,
            "periods": period_context["periods"],
            "selected_month": month,
            "selected_year": year,
            "report_key": report_key,
            "page_title": page_title,
        },
    )


@login_required
def report_pc(request: HttpRequest) -> HttpResponse:
    return _render_sheet_report(request, build_pc_report, "pc", "PC")


@login_required
def report_abs(request: HttpRequest) -> HttpResponse:
    period_context = _report_period_context(request)
    month = period_context["selected_month"]
    year = period_context["selected_year"]
    report = build_abs_report(month, year) if month and year else None
    return render(
        request,
        "import_excel/report_abs.html",
        {
            "report": report,
            "periods": period_context["periods"],
            "selected_month": month,
            "selected_year": year,
            "page_title": "Absenteeism",
        },
    )


@login_required
def report_abs_se_without_ki(request: HttpRequest) -> HttpResponse:
    period_context = _report_period_context(request)
    month = period_context["selected_month"]
    year = period_context["selected_year"]
    report = build_abs_se_without_ki_report(month, year) if month and year else None
    return render(
        request,
        "import_excel/report_abs.html",
        {
            "report": report,
            "periods": period_context["periods"],
            "selected_month": month,
            "selected_year": year,
            "page_title": "Absenteeism SE without KI",
        },
    )


@login_required
def report_to(request: HttpRequest) -> HttpResponse:
    return _render_sheet_report(request, build_to_report, "to", "Turnover")


@login_required
def report_abs_comp(request: HttpRequest) -> HttpResponse:
    period_context = _report_period_context(request)
    month = period_context["selected_month"]
    year = period_context["selected_year"]
    report = build_abs_comp_report(month, year) if month and year else None
    return render(
        request,
        "import_excel/abs_comp.html",
        {
            "report": report,
            "periods": period_context["periods"],
            "selected_month": month,
            "selected_year": year,
            "page_title": "ABS Complete",
        },
    )


@login_required
def report_actual_vs_budget(request: HttpRequest) -> HttpResponse:
    period_context = _report_period_context(request)
    month = period_context["selected_month"]
    year = period_context["selected_year"]
    report = build_actual_vs_budget_report(month, year) if month and year else None

    # Load existing budget entries for the budget form (gap stored as decimal, displayed as %)
    budget_entries: dict[str, dict] = {}
    if month and year:
        for b in BudgetPlanData.objects.filter(month=month, year=year):
            budget_entries[b.site] = {
                "max_capacity": b.max_capacity if b.max_capacity is not None else "",
                "budgeted_turnover_gap": f"{float(b.budgeted_turnover_gap)*100:.2f}" if b.budgeted_turnover_gap is not None else "",
                "target": b.target if b.target is not None else "",
            }

    return render(
        request,
        "import_excel/report_avb.html",
        {
            "report": report,
            "periods": period_context["periods"],
            "selected_month": month,
            "selected_year": year,
            "page_title": "ACTUAL vs BUDGET",
            "budget_entries": budget_entries,
            "sites": ["SUB", "KIK", "SEN"],
        },
    )


@login_required
@require_POST
def api_save_budget(request: HttpRequest) -> JsonResponse:
    try:
        month = int(request.POST.get("month", 0))
        year = int(request.POST.get("year", 0))
        if not month or not year:
            return JsonResponse({"error": "month/year required"}, status=400)
        for site in ["SUB", "KIK", "SEN"]:
            def _int(val: str | None) -> int | None:
                if val is None or val.strip() == "":
                    return None
                try:
                    return int(val)
                except ValueError:
                    return None

            def _dec(val: str | None):
                if val is None or val.strip() == "":
                    return None
                try:
                    v = val.strip().rstrip("%")
                    return float(v) / 100
                except ValueError:
                    return None

            BudgetPlanData.objects.update_or_create(
                month=month, year=year, site=site,
                defaults={
                    "max_capacity": _int(request.POST.get(f"{site}_max_capacity")),
                    "budgeted_turnover_gap": _dec(request.POST.get(f"{site}_budgeted_turnover_gap")),
                    "target": _int(request.POST.get(f"{site}_target")),
                },
            )
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def api_delete_period(request: HttpRequest) -> JsonResponse:
    try:
        month = request.POST.get("month")
        year = request.POST.get("year")
        if not month or not year:
            return JsonResponse({"success": False, "message": "Month and Year are required."}, status=400)
        
        delete_period_data(int(month), int(year))
        return JsonResponse({"success": True, "message": f"Data for {month}/{year} deleted."})
    except Exception as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


@login_required
@require_POST
def api_clear_import_log(request: HttpRequest) -> JsonResponse:
    try:
        deleted, _ = ExcelImportLog.objects.all().delete()
        return JsonResponse({"success": True, "message": f"Obrisano {deleted} log zapisa."})
    except Exception as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=500)


def _get_related_forms(request: HttpRequest | None, presence: PersonnelPresence) -> dict[str, Any]:
    instances = {
        "department_form": PersonnelPresenceDepartmentForm(
            request.POST or None,
            instance=getattr(presence, "personnelpresencedepartment", None),
            prefix="department",
        ),
        "location_form": PersonnelPresenceLocationForm(
            request.POST or None,
            instance=getattr(presence, "personnelpresencelocation", None),
            prefix="location",
        ),
        "shift_form": PersonnelPresenceShiftForm(
            request.POST or None,
            instance=getattr(presence, "personnelpresenceshift", None),
            prefix="shift",
        ),
        "inteos_form": PersonnelPresenceInteosForm(
            request.POST or None,
            instance=getattr(presence, "personnelpresenceinteos", None),
            prefix="inteos",
        ),
        "zucchetti_form": PersonnelPresenceZucchettiForm(
            request.POST or None,
            instance=getattr(presence, "personnelpresencezucchetti", None),
            prefix="zucchetti",
        ),
    }
    return instances


@login_required
@require_http_methods(["GET", "POST"])
def personnel_presence_edit(request: HttpRequest, pk: int) -> HttpResponse:
    presence = get_object_or_404(PersonnelPresence, pk=pk)
    master_record = PersonnelMasterRecord.objects.filter(
        employee_code=presence.employee_code,
        month=presence.month,
        year=presence.year,
    ).first()

    main_form = PersonnelPresenceForm(request.POST or None, instance=presence, prefix="main")
    master_form = PersonnelMasterRecordForm(request.POST or None, instance=master_record, prefix="master")
    related_forms = _get_related_forms(request, presence)

    if request.method == "POST":
        all_forms = [main_form, master_form, *related_forms.values()]
        if all(form.is_valid() for form in all_forms):
            presence = main_form.save()
            if master_form.has_changed():
                master_instance = master_form.save(commit=False)
                master_instance.employee_code = presence.employee_code
                master_instance.month = presence.month
                master_instance.year = presence.year
                master_instance.save()
            for form in related_forms.values():
                instance = form.save(commit=False)
                instance.presence = presence
                instance.save()
            messages.success(request, "Employee record updated successfully.")
            return redirect("personnel_presence_edit", pk=presence.pk)
        messages.error(request, "Please correct the highlighted fields.")

    return render(
        request,
        "import_excel/personnel_presence_edit.html",
        {
            "presence": presence,
            "main_form": main_form,
            "master_form": master_form,
            **related_forms,
        },
    )


@login_required
def analytics(request: HttpRequest) -> HttpResponse:
    periods = list(
        PersonnelPresence.objects.values("month", "year")
        .annotate(total=Count("id"))
        .order_by("year", "month")  # oldest first for charts
    )
    analytics_data = build_analytics_data(periods) if periods else None
    return render(request, "import_excel/analytics.html", {
        "analytics_data": analytics_data,
        "analytics_data_json": json.dumps(analytics_data),
        "periods": periods,
    })


def _get_uploaded_file_bytes(request: HttpRequest) -> tuple[bytes, str]:
    upload = request.FILES.get("file")
    if not upload:
        raise ValueError("Excel file is required.")
    return upload.read(), upload.name


@login_required
@require_POST
def api_import_upload(request: HttpRequest) -> JsonResponse:
    try:
        file_bytes, file_name = _get_uploaded_file_bytes(request)
        month = request.POST.get("month")
        year = request.POST.get("year")
        replace_existing = request.POST.get("replace_existing") == "true"
        import_log = import_workbook(
            file_bytes,
            file_name,
            selected_month=int(month) if month and month.isdigit() else None,
            selected_year=int(year) if year and year.isdigit() else None,
            replace_existing=replace_existing,
        )
        return JsonResponse(
            {
                "success": True,
                "import_id": import_log.id,
                "status": import_log.status,
                "month": import_log.month,
                "year": import_log.year,
                "imported_rows": import_log.imported_rows,
                "message": import_log.message,
            }
        )
    except Exception as exc:
        log = ExcelImportLog.objects.create(
            original_file_name=request.FILES.get("file").name if request.FILES.get("file") else "unknown",
            status=ExcelImportLog.STATUS_FAILED,
            message=str(exc),
        )
        return JsonResponse({"success": False, "import_id": log.id, "message": str(exc)}, status=400)


@login_required
@require_POST
def api_import_preview(request: HttpRequest) -> JsonResponse:
    try:
        file_bytes, _file_name = _get_uploaded_file_bytes(request)
        data = preview_workbook(file_bytes)  # Uvek preview main
        return JsonResponse({"success": True, **data})
    except Exception as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=400)


@login_required
@require_POST
def api_import_headers(request: HttpRequest) -> JsonResponse:
    try:
        file_bytes, _file_name = _get_uploaded_file_bytes(request)
        data = preview_workbook(file_bytes, limit=1)  # Uvek uzimamo headere iz main
        return JsonResponse({"success": True, "headers": data["headers"]})
    except Exception as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=400)


@login_required
@require_GET
def api_import_status(request: HttpRequest, import_id: int) -> JsonResponse:
    import_log = get_object_or_404(ExcelImportLog, pk=import_id)
    return JsonResponse(
        {
            "success": True,
            "import_id": import_log.id,
            "status": import_log.status,
            "month": import_log.month,
            "year": import_log.year,
            "total_rows": import_log.total_rows,
            "imported_rows": import_log.imported_rows,
            "message": import_log.message,
            "created_at": import_log.created_at.isoformat(),
            "updated_at": import_log.updated_at.isoformat(),
        }
    )


@login_required
@require_GET
def api_import_data(request: HttpRequest, import_id: int) -> JsonResponse:
    import_log = get_object_or_404(ExcelImportLog, pk=import_id)
    rows = list(import_log.imported_rows_data.values("row_number", "raw_payload")[:50])
    return JsonResponse({"success": True, "rows": rows, "count": import_log.imported_rows_data.count()})
