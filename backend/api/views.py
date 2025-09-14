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
)
from .models import Report
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
    q = request.query_params.get("q", "").strip().lower()
    reports = Report.objects.filter(owner=request.user)
    if q:
        reports = reports.filter(Q(entity__icontains=q) | Q(reporting_period__icontains=q))
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

    try:
        with report.oim_json_file.open("rb") as f:
            oim_json = jsonlib.load(f)
    except Exception as e:
        logger.exception("Failed to load OIM JSON for report id=%s", report_id)
        return Response({"error": "Could not read extracted JSON"}, status=500)

    # Update metadata best-effort if empty
    if not report.entity or not report.reporting_period:
        try:
            entity, period = extract_metadata(oim_json)
            if entity or period:
                report.entity = report.entity or entity
                report.reporting_period = report.reporting_period or period
                report.save(update_fields=["entity", "reporting_period", "updated_at"])
        except Exception:
            logger.warning("Metadata extraction failed for report id=%s", report_id)

    q = (request.query_params.get("q") or "").lower().strip()
    page = max(int(request.query_params.get("page", 1)), 1)
    page_size = max(min(int(request.query_params.get("page_size", 50)), 200), 1)

    try:
        rows = list(extract_facts(oim_json))
    except Exception:
        logger.exception("Fact extraction failed for report id=%s", report_id)
        return Response({"error": "Could not extract facts"}, status=500)

    if q:
        rows = [r for r in rows if q in (r["concept"] or "").lower() or q in (r["value"] or "").lower()]

    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return Response({"results": page_rows, "count": total, "page": page, "page_size": page_size})


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
