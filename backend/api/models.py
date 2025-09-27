from django.db import models
from django.contrib.auth.models import User
from django.db import models as dj_models


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Report(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        VALIDATED = "validated", "Validated"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="reports")
    reporting_year = models.PositiveIntegerField()
    user_report_number = models.PositiveIntegerField(default=1, help_text="Sequential report number per user")
    original_file = models.FileField(upload_to="reports/original/")
    oim_json_file = models.FileField(upload_to="reports/oim/", null=True, blank=True)

    entity = models.CharField(max_length=255, blank=True)
    reporting_period = models.CharField(max_length=255, blank=True)
    taxonomy_version = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    validation_summary = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "reporting_year"], name="unique_company_year")
        ]

    def __str__(self) -> str:
        entity = self.entity or "Unknown entity"
        period = self.reporting_period or "period"
        comp = getattr(self, "company", None)
        cy = f", {self.reporting_year}" if getattr(self, "reporting_year", None) else ""
        cname = f" — {comp.name}" if comp else ""
        report_num = getattr(self, "user_report_number", self.id)
        return f"Report #{report_num}{cname}{cy} — {entity} ({period})"


class Fact(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="facts")
    concept = models.CharField(max_length=512)
    value = models.TextField(blank=True)
    datatype = models.CharField(max_length=256, blank=True)
    unit = models.CharField(max_length=128, blank=True)
    context = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["report", "concept"]),
        ]


class VsmeRegister(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="register_rows")
    year = models.PositiveIntegerField()
    entity_identifier = models.CharField(max_length=255, blank=True)

    # Core ESG metrics (numeric values) and units; all nullable
    employees_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    employees_unit = models.CharField(max_length=64, blank=True)

    ghg_total_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    ghg_total_unit = models.CharField(max_length=64, blank=True)
    ghg_scope1_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    ghg_scope1_unit = models.CharField(max_length=64, blank=True)
    ghg_scope2_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    ghg_scope2_unit = models.CharField(max_length=64, blank=True)

    energy_consumption_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    energy_consumption_unit = models.CharField(max_length=64, blank=True)
    renewable_energy_share_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    renewable_energy_share_unit = models.CharField(max_length=32, blank=True)

    water_withdrawal_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    water_withdrawal_unit = models.CharField(max_length=64, blank=True)
    water_discharge_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    water_discharge_unit = models.CharField(max_length=64, blank=True)

    waste_generated_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    waste_generated_unit = models.CharField(max_length=64, blank=True)
    hazardous_waste_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    hazardous_waste_unit = models.CharField(max_length=64, blank=True)
    non_hazardous_waste_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    non_hazardous_waste_unit = models.CharField(max_length=64, blank=True)

    completeness_score = models.PositiveSmallIntegerField(default=0)  # 0..100 percent
    last_report = models.ForeignKey(Report, on_delete=models.SET_NULL, null=True, blank=True, related_name="register_rows")
    source_concepts = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "year")
        ordering = ["company__name", "year"]

    def __str__(self) -> str:
        return f"Register {self.company.name} {self.year} ({self.completeness_score}%)"
