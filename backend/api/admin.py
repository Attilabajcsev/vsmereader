from django.contrib import admin
from .models import Report, Fact


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "entity", "reporting_period", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("entity", "reporting_period", "owner__username")


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "concept", "unit", "context", "created_at")
    list_filter = ("report",)
    search_fields = ("concept", "value", "unit", "context")
