from django.contrib import admin
from .models import Report, Fact, Company, VsmeRegister


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "company", "reporting_year", "entity", "reporting_period", "status", "created_at")
    list_filter = ("status", "created_at", "company", "reporting_year")
    search_fields = ("entity", "reporting_period", "owner__username", "company__name")


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "concept", "unit", "context", "created_at")
    list_filter = ("report",)
    search_fields = ("concept", "value", "unit", "context")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(VsmeRegister)
class VsmeRegisterAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "year", "entity_identifier", "completeness_score", "updated_at")
    list_filter = ("company", "year")
    search_fields = ("company__name", "entity_identifier")
