from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models


def daily_value_fields(prefix: str = "day") -> dict[str, models.Field]:
    return {
        f"{prefix}{day}": models.CharField(max_length=255, blank=True, default="")
        for day in range(1, 32)
    }


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PersonnelPresence(TimeStampedModel):
    employee_code = models.CharField(max_length=100)
    employee_name = models.CharField(max_length=255, blank=True, default="")
    current_department = models.CharField(max_length=255, blank=True, default="")
    employee_type = models.CharField(max_length=100, blank=True, default="")
    current_location = models.CharField(max_length=255, blank=True, default="")
    change_date = models.CharField(max_length=100, blank=True, default="")
    previous_department = models.CharField(max_length=255, blank=True, default="")
    previous_location = models.CharField(max_length=255, blank=True, default="")
    start_day = models.CharField(max_length=50, blank=True, default="")
    end_day = models.CharField(max_length=50, blank=True, default="")
    ki_to_se = models.CharField(max_length=100, blank=True, default="")
    actual = models.CharField(max_length=100, blank=True, default="")
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "personnel_presence"
        ordering = ["year", "month", "employee_code", "employee_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee_code", "month", "year"],
                name="unique_employee_month_year",
            )
        ]

    def __str__(self) -> str:
        return f"{self.employee_code} - {self.employee_name} ({self.month}/{self.year})"

    def clean(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValidationError({"month": "Month must be between 1 and 12."})


class AbstractDailyRecord(TimeStampedModel):
    presence = models.OneToOneField(PersonnelPresence, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class PersonnelPresenceDepartment(AbstractDailyRecord):
    class Meta:
        db_table = "personnel_presence_department"


class PersonnelPresenceLocation(AbstractDailyRecord):
    class Meta:
        db_table = "personnel_presence_location"


class PersonnelPresenceShift(AbstractDailyRecord):
    class Meta:
        db_table = "personnel_presence_shift"


class PersonnelPresenceInteos(AbstractDailyRecord):
    class Meta:
        db_table = "personnel_presence_inteos"


class PersonnelPresenceZucchetti(AbstractDailyRecord):
    class Meta:
        db_table = "personnel_presence_zucchetti"


for model in [
    PersonnelPresenceDepartment,
    PersonnelPresenceLocation,
    PersonnelPresenceShift,
    PersonnelPresenceInteos,
    PersonnelPresenceZucchetti,
]:
    for field_name, field in daily_value_fields().items():
        field.contribute_to_class(model, field_name)


class PersonnelMasterRecord(TimeStampedModel):
    """ Tabela: maticna_knjiga (iz 'mat' sheeta - Table2) """
    employee_code = models.CharField(max_length=100)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()

    hire_date = models.CharField(max_length=100, blank=True, default="")
    termination_date = models.CharField(max_length=100, blank=True, default="")
    job_title = models.CharField(max_length=255, blank=True, default="")
    department = models.CharField(max_length=255, blank=True, default="")
    employment_status = models.CharField(max_length=100, blank=True, default="")
    seniority_months = models.CharField(max_length=100, blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "maticna_knjiga"
        unique_together = ("employee_code", "month", "year")

    def __str__(self) -> str:
        return f"Master: {self.employee_code} ({self.month}/{self.year})"


class PersonnelActualData(TimeStampedModel):
    """ Tabela za ACTUAL data sheet — pozicija zaposlenog u dva preseka (before/after). """
    employee_code = models.CharField(max_length=100)
    employee_name = models.CharField(max_length=255, blank=True, default="")
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    actual_pos_after = models.CharField(max_length=255, blank=True, default="")
    actual_pos_before = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "personnel_actual_data"
        unique_together = ("employee_code", "month", "year")

    def __str__(self) -> str:
        return f"Actual {self.employee_code} ({self.month}/{self.year})"


class BudgetPlanData(TimeStampedModel):
    """Ručno unete budget vrednosti po sajtu i periodu za ACTUAL vs BUDGET izveštaj."""
    SITE_SUB = "SUB"
    SITE_KIK = "KIK"
    SITE_SEN = "SEN"
    SITE_CHOICES = [(SITE_SUB, "SUB"), (SITE_KIK, "KIK"), (SITE_SEN, "SEN")]

    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    site = models.CharField(max_length=3, choices=SITE_CHOICES)
    max_capacity = models.PositiveIntegerField(null=True, blank=True)
    budgeted_turnover_gap = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True,
                                                 help_text="Npr. 0.33 za 33%")
    target = models.PositiveIntegerField(null=True, blank=True, help_text="Op. in line logging on iPad TARGET")

    class Meta:
        db_table = "budget_plan_data"
        unique_together = ("month", "year", "site")

    def __str__(self) -> str:
        return f"Budget {self.site} {self.month}/{self.year}"


class ExcelImportLog(TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    original_file_name = models.CharField(max_length=255)
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    replace_existing = models.BooleanField(default=False)
    detected_sheet = models.CharField(max_length=100, blank=True, default="")
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.original_file_name} - {self.status}"


class ImportedData(TimeStampedModel):
    import_log = models.ForeignKey(ExcelImportLog, on_delete=models.CASCADE, related_name="imported_rows_data")
    row_number = models.PositiveIntegerField()
    raw_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["row_number"]

    def __str__(self) -> str:
        return f"Import #{self.import_log_id} row {self.row_number}"
