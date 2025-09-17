from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    # Authentication
    path("register/", views.create_user, name="register"),
    path("oauth-google/", views.oauth_google, name="oauth-google"),
    path("login/", TokenObtainPairView.as_view(), name="get_token"),
    path("token/verify/", TokenVerifyView.as_view(), name="verify_token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="refresh_token"),
    path("user/profile/", views.user_profile, name="user_profile"),
    # Reports
    path("reports/", views.report_list, name="report_list"),
    path("reports/upload/", views.report_upload, name="report_upload"),
    path("reports/upload", views.report_upload),  # allow missing trailing slash for POST
    path("reports/<int:report_id>/", views.report_detail, name="report_detail"),
    path("reports/<int:report_id>/facts/", views.report_facts, name="report_facts"),
    path("reports/<int:report_id>/summary/", views.report_summary, name="report_summary"),
    path("reports/<int:report_id>/delete/", views.report_delete, name="report_delete"),
    path("reports/<int:report_id>/delete", views.report_delete),
    path("reports/<int:report_id>/download/original/", views.download_original, name="download_original"),
    path("reports/<int:report_id>/download/oim-json/", views.download_oim_json, name="download_oim_json"),
    path("companies/", views.companies_list, name="companies_list"),
    path("companies", views.companies_list),  # allow missing trailing slash for POST
    # vSME Register (avoid conflict with user registration endpoint)
    path("vsme-register/", views.register_list, name="vsme_register_list"),
    path("vsme-register/export.csv", views.register_export_csv, name="vsme_register_export_csv"),
    path("vsme-register/<int:company_id>/<int:year>/", views.register_detail, name="vsme_register_detail"),
]
