# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 4.2 web application for importing, managing, and reporting on HR employee attendance data from Excel files. Targets manufacturing sites (SUB/Kikinda, KIK, SEN). UI is English; some field names and documentation are in Serbian.

## Common Commands

```bash
# Activate virtual environment (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create admin user (first time)
python manage.py createsuperuser

# Run dev server (default port 8000)
python manage.py runserver

# Run on specific port (configured in .claude/settings.local.json)
python manage.py runserver 0.0.0.0:8010
```

## Configuration

Copy `.env.example` to `.env`. Key variables:

```ini
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

USE_MSSQL=False          # True to switch from SQLite to MSSQL
DB_NAME=HR_Database
DB_USER=sa
DB_PASSWORD=password
DB_HOST=server-ip
DB_PORT=1433
DB_DRIVER=ODBC Driver 17 for SQL Server
```

The database backend switches based on `USE_MSSQL` in `settings.py`.

## Architecture

The main app is `import_excel/`. Concerns are separated across:

- **`models.py`** — 9 models. `PersonnelPresence` is the central record (one per employee per month/year). Five parallel `OneToOneField` models store daily values (day1–day31 per type): `PersonnelPresenceDepartment`, `PersonnelPresenceLocation`, `PersonnelPresenceShift`, `PersonnelPresenceInteos`, `PersonnelPresenceZucchetti`. Also `PersonnelMasterRecord`, `ActualBudgetData`, `ExcelImportLog`, and `ImportedData`.

- **`services.py`** — Excel import pipeline. `import_workbook()` is the main entry point. Reads three sheets: `"main"` (attendance), `"mat"` (master records), `"ACTUAL data"` (budget). Period (month/year) is auto-detected from row 5 of the main sheet via regex. All import operations are wrapped in `@transaction.atomic`.

- **`reporting.py`** — Six report builders (`build_pc_report`, `build_abs_report`, `build_abs_se_without_ki_report`, `build_to_report`, `build_abs_comp_report`, `build_analytics_data`, `build_actual_vs_budget_report`). All queries filter by `(month, year)`. Heavy use of Django ORM `select_related()` for performance.

- **`views.py`** — 23 view functions, all guarded by `@login_required`. Split between HTML template views (reports, list, edit) and JSON API endpoints under `/api/import/`.

- **`forms.py`** — 7 `ModelForm` subclasses. All extend `StyledModelForm`, which auto-applies Bootstrap `form-control` to every field.

## URL Structure

Web views: `/`, `/import/`, `/personnel/`, `/personnel/<id>/edit/`, `/reports/pc/`, `/reports/abs/`, `/reports/abs-se-without-ki/`, `/reports/to/`, `/reports/abs-comp/`, `/reports/actual-vs-budget/`, `/reports/analytics/`

JSON APIs (POST unless noted): `/api/import/upload/`, `/api/import/preview/`, `/api/import/headers/`, `/api/import/status/<id>/` (GET), `/api/import/data/<id>/` (GET), `/api/import/delete-period/`, `/api/import/clear-log/`

## Excel File Format

The importer expects:
- **Sheet `"main"`**: Row 5 = period string, Row 6 = headers, Row 7+ = data. Required columns include `R`, `NAME`, `DEP sada`, `SUBSID sada`, `KI TO SE`, `START`, `END`, `TYPE`, plus day columns `DEP1`–`DEP31`, `SUB1`–`SUB31`, `SH1`–`SH31`.
- **Sheet `"mat"`** (optional): Row 2 = headers, Row 3+ = master employee data.
- **Sheet `"ACTUAL data"`** (optional): Row 1 = headers, Row 2+ = budget vs actual by department.

## Key Constraints

- `PersonnelPresence` has a unique constraint on `(employee_code, month, year)` — one record per employee per period.
- `PersonnelMasterRecord` and `ActualBudgetData` have similar period-scoped unique constraints.
- All daily related models use `OneToOneField` back to `PersonnelPresence`.
