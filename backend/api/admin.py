from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "entity", "reporting_period", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("entity", "reporting_period", "owner__username")
