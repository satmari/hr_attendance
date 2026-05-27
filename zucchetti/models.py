from django.db import models


class ZucchettiEmployee(models.Model):
    emp_code = models.CharField(max_length=10)       # IDEMPLOY
    subject_code = models.CharField(max_length=20)  # IDSUBJECT
    surname = models.CharField(max_length=100)       # ANSURNAM
    name = models.CharField(max_length=100)          # ANNAME
    card_code = models.CharField(max_length=20)      # IDTICKET

    class Meta:
        ordering = ["emp_code"]

    def __str__(self):
        return f"{self.emp_code} – {self.surname} {self.name}"


class NewRequest(models.Model):
    emp_code = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    plant = models.CharField(max_length=20)
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)
    time_out = models.TimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["emp_code"]

    def __str__(self):
        return f"{self.emp_code} – {self.name}"


class PlantSetting(models.Model):
    plant = models.CharField(max_length=20)
    terminal = models.CharField(max_length=100)

    class Meta:
        ordering = ["plant"]

    def __str__(self):
        return f"{self.plant} → {self.terminal}"
