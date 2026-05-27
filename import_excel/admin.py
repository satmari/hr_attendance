from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


class CustomUserAdmin(UserAdmin):
    def get_groups(self, obj):
        return ", ".join(g.name for g in obj.groups.all()) or "-"
    get_groups.short_description = "Groups"

    list_display = ("username", "email", "first_name", "last_name", "get_groups", "is_staff")


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

from .models import (
    BudgetPlanData,
    ExcelImportLog,
    ImportedData,
    PersonnelPresence,
    PersonnelMasterRecord,
    PersonnelActualData,
    PersonnelPresenceDepartment,
    PersonnelPresenceInteos,
    PersonnelPresenceLocation,
    PersonnelPresenceShift,
    PersonnelPresenceZucchetti,
)


@admin.register(PersonnelPresence)
class PersonnelPresenceAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "employee_name", "month", "year", "current_department", "current_location")
    list_filter = ("year", "month", "current_department", "current_location")
    search_fields = ("employee_code", "employee_name")


@admin.register(ExcelImportLog)
class ExcelImportLogAdmin(admin.ModelAdmin):
    list_display = ("original_file_name", "status", "month", "year", "total_rows", "imported_rows", "created_at")
    list_filter = ("status", "year", "month")
    search_fields = ("original_file_name",)


@admin.register(ImportedData)
class ImportedDataAdmin(admin.ModelAdmin):
    list_display = ("import_log", "row_number", "created_at")
    list_filter = ("import_log",)


@admin.register(PersonnelMasterRecord)
class PersonnelMasterRecordAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "month", "year", "job_title", "department")
    list_filter = ("year", "month", "department")


@admin.register(PersonnelActualData)
class PersonnelActualDataAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "employee_name", "month", "year", "actual_pos_after", "actual_pos_before")
    list_filter = ("year", "month")
    search_fields = ("employee_code", "employee_name")


@admin.register(BudgetPlanData)
class BudgetPlanDataAdmin(admin.ModelAdmin):
    list_display = ("site", "month", "year", "max_capacity", "budgeted_turnover_gap", "target")
    list_filter = ("year", "month", "site")


admin.site.register(PersonnelPresenceDepartment)
admin.site.register(PersonnelPresenceLocation)
admin.site.register(PersonnelPresenceShift)
admin.site.register(PersonnelPresenceInteos)
admin.site.register(PersonnelPresenceZucchetti)
