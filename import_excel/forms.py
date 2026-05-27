from __future__ import annotations

from django import forms

from .models import (
    PersonnelMasterRecord,
    PersonnelPresence,
    PersonnelPresenceDepartment,
    PersonnelPresenceInteos,
    PersonnelPresenceLocation,
    PersonnelPresenceShift,
    PersonnelPresenceZucchetti,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css_class = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{css_class} form-control".strip()


class PersonnelPresenceForm(StyledModelForm):
    class Meta:
        model = PersonnelPresence
        fields = [
            "employee_code",
            "employee_name",
            "current_department",
            "employee_type",
            "current_location",
            "change_date",
            "previous_department",
            "previous_location",
            "start_day",
            "end_day",
            "ki_to_se",
            "actual",
            "month",
            "year",
        ]


class DailyRecordForm(StyledModelForm):
    class Meta:
        fields = [f"day{day}" for day in range(1, 32)]


class PersonnelPresenceDepartmentForm(DailyRecordForm):
    class Meta(DailyRecordForm.Meta):
        model = PersonnelPresenceDepartment


class PersonnelPresenceLocationForm(DailyRecordForm):
    class Meta(DailyRecordForm.Meta):
        model = PersonnelPresenceLocation


class PersonnelPresenceShiftForm(DailyRecordForm):
    class Meta(DailyRecordForm.Meta):
        model = PersonnelPresenceShift


class PersonnelPresenceInteosForm(DailyRecordForm):
    class Meta(DailyRecordForm.Meta):
        model = PersonnelPresenceInteos


class PersonnelPresenceZucchettiForm(DailyRecordForm):
    class Meta(DailyRecordForm.Meta):
        model = PersonnelPresenceZucchetti


class PersonnelMasterRecordForm(StyledModelForm):
    class Meta:
        model = PersonnelMasterRecord
        fields = [
            "hire_date",
            "termination_date",
            "job_title",
            "department",
            "employment_status",
            "seniority_months",
            "category",
        ]
