from django.db import models
from django.contrib.auth.models import User


class Report(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        VALIDATED = "validated", "Validated"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports")
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

    def __str__(self) -> str:
        entity = self.entity or "Unknown entity"
        period = self.reporting_period or "period"
        return f"Report #{self.id} — {entity} ({period})"


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

