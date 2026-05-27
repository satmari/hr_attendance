# HR Attendance

## Trenutni status

Ovo je Django projekat za import i pregled HR Excel podataka iz `main` sheeta.

Trenutno radi:
- import Excel fajla sa `main` sheeta
- automatsko čitanje perioda iz fajla (`mesec/godina`)
- upis u glavnu tabelu `personnel_presence`
- upis u dodatne tabele:
  - `personnel_presence_department`
  - `personnel_presence_location`
  - `personnel_presence_shift`
  - `personnel_presence_inteos`
  - `personnel_presence_zucchetti`
- staging log kroz `ExcelImportLog` i `ImportedData`
- Pregled unosa
- ručni edit glavnog zapisa i svih dodatnih tabela

Jedinstveni ključ glavne tabele je:
- `employee_code + month + year`

## Rute

- `/`
- `/import/`
- `/personnel/`
- `/personnel/<id>/edit/`
- `/admin/`

API:
- `/api/import/upload/`
- `/api/import/preview/`
- `/api/import/headers/`
- `/api/import/sheets/`
- `/api/import/status/<import_id>/`
- `/api/import/data/<import_id>/`

## Pokretanje

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Baza

Trenutno projekat radi na `SQLite` lokalno preko `db.sqlite3`.

MSSQL podrška je pripremljena kroz:
- `USE_MSSQL=True`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_DRIVER`
