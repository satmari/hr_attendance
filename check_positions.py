import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrapp.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()
from django.db.models import Count
from import_excel.models import PersonnelActualData

for m, y in [(3, 2026), (4, 2026)]:
    print(f"\n=== {m}/{y} ===")
    qs = (PersonnelActualData.objects
          .filter(month=m, year=y)
          .values('actual_pos_after')
          .annotate(n=Count('id'))
          .order_by('actual_pos_after'))
    for row in qs:
        pos = row['actual_pos_after']
        n = row['n']
        # highlight non-dash, non-SU/KI/SE
        flag = ''
        p = pos.strip().upper() if pos else ''
        if p and p != '-' and not (p.startswith('SU_') or p.startswith('KI_') or p.startswith('SE_')):
            flag = ' <-- UNKNOWN'
        print(f"  {pos!r:40s} {n:4d}{flag}")
