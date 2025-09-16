from django.contrib.auth.models import User
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
import logging
import json as jsonlib
from django.db.models import Q
from .serializers import (
    UserSerializer,
    OAuthUserRegistrationSerializer,
    ReportUploadSerializer,
    ReportListSerializer,
    ReportDetailSerializer,
    CompanySerializer,
    VsmeRegisterListSerializer,
    VsmeRegisterDetailSerializer,
)
from .models import Report, Fact, Company, VsmeRegister
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework.request import Request
from rest_framework.parsers import MultiPartParser, FormParser
import json
from typing import Any
from .processing import process_report_async
from .oim import extract_metadata, extract_facts

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def create_user(request: Request) -> Response:
    """
    Creates user to the database.
    Endpoint: register/

    Request body:
        - username
        - email
        - first_name
        - last_name
        - password

    Returns:
        - id
        - username
    """
    serializer = UserSerializer(data=request.data)

    if serializer.is_valid():
        user: User = serializer.save()
        return Response(
            {
                "id": user.id,
                "username": user.username,
            },
            status=201,
        )

    print(f"Validation errors: {serializer.errors}")
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile(request: Request) -> Response:
    """
    Gets user profile information
    Endpoint: user/profile/

    Returns:
        - id
        - username
        - email
        - first_name
        - last_name
    """
    try:
        user: User = request.user
        serializer = UserSerializer(user)

        return Response(serializer.data)

    except Exception as e:
        print(f"Validation errors: {str(e)}")
        return Response({"error": "Internal server error"}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
def oauth_google(request: Request) -> Response:
    """
    Verifies Google Auth token and creates User in the database.
    Endpoint: oauth-google/

    Request body:
        - id_token: token recieved on successful Google OAuth

    Returns:
        - access: JWT access token
        - refresh: JWT refresh token
    """

    data: dict[str, Any] = json.loads(request.body)
    google_token: str | None = data.get("id_token")

    if not google_token:
        return Response({"error": "Google token not provided"}, status=400)

    try:
        userinfo: dict[str, Any] = id_token.verify_oauth2_token(
            google_token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        email: str = userinfo["email"]

        user: User = User.objects.filter(email=email).first()

        if not user:
            user_data: dict[str, str] = {
                "username": email,
                "email": email,
                "first_name": userinfo.get("given_name", ""),
                "last_name": userinfo.get("family_name", ""),
            }

            serializer = OAuthUserRegistrationSerializer(
                data=user_data
            )  # Creates new user with default user sync settings and basic user tier
            if serializer.is_valid():
                user = serializer.save()
            else:
                return Response(serializer.errors, status=400)

        # Generate JWT tokens for user
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})

    except ValueError:
        return Response(
            {"error": "Invalid token or token verification failed"}, status=401
        )
    except Exception as e:
        return Response({"error": f"Authentication failed: {str(e)}"}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def report_upload(request: Request) -> Response:
    serializer = ReportUploadSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        report: Report = serializer.save()
        process_report_async(report.id)
        return Response({"id": report.id, "status": report.status}, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_list(request: Request) -> Response:
    q = request.query_params.get("q", "").strip()
    reports = Report.objects.select_related("company").filter(owner=request.user)
    if q:
        # If q looks like a 4-digit year, filter exact by reporting_year
        if q.isdigit() and len(q) == 4:
            reports = reports.filter(reporting_year=int(q))
        else:
            ql = q.lower()
            reports = reports.filter(
                Q(entity__icontains=ql)
                | Q(reporting_period__icontains=ql)
                | Q(company__name__icontains=ql)
            )
    data = ReportListSerializer(reports, many=True).data
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_detail(request: Request, report_id: int) -> Response:
    report = get_object_or_404(Report, id=report_id, owner=request.user)
    data = ReportDetailSerializer(report).data
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_facts(request: Request, report_id: int) -> Response:
    report = get_object_or_404(Report, id=report_id, owner=request.user)
    if not report.oim_json_file:
        return Response({"results": [], "count": 0}, status=200)

    q = (request.query_params.get("q") or "").lower().strip()
    page = max(int(request.query_params.get("page", 1)), 1)
    page_size = max(min(int(request.query_params.get("page_size", 50)), 200), 1)

    facts_qs = Fact.objects.filter(report=report)
    if q:
        facts_qs = facts_qs.filter(
            Q(concept__icontains=q) | Q(value__icontains=q)
        )

    total = facts_qs.count()
    page_rows = facts_qs.order_by('id')[(page - 1) * page_size: (page - 1) * page_size + page_size]
    results = [
        {
            "concept": f.concept,
            "value": f.value,
            "datatype": f.datatype,
            "unit": f.unit,
            "context": f.context,
        }
        for f in page_rows
    ]

    return Response({"results": results, "count": total, "page": page, "page_size": page_size})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_summary(request: Request, report_id: int) -> Response:
    """Return a small vSME ESG summary for the report.

    Structure:
    {
      entity: str,
      reporting_period: str,
      fact_count: int,
      required_count: 5,
      present_count: int,
      items: [
        { label: str, code: str, present: bool, value: str | null }
      ]
    }
    """
    report = get_object_or_404(Report, id=report_id, owner=request.user)

    facts_qs = Fact.objects.filter(report=report)
    total_count = facts_qs.count()

    # Hardcoded concept matching rules (simple contains checks)
    checks = [
        {
            "label": "Total GHG emissions",
            "code": "ghg_total",
            # Try likely vSME concept fragments
            "concept_contains": ["TotalGHG", "GHGEmissions", "GreenhouseGasEmissions"],
        },
        {
            "label": "Energy consumption",
            "code": "energy_consumption",
            "concept_contains": ["TotalEnergyConsumption", "EnergyConsumption"],
        },
        {
            "label": "Water withdrawal",
            "code": "water_withdrawal",
            "concept_contains": ["WaterWithdrawal"],
        },
        {
            "label": "Waste generated",
            "code": "waste_generated",
            "concept_contains": ["WasteGenerated", "TotalWasteGenerated"],
        },
        {
            "label": "Employees",
            "code": "employees",
            "concept_contains": ["NumberOfEmployees", "Employees"],
        },
    ]

    items: list[dict] = []
    present_count = 0

    for chk in checks:
        matched_fact = None
        for frag in chk["concept_contains"]:
            f = facts_qs.filter(concept__icontains=frag).order_by("id").first()
            if f:
                matched_fact = f
                break
        item = {
            "label": chk["label"],
            "code": chk["code"],
            "present": bool(matched_fact),
            "value": matched_fact.value if matched_fact else None,
        }
        if item["present"]:
            present_count += 1
        items.append(item)

    data = {
        "entity": report.entity,
        "reporting_period": report.reporting_period,
        "fact_count": total_count,
        "required_count": len(checks),
        "present_count": present_count,
        "items": items,
    }
    return Response(data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def report_delete(request: Request, report_id: int) -> Response:
    report = get_object_or_404(Report, id=report_id, owner=request.user)
    report.delete()
    return Response({"deleted": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_original(request: Request, report_id: int):
    report = get_object_or_404(Report, id=report_id, owner=request.user)
    if not report.original_file:
        raise Http404
    response = FileResponse(report.original_file.open("rb"), as_attachment=True, filename=report.original_file.name.split("/")[-1])
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_oim_json(request: Request, report_id: int):
    report = get_object_or_404(Report, id=report_id, owner=request.user)
    if not report.oim_json_file:
        raise Http404
    response = FileResponse(report.oim_json_file.open("rb"), as_attachment=True, filename=report.oim_json_file.name.split("/")[-1])
    return response


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def companies_list(request: Request) -> Response:
    if request.method == "GET":
        companies = Company.objects.all().order_by("name")
        return Response(CompanySerializer(companies, many=True).data)
    # POST: create or return existing (case-insensitive)
    name = (request.data.get("name") or "").strip()
    if not name:
        return Response({"name": ["Name is required."]}, status=400)
    if len(name) < 2:
        return Response({"name": ["Name must be at least 2 characters."]}, status=400)
    existing = Company.objects.filter(name__iexact=name).first()
    if existing:
        return Response(CompanySerializer(existing).data, status=200)
    company = Company.objects.create(name=name)
    return Response(CompanySerializer(company).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def register_list(request: Request) -> Response:
    """List/filter VsmeRegister rows by company name, year range, and min completeness."""
    qs = VsmeRegister.objects.select_related("company").all()
    company = request.query_params.get("company", "").strip()
    year = request.query_params.get("year", "").strip()
    year_from = request.query_params.get("year_from", "").strip()
    year_to = request.query_params.get("year_to", "").strip()
    min_comp = request.query_params.get("min_completeness", "").strip()

    if company:
        qs = qs.filter(company__name__icontains=company)
    if year.isdigit():
        qs = qs.filter(year=int(year))
    else:
        if year_from.isdigit():
            qs = qs.filter(year__gte=int(year_from))
        if year_to.isdigit():
            qs = qs.filter(year__lte=int(year_to))
    if min_comp.isdigit():
        qs = qs.filter(completeness_score__gte=int(min_comp))

    data = VsmeRegisterListSerializer(qs.order_by("company__name", "year"), many=True).data
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def register_detail(request: Request, company_id: int, year: int) -> Response:
    row = get_object_or_404(VsmeRegister.objects.select_related("company"), company_id=company_id, year=year)
    return Response(VsmeRegisterDetailSerializer(row).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def register_export_csv(request: Request) -> Response:
    import csv
    from io import StringIO

    qs = VsmeRegister.objects.select_related("company").all()
    company = request.query_params.get("company", "").strip()
    year = request.query_params.get("year", "").strip()
    year_from = request.query_params.get("year_from", "").strip()
    year_to = request.query_params.get("year_to", "").strip()
    min_comp = request.query_params.get("min_completeness", "").strip()

    if company:
        qs = qs.filter(company__name__icontains=company)
    if year.isdigit():
        qs = qs.filter(year=int(year))
    else:
        if year_from.isdigit():
            qs = qs.filter(year__gte=int(year_from))
        if year_to.isdigit():
            qs = qs.filter(year__lte=int(year_to))
    if min_comp.isdigit():
        qs = qs.filter(completeness_score__gte=int(min_comp))

    headers = [
        "company_id","company_name","year","entity_identifier",
        "employees_value","employees_unit",
        "ghg_total_value","ghg_total_unit",
        "ghg_scope1_value","ghg_scope1_unit",
        "ghg_scope2_value","ghg_scope2_unit",
        "energy_consumption_value","energy_consumption_unit",
        "renewable_energy_share_value","renewable_energy_share_unit",
        "water_withdrawal_value","water_withdrawal_unit",
        "water_discharge_value","water_discharge_unit",
        "waste_generated_value","waste_generated_unit",
        "hazardous_waste_value","hazardous_waste_unit",
        "non_hazardous_waste_value","non_hazardous_waste_unit",
        "completeness_score","updated_at",
    ]

    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    for r in qs.iterator():
        row = [
            r.company_id,
            r.company.name,
            r.year,
            r.entity_identifier,
            r.employees_value, r.employees_unit,
            r.ghg_total_value, r.ghg_total_unit,
            r.ghg_scope1_value, r.ghg_scope1_unit,
            r.ghg_scope2_value, r.ghg_scope2_unit,
            r.energy_consumption_value, r.energy_consumption_unit,
            r.renewable_energy_share_value, r.renewable_energy_share_unit,
            r.water_withdrawal_value, r.water_withdrawal_unit,
            r.water_discharge_value, r.water_discharge_unit,
            r.waste_generated_value, r.waste_generated_unit,
            r.hazardous_waste_value, r.hazardous_waste_unit,
            r.non_hazardous_waste_value, r.non_hazardous_waste_unit,
            r.completeness_score, r.updated_at.isoformat(),
        ]
        writer.writerow(row)

    content = out.getvalue().encode("utf-8")
    from django.http import HttpResponse
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=vsme_register.csv"
    return response
